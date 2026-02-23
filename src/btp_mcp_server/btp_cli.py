import json
import shutil
import subprocess
import os
from typing import Any, List, Optional, Dict
from .utils import logger, BTPError, BTPCommandError, BTPLoginError

class BTPCLI:
    """
    Wrapper for the SAP BTP CLI (Command Line Interface).
    
    This class handles the execution of 'btp' commands via subprocess,
    manages authentication checks, handles JSON output parsing, and
    maps CLI errors to Python exceptions with robust fail-safe mechanisms.
    """

    def __init__(self, cli_path: Optional[str] = None):
        """
        Initialize the BTP CLI wrapper.

        Args:
            cli_path: Optional full path to the 'btp' executable. 
                      If not provided, it will search in the system PATH and common locations.
        """
        self.cli_path = cli_path or self._find_btp_binary()
        
        if not self.cli_path:
            logger.warning("BTP CLI ('btp') not found in system PATH or common locations. Please ensure it is installed.")

    def _find_btp_binary(self) -> Optional[str]:
        """Search for the 'btp' binary in common locations."""
        # 1. Check in PATH
        path_binary = shutil.which("btp")
        if path_binary:
            return path_binary

        # 2. Check common platform-specific locations
        common_locations = [
            "/usr/local/bin/btp",
            "/opt/homebrew/bin/btp",
            os.path.expanduser("~/bin/btp"),
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "sap", "btp", "btp.exe"),
        ]
        
        for loc in common_locations:
            if os.path.exists(loc) and os.access(loc, os.X_OK):
                return loc
        
        return None

    def _execute(self, args: List[str], timeout: int = 60) -> Dict[str, Any]:
        """
        Execute a BTP command as a subprocess and parse the result.

        Args:
            args: List of command arguments.
            timeout: Maximum execution time in seconds (default 60s).

        Returns:
            Dict containing the parsed JSON output.

        Raises:
            BTPLoginError: If authentication fails.
            BTPCommandError: If the command returns a non-zero exit code.
            BTPError: For execution failures, timeouts, or unexpected errors.
        """
        if not self.cli_path:
            raise BTPError("BTP CLI is not installed or not found. Please download it from https://tools.hana.ondemand.com/#cloud")

        # --- Command Construction ---
        # We always append '--format json' to ensure machine-readable output.
        # This is a core fail-safe for integration.
        # Note: In modern BTP CLI versions, global options like --format must 
        # come BEFORE the positional action/group to avoid parsing errors.
        full_command = [self.cli_path, "--format", "json"] + args
        
        # --- Environment Hardening ---
        # We define specific environment variables to force non-interactive mode.
        env = os.environ.copy()
        env["CI"] = "true" # Disables interactive prompts in most modern CLI tools
        env["PYTHONIOENCODING"] = "utf-8"

        logger.debug(f"Executing: {' '.join(full_command)}")

        try:
            # Run the command with timeout and explicit encoding
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
                encoding="utf-8",
                env=env,
                # Ensure it doesn't wait for input
                stdin=subprocess.DEVNULL 
            )
        except subprocess.TimeoutExpired:
             logger.error(f"BTP command timed out after {timeout}s: {' '.join(full_command)}")
             raise BTPError(f"Command timed out after {timeout} seconds. The SAP BTP API might be slow or unresponsive.")
        except FileNotFoundError:
             raise BTPError(f"BTP CLI executable not found at {self.cli_path}")
        except Exception as e:
             raise BTPError(f"Unexpected error executing BTP CLI: {str(e)}")

        # --- Authentication & Connection Check ---
        combined_output = (result.stdout + result.stderr).lower()
        auth_triggers = [
            "not logged in", 
            "session expired", 
            "login required", 
            "authentication failed",
            "authorization failed",
            "is not authenticated",
            "unknown session",
            "please log in"
        ]
        
        if any(trigger in combined_output for trigger in auth_triggers):
            logger.error("BTP CLI authentication failure detected.")
            raise BTPLoginError(
                "You are not logged in to SAP BTP. Please run " + 
                (f"'{self.cli_path} login'" if self.cli_path else "'btp login'") + 
                " in your terminal and ensure you are targeting the correct global account.",
                result.returncode,
                result.stdout,
                result.stderr
            )

        # --- Error Handling ---
        if result.returncode != 0:
            logger.error(f"BTP CLI command failed (Code {result.returncode})")
            
            # Specific handling for rate limiting or transient busy states
            if "too many requests" in combined_output or "retry after" in combined_output:
                logger.warning("BTP API Rate limiting detected.")
                # We could implement local sleep here if we wanted auto-retry
            
            # Attempt to extract error from JSON but be resilient to mixed output
            msg = self._extract_error_message(result)
            
            raise BTPCommandError(
                f"BTP CLI Error: {msg}",
                result.returncode,
                result.stdout,
                result.stderr
            )

        # --- Success & Parsing ---
        data = self._parse_json_safely(result.stdout, result.stderr)
        
        # Handle Pagination (automatic following of next pages for list commands)
        # BTP CLI JSON usually contains a 'value' list and an optional '@odata.nextLink' or similar 
        # based on the specific API, but currently standard BTP CLI often just returns the list.
        # If it's a list response from 'list' actions, we ensure it's structured.
        return data

    def _execute_with_retry(self, args: List[str], timeout: int = 60, retries: int = 2) -> Dict[str, Any]:
        """
        A fail-safe execution wrapper that implements retries for transient failures.
        
        Logic:
        1. Retries are ONLY performed for base BTPError (timeouts, subprocess crashes).
        2. Retries are NOT performed for Auth errors or Logic errors (Command errors).
        3. Uses exponential backoff (2s, 4s, etc.) to give the BTP API time to recover.
        """
        last_error = None
        for attempt in range(retries + 1):
            try:
                return self._execute(args, timeout=timeout)
            except (BTPLoginError, BTPCommandError):
                # Don't retry on logical errors or auth errors
                raise
            except BTPError as e:
                last_error = e
                if attempt < retries:
                    logger.info(f"Retrying BTP command (attempt {attempt + 1}/{retries})...")
                    import time
                    time.sleep(2 * (attempt + 1)) # Exponential backoff
                continue
        raise last_error

    def _extract_error_message(self, result: subprocess.CompletedProcess) -> str:
        """Helper to extract a clean error message from CLI output."""
        try:
            # Sometimes BTP CLI outputs non-JSON warnings before the actual JSON error
            clean_stdout = result.stdout.strip()
            if "{" in clean_stdout:
                json_start = clean_stdout.find("{")
                data = json.loads(clean_stdout[json_start:])
                return data.get("error", {}).get("message") or data.get("message") or result.stderr.strip()
        except:
            pass
        
        return result.stderr.strip() or result.stdout.strip() or "Unknown CLI error occurred."

    def _parse_json_safely(self, stdout: str, stderr: str) -> Any:
        """
        Deep JSON Recovery Engine.
        
        The BTP CLI often returns mixed output, combining useful data with
        unpredictable login prompts, warnings, or environment messages.
        
        This method uses a multi-tiered strategy:
        1. Direct JSON parsing (Standard Case).
        2. Regex extraction of valid JSON structures within larger blocks of text.
        3. Brute-force boundary search for '{' or '[' markers.
        """
        clean_stdout = stdout.strip()
        if not clean_stdout:
            # Handle empty success (some DELETE commands return empty stdout)
            return {"status": "success", "message": "Command completed successfully.", "details": stderr.strip()}

        try:
            # Multi-layered extraction strategy
            
            # 1. Direct parse
            try:
                return json.loads(clean_stdout)
            except json.JSONDecodeError:
                pass

            # 2. Pattern matching for JSON objects/arrays embedded in text
            # This handles cases where SAP prints "Warning: ..." before the JSON
            json_pattern = r'(\{.*\}|\[.*\])'
            match = re.search(json_pattern, clean_stdout, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # 3. Last resort: manual boundary finding
            if "{" in clean_stdout:
                start = clean_stdout.find("{")
                end = clean_stdout.rfind("}") + 1
                return json.loads(clean_stdout[start:end])
            elif "[" in clean_stdout:
                start = clean_stdout.find("[")
                end = clean_stdout.rfind("]") + 1
                return json.loads(clean_stdout[start:end])
            
            raise json.JSONDecodeError("Manual boundary search failed", clean_stdout, 0)
            
        except (json.JSONDecodeError, ValueError):
            logger.warning("BTP CLI did not return valid JSON. Returning raw output.")
            # Map raw output to a consistent structure
            return {
                "raw_output": clean_stdout, 
                "stderr": stderr.strip(),
                "is_raw": True,
                "warning": "The CLI response was not in a standard JSON format or was truncated."
            }

    def _sanitize_param(self, value: Any) -> str:
        """Sanitize parameters to prevent command injection risks or shell breakage."""
        val_str = str(value)
        # BTP CLI specific sanitation: remove or escape characters that might break 
        # parameter parsing even in subprocess list mode.
        return val_str.strip().replace("\n", " ").replace("\r", "")

    def run_command(self, action: str, group_object: str, params: Dict[str, Any] = {}, flags: List[str] = []) -> Any:
        """
        A generic helper to build and run BTP CLI commands with sanitation.
        """
        # Sanitation to prevent command injection even though subprocess.run([list]) is safe
        action = str(action).strip().lower()
        group_object = str(group_object).strip().lower()
        
        args = [action, group_object]
        
        for key, value in params.items():
            key_clean = str(key).strip().lstrip("-")
            args.append(f"--{key_clean}")
            args.append(self._sanitize_param(value))
            
        for flag in flags:
            flag_clean = str(flag).strip().lstrip("-")
            args.append(f"--{flag_clean}")

        # Increased timeout for potentially heavy operations like creation
        timeout = 300 if action in ["create", "delete", "update", "subscribe", "migrate"] else 60
        return self._execute_with_retry(args, timeout=timeout)

    def ping(self) -> bool:
        """
        Check if the BTP CLI is accessible and the user is authenticated.
        Returns True if successful, raises exception otherwise.
        """
        # We use a simple 'get global-account' as a health check
        self.get_global_account()
        return True

    def list_regions(self) -> Any:
        """List all available technical regions for the current global account."""
        return self.run_command("list", "accounts/region")

    def list_directories(self) -> Any:
        """List all directories in the global account."""
        return self.run_command("list", "accounts/directory")

    # ==========================
    # --- Account Management ---
    # ==========================

    def list_subaccounts(self) -> Any:
        """Fetch all subaccounts accessible to the current user."""
        return self.run_command("list", "accounts/subaccount")

    def get_subaccount(self, subaccount_id: str) -> Any:
        """Get detailed information for a specific subaccount ID."""
        return self.run_command("get", "accounts/subaccount", {"subaccount": subaccount_id})

    def create_subaccount(self, display_name: str, region: str, subdomain: str) -> Any:
        """Create a new subaccount in the current global account."""
        return self.run_command("create", "accounts/subaccount", {
            "display-name": display_name,
            "region": region,
            "subdomain": subdomain
        })

    def delete_subaccount(self, subaccount_id: str, confirm: bool = False) -> Any:
        """Delete an existing subaccount."""
        flags = ["confirm"] if confirm else []
        return self.run_command("delete", "accounts/subaccount", {"subaccount": subaccount_id}, flags)

    def get_global_account(self) -> Any:
        """Retrieve details about the current global account."""
        return self.run_command("get", "accounts/global-account")

    # ================
    # --- Security ---
    # ================

    def list_users(self) -> Any:
        """List all users in the current global account context."""
        return self.run_command("list", "security/user")

    def get_user(self, email: str) -> Any:
        """Get details for a specific user by their email address."""
        return self.run_command("get", "security/user", {"user": email})

    def list_role_collections(self) -> Any:
        """List all available role collections."""
        return self.run_command("list", "security/role-collection")

    def assign_role_collection(self, role_collection_name: str, user_email: str) -> Any:
        """Assign a specific role collection to a user."""
        return self.run_command("assign", "security/role-collection", {
            "name": role_collection_name,
            "to-user": user_email
        })

    def unassign_role_collection(self, role_collection_name: str, user_email: str) -> Any:
        """Unassign a role collection from a user."""
        return self.run_command("unassign", "security/role-collection", {
            "name": role_collection_name,
            "from-user": user_email
        })

    # ====================
    # --- Entitlements ---
    # ====================

    def list_entitlements(self, subaccount_id: str) -> Any:
        """List all service plans and quotas (entitlements) assigned to a subaccount."""
        return self.run_command("list", "accounts/entitlement", {"subaccount": subaccount_id})

    def assign_entitlement(self, subaccount_id: str, service_name: str, service_plan: str, amount: Optional[int] = None) -> Any:
        """Allocate or update an entitlement quota for a specific subaccount."""
        params = {
            "to-subaccount": subaccount_id,
            "service-name": service_name,
            "plan-name": service_plan
        }
        if amount is not None:
            params["amount"] = str(amount)
        return self.run_command("assign", "accounts/entitlement", params)

    def remove_entitlement(self, subaccount_id: str, service_name: str, service_plan: str) -> Any:
        """Remove an entitlement from a subaccount."""
        return self.run_command("remove", "accounts/entitlement", {
            "subaccount": subaccount_id,
            "service-name": service_name,
            "plan-name": service_plan
        })

    # ================
    # --- Services ---
    # ================

    def list_service_instances(self, subaccount_id: str) -> Any:
        """List all service instances created in a specific subaccount."""
        return self.run_command("list", "services/instance", {"subaccount": subaccount_id})

    def list_service_bindings(self, subaccount_id: str) -> Any:
         """List all service bindings in a specific subaccount."""
         return self.run_command("list", "services/binding", {"subaccount": subaccount_id})

    # ====================
    # --- Connectivity ---
    # ====================

    def list_destinations(self, subaccount_id: str) -> Any:
        """List all destinations defined in a subaccount."""
        return self.run_command("list", "connectivity/destination", {"subaccount": subaccount_id})

    def get_destination(self, subaccount_id: str, destination_name: str) -> Any:
        """Get details of a specific destination configuration."""
        return self.run_command("get", "connectivity/destination", {
            "subaccount": subaccount_id,
            "name": destination_name
        })

    def list_environment_instances(self, subaccount_id: str) -> Any:
        """List all environment instances (CF, Kyma, etc.) in a specific subaccount."""
        return self.run_command("list", "accounts/environment-instance", {"subaccount": subaccount_id})

    def list_subscriptions(self, subaccount_id: str) -> Any:
        """List all multi-tenant application subscriptions in a specific subaccount."""
        return self.run_command("list", "accounts/subscription", {"subaccount": subaccount_id})

