from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .btp_cli import BTPCLI, BTPError, BTPCommandError, BTPLoginError
from .utils import logger

# Initialize FastMCP
mcp = FastMCP("SAP BTP CLI Manager")

# Initialize BTP CLI wrapper
cli = BTPCLI()

# --- Core Tools ---

@mcp.tool()
def btp_execute_command(
    action: str = Field(..., description="The action (e.g., 'list', 'get', 'create', 'delete', 'assign')."),
    group_object: str = Field(..., description="The object (e.g., 'accounts/subaccount', 'security/user')."),
    parameters: Dict[str, str] = Field(default_factory=dict, description="Parameters (e.g., {'subaccount': 'id'}). Keys without '--' prefix."),
    flags: List[str] = Field(default_factory=list, description="Flags (e.g., ['verbose']). without '--' prefix.")
) -> str:
    """
    Execute ANY SAP BTP CLI command. 
    Use this if a specific tool is not available.
    """
    try:
        result = cli.run_command(action, group_object, parameters, flags)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# --- Account Management Tools ---

@mcp.tool()
def btp_list_subaccounts() -> str:
    """List all subaccounts in the global account."""
    try:
        return str(cli.list_subaccounts())
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_get_subaccount(subaccount_id: str = Field(..., description="ID of the subaccount")) -> str:
    """Get details of a specific subaccount."""
    try:
        return str(cli.get_subaccount(subaccount_id))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_create_subaccount(
    display_name: str = Field(..., description="Display name for the new subaccount"),
    region: str = Field(..., description="Region (e.g., 'us10')"),
    subdomain: str = Field(..., description="Unique subdomain")
) -> str:
    """Create a new subaccount."""
    try:
        return str(cli.create_subaccount(display_name, region, subdomain))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_delete_subaccount(
    subaccount_id: str = Field(..., description="ID of the subaccount to delete"),
    confirm: bool = Field(False, description="Set to True to bypass confirmation prompt")
) -> str:
    """Delete a subaccount."""
    try:
        return str(cli.delete_subaccount(subaccount_id, confirm))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_get_global_account() -> str:
    """Get details of the current global account."""
    try:
        return str(cli.get_global_account())
    except Exception as e: return f"Error: {str(e)}"

# --- Security Tools ---

@mcp.tool()
def btp_list_users() -> str:
    """List all users in the global account."""
    try:
        return str(cli.list_users())
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_get_user(email: str = Field(..., description="Email address of the user")) -> str:
    """Get details for a specific user."""
    try:
        return str(cli.get_user(email))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_list_role_collections() -> str:
    """List all role collections."""
    try:
        return str(cli.list_role_collections())
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_assign_role_collection(
    role_collection_name: str = Field(..., description="Name of the role collection"),
    user_email: str = Field(..., description="Email of the user")
) -> str:
    """Assign a role collection to a user."""
    try:
        return str(cli.assign_role_collection(role_collection_name, user_email))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_unassign_role_collection(
    role_collection_name: str = Field(..., description="Name of the role collection"),
    user_email: str = Field(..., description="Email of the user")
) -> str:
    """Unassign a role collection from a user."""
    try:
        return str(cli.unassign_role_collection(role_collection_name, user_email))
    except Exception as e: return f"Error: {str(e)}"

# --- Entitlement Tools ---

@mcp.tool()
def btp_list_entitlements(subaccount_id: str = Field(..., description="ID of the subaccount")) -> str:
    """List entitlements for a subaccount."""
    try:
        return str(cli.list_entitlements(subaccount_id))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_assign_entitlement(
    subaccount_id: str = Field(..., description="ID of the subaccount"),
    service_name: str = Field(..., description="Name of the service"),
    service_plan: str = Field(..., description="Name of the plan"),
    amount: Optional[int] = Field(None, description="Amount/Quota to assign (optional)")
) -> str:
    """Assign an entitlement quota to a subaccount."""
    try:
        return str(cli.assign_entitlement(subaccount_id, service_name, service_plan, amount))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_remove_entitlement(
    subaccount_id: str = Field(..., description="ID of the subaccount"),
    service_name: str = Field(..., description="Name of the service"),
    service_plan: str = Field(..., description="Name of the plan")
) -> str:
    """Remove an entitlement from a subaccount."""
    try:
        return str(cli.remove_entitlement(subaccount_id, service_name, service_plan))
    except Exception as e: return f"Error: {str(e)}"

# --- Service Tools ---

@mcp.tool()
def btp_list_service_instances(subaccount_id: str = Field(..., description="ID of the subaccount")) -> str:
    """List service instances in a subaccount."""
    try:
        return str(cli.list_service_instances(subaccount_id))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_list_service_bindings(subaccount_id: str = Field(..., description="ID of the subaccount")) -> str:
    """List service bindings in a subaccount."""
    try:
        return str(cli.list_service_bindings(subaccount_id))
    except Exception as e: return f"Error: {str(e)}"

# --- Connectivity Tools ---

@mcp.tool()
def btp_list_destinations(subaccount_id: str = Field(..., description="ID of the subaccount")) -> str:
    """List destinations in a subaccount."""
    try:
        return str(cli.list_destinations(subaccount_id))
    except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
def btp_get_destination(
    subaccount_id: str = Field(..., description="ID of the subaccount"),
    destination_name: str = Field(..., description="Name of the destination")
) -> str:
    """Get details of a specific destination."""
    try:
        return str(cli.get_destination(subaccount_id, destination_name))
    except Exception as e: return f"Error: {str(e)}"

def main():
    mcp.run()
