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

        # We always append '--format json' to ensure machine-readable output.
        # This is a core fail-safe for integration.
        full_command = [self.cli_path] + args + ["--format", "json"]
        
        # Ensure we don't start interactive mode which hangs the server
        env = os.environ.copy()
        # Some CLIs use env vars to disable interactivity
        env["CI"] = "true" 
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
            "is not authenticated"
        ]
        
        if any(trigger in combined_output for trigger in auth_triggers):
            logger.error("BTP CLI authentication failure detected.")
            raise BTPLoginError(
                "You are not logged in to SAP BTP. Please run 'btp login' in your terminal and ensure you are targeting the correct global account.",
                result.returncode,
                result.stdout,
                result.stderr
            )

        # --- Error Handling ---
        if result.returncode != 0:
            logger.error(f"BTP CLI command failed (Code {result.returncode})")
            
            # Attempt to extract error from JSON but be resilient to mixed output
            msg = self._extract_error_message(result)
            
            raise BTPCommandError(
                f"BTP CLI Error: {msg}",
                result.returncode,
                result.stdout,
                result.stderr
            )

        # --- Success & Parsing ---
        return self._parse_json_safely(result.stdout, result.stderr)

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

    def _parse_json_safely(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Safely parse JSON from stdout, handling potential non-JSON prefix/suffix."""
        clean_stdout = stdout.strip()
        if not clean_stdout:
            return {"status": "success", "message": "Command completed successfully.", "details": stderr.strip()}

        try:
            # Find the actual JSON boundaries in case of CLI warnings/messages
            if "{" in clean_stdout:
                start = clean_stdout.find("{")
                end = clean_stdout.rfind("}") + 1
                return json.loads(clean_stdout[start:end])
            elif "[" in clean_stdout:
                start = clean_stdout.find("[")
                end = clean_stdout.rfind("]") + 1
                return {"items": json.loads(clean_stdout[start:end])}
            
            return json.loads(clean_stdout)
        except json.JSONDecodeError:
            logger.warning("BTP CLI did not return valid JSON. Returning raw output.")
            return {
                "raw_output": clean_stdout, 
                "stderr": stderr.strip(),
                "warning": "The CLI response was not in a standard JSON format."
            }

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
            args.append(str(value))
            
        for flag in flags:
            flag_clean = str(flag).strip().lstrip("-")
            args.append(f"--{flag_clean}")

        # Increased timeout for potentially heavy operations like creation
        timeout = 120 if action in ["create", "delete", "update", "subscribe"] else 60
        return self._execute(args, timeout=timeout)

    def ping(self) -> bool:
        """
        Check if the BTP CLI is accessible and the user is authenticated.
        Returns True if successful, raises exception otherwise.
        """
        # We use a simple 'get global-account' as a health check
        self.get_global_account()
        return True

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

