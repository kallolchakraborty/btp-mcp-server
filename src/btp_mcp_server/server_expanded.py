from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .btp_cli import BTPCLI, BTPError, BTPCommandError, BTPLoginError
from .utils import logger

# Initialize FastMCP - this will handle the stdio connection
mcp = FastMCP("SAP BTP CLI Manager")

# Initialize BTP CLI wrapper
# We assume BTP is in PATH. If not, this might log a warning but won't crash immediately.
cli = BTPCLI()

@mcp.tool()
def btp_execute_command(
    action: str = Field(..., description="The action to perform (e.g., 'list', 'get', 'create', 'update', 'delete', 'assign', 'unassign')."),
    group_object: str = Field(..., description="The object to act on (e.g., 'accounts/subaccount', 'security/role-collection')."),
    parameters: Dict[str, str] = Field(default_factory=dict, description="Key-value pairs for command parameters (e.g., {'passcode': '...'} or {'subaccount': 'id'}). Do NOT include '--' prefix in keys."),
    flags: List[str] = Field(default_factory=list, description="List of boolean flags to enable (e.g., ['verbose', 'force']). Do NOT include '--' prefix.")
) -> str:
    """
    Execute a generic SAP BTP CLI command.
    
    This tool allows you to run any available BTP command by specifying the action, object, and parameters.
    It returns the JSON output from the BTP CLI.
    
    Example:
      action='list', group_object='accounts/subaccount' -> 'btp list accounts/subaccount'
      action='get', group_object='security/user', parameters={'email': 'user@example.com'} -> 'btp get security/user --email user@example.com'
    """
    try:
        result = cli.run_command(action, group_object, parameters, flags)
        # FastMCP automatically handles dict returns as JSON content
        return str(result) 
    except BTPLoginError as e:
        return f"Authentication Error: {str(e)}"
    except BTPCommandError as e:
        return f"Command Failed (Exit Code {e.return_code}): {str(e)}"
    except BTPError as e:
        return f"BTP CLI Error: {str(e)}"
    except Exception as e:
        logger.exception("Unexpected error in btp_execute_command")
        return f"Internal Server Error: {str(e)}"

@mcp.tool()
def btp_list_subaccounts() -> str:
    """
    List all subaccounts in the current global account.
    """
    try:
        result = cli.list_subaccounts()
        return str(result)
    except BTPError as e:
        return f"Error listing subaccounts: {str(e)}"

@mcp.tool()
def btp_get_subaccount(subaccount_id: str = Field(..., description="The ID of the subaccount to retrieve.")) -> str:
    """
    Get details for a specific subaccount.
    """
    try:
        result = cli.get_subaccount(subaccount_id)
        return str(result)
    except BTPError as e:
        return f"Error getting subaccount details: {str(e)}"

@mcp.tool()
def btp_list_entitlements(
    subaccount_id: str = Field(..., description="The ID of the subaccount to list entitlements for.")
) -> str:
    """
    List entitlements (service plans) available to a subaccount.
    """
    try:
        result = cli.list_entitlements(subaccount_id)
        return str(result)
    except BTPError as e:
        return f"Error listing entitlements: {str(e)}"

def main():
    """Entry point to start the server."""
    mcp.run()
