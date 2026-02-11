import json
import shutil
import subprocess
from typing import Any, List, Optional, Dict
from .utils import logger, BTPError, BTPCommandError, BTPLoginError

class BTPCLI:
    """
    Wrapper for the SAP BTP CLI.
    Handles command execution, error checking, and JSON parsing.
    """

    def __init__(self, cli_path: Optional[str] = None):
        """
        Initialize the BTP CLI wrapper.

        Args:
            cli_path: Optional path to the btp executable. If None, looks in PATH.
        """
        self.cli_path = cli_path or shutil.which("btp")
        if not self.cli_path:
            logger.warning("BTP CLI not found in PATH. Please verify installation.")
    
    def _execute(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute a BTP command and return the parsed JSON result.

        Args:
            args: List of command arguments (excluding 'btp').

        Returns:
            Dict containing the parsed JSON output or raw execution details.

        Raises:
            BTPLoginError: If the user is not authenticated.
            BTPCommandError: If the command fails.
        """
        if not self.cli_path:
            raise BTPError("BTP CLI is not installed or not found in PATH.")

        # Always try to force JSON output for easier parsing
        full_command = [self.cli_path] + args + ["--format", "json"]
        
        logger.debug(f"Executing: {' '.join(full_command)}")

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False 
            )
        except FileNotFoundError:
             raise BTPError("BTP CLI executable not found during execution.")

        # Check for login errors in stderr/stdout
        combined_output = (result.stdout + result.stderr).lower()
        if "not logged in" in combined_output or "session expired" in combined_output:
            logger.error("User is not logged in to BTP CLI.")
            raise BTPLoginError(
                "You are not logged in to the SAP BTP CLI. Please run 'btp login' in your terminal.",
                result.returncode,
                result.stdout,
                result.stderr
            )

        if result.returncode != 0:
            logger.error(f"Command failed with code {result.returncode}: {result.stderr}")
            try:
                err_json = json.loads(result.stdout) if result.stdout else {}
                msg = err_json.get("error", {}).get("message") or result.stderr.strip()
            except json.JSONDecodeError:
                msg = result.stderr.strip() or result.stdout.strip()
            
            raise BTPCommandError(
                f"BTP CLI Error: {msg}",
                result.returncode,
                result.stdout,
                result.stderr
            )

        # Success - Parse JSON
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("Could not parse BTP CLI output as JSON. Returning raw stdout.")
            return {"raw_output": result.stdout, "warning": "Output was not valid JSON"}

    def run_command(self, action: str, group_object: str, params: Dict[str, str] = {}, flags: List[str] = []) -> Any:
        """
        Generic method to run any BTP command.
        """
        args = [action, group_object]
        
        for key, value in params.items():
            # Add -- prefix if missing
            flag_name = key if key.startswith("-") else f"--{key}"
            args.append(flag_name)
            args.append(value)
            
        for flag in flags:
            flag_name = flag if flag.startswith("-") else f"--{flag}"
            args.append(flag_name)

        return self._execute(args)

    # --- Account Management ---
    def list_subaccounts(self) -> Any:
        return self.run_command("list", "accounts/subaccount")

    def get_subaccount(self, subaccount_id: str) -> Any:
        return self.run_command("get", "accounts/subaccount", {"subaccount": subaccount_id})

    def create_subaccount(self, display_name: str, region: str, subdomain: str) -> Any:
        return self.run_command("create", "accounts/subaccount", {
            "display-name": display_name,
            "region": region,
            "subdomain": subdomain
        })

    def delete_subaccount(self, subaccount_id: str, confirm: bool = False) -> Any:
        flags = ["confirm"] if confirm else []
        return self.run_command("delete", "accounts/subaccount", {"subaccount": subaccount_id}, flags)

    def get_global_account(self) -> Any:
        return self.run_command("get", "accounts/global-account")

    # --- Security ---
    def list_users(self) -> Any:
        return self.run_command("list", "security/user")

    def get_user(self, email: str) -> Any:
        return self.run_command("get", "security/user", {"user": email})

    def list_role_collections(self) -> Any:
        return self.run_command("list", "security/role-collection")

    def assign_role_collection(self, role_collection_name: str, user_email: str) -> Any:
        return self.run_command("assign", "security/role-collection", {
            "name": role_collection_name,
            "to-user": user_email
        })

    def unassign_role_collection(self, role_collection_name: str, user_email: str) -> Any:
        return self.run_command("unassign", "security/role-collection", {
            "name": role_collection_name,
            "from-user": user_email
        })

    # --- Entitlements ---
    def list_entitlements(self, subaccount_id: str) -> Any:
        return self.run_command("list", "accounts/entitlement", {"subaccount": subaccount_id})

    def assign_entitlement(self, subaccount_id: str, service_name: str, service_plan: str, amount: Optional[int] = None) -> Any:
        params = {
            "to-subaccount": subaccount_id,
            "service-name": service_name,
            "plan-name": service_plan
        }
        if amount is not None:
            params["amount"] = str(amount)
        return self.run_command("assign", "accounts/entitlement", params)

    def remove_entitlement(self, subaccount_id: str, service_name: str, service_plan: str) -> Any:
        return self.run_command("remove", "accounts/entitlement", {
            "subaccount": subaccount_id,
            "service-name": service_name,
            "plan-name": service_plan
        })

    # --- Services ---
    def list_service_instances(self, subaccount_id: str) -> Any:
        return self.run_command("list", "services/instance", {"subaccount": subaccount_id})

    def list_service_bindings(self, subaccount_id: str) -> Any:
         return self.run_command("list", "services/binding", {"subaccount": subaccount_id})

    # --- Connectivity ---
    def list_destinations(self, subaccount_id: str) -> Any:
        return self.run_command("list", "connectivity/destination", {"subaccount": subaccount_id})

    def get_destination(self, subaccount_id: str, destination_name: str) -> Any:
        return self.run_command("get", "connectivity/destination", {
            "subaccount": subaccount_id,
            "name": destination_name
        })
