import json
import re
from typing import Any, Dict, List, Optional, Union
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .btp_cli import BTPCLI, BTPError, BTPCommandError, BTPLoginError
from .utils import logger

# --- FastMCP Initialization ---
mcp = FastMCP("SAP BTP CLI Manager")


# --- Initial Setup ---
# Initialize the BTP CLI wrapper with optional path from environment.
# This allows the server to work even if 'btp' is not in the system's global PATH.
import os
cli_path = os.environ.get("BTP_CLI_PATH")
cli = BTPCLI(cli_path=cli_path)

# --- Response Formatting ---
def format_response(data: Any) -> str:
    """
    Standardizes and beautifies the output format for all tools. 
    Ensures the AI agent receives structured, readable, and parseable markdown-like strings.
    
    Processing Steps:
    1. Handle None: Returns a clear success message.
    2. Handle Lists/Dicts: 
       - If the result is a wrapper dict with an 'items' key (common in BTP CLI),
         it unwraps it to provide a cleaner list to the LLM.
       - Converts to pretty-printed JSON (indent=2) for max readability.
    3. Handle Strings/Primitives: Returns stripped string.
    """
    if data is None:
        return "Command completed successfully with no return data."
    
    if isinstance(data, (dict, list)):
        # If the result contains a single key with the list of items, simplify it
        if isinstance(data, dict) and len(data) == 1 and "items" in data:
             data = data["items"]
        return json.dumps(data, indent=2)
    
    return str(data).strip()

def handle_btp_errors(func):
    """
    A unified higher-order decorator that wraps all tool execution.
    It translates internal Python exceptions into human-friendly (and AI-friendly) 
    response strings.
    
    Error Mapping:
    - BTPLoginError: Prompts the user with specific CLI login commands.
    - BTPCommandError: Captures CLI-level failures (invalid IDs, permissions) and 
      appends helpful 'TIP' hints based on natural language analysis of the error.
    - BTPError: Catches foundational execution errors (timeouts, missing binaries).
    - Exception: Catch-all for unexpected internal logic bugs to prevent server crash.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BTPLoginError as e:
            return (
                f"❌ AUTHENTICATION ERROR: {str(e)}\n\n"
                "To fix this, please follow these steps:\n"
                "1. Open your local terminal.\n"
                f"2. Run: {cli.cli_path or 'btp'} login\n"
                "3. Follow the prompts to authenticate.\n"
                "4. Once authenticated, try your request again."
            )
        except BTPCommandError as e:
            error_msg = str(e)
            hint = ""
            if "entitlement" in error_msg.lower() and "quota" in error_msg.lower():
                hint = "\n💡 TIP: Check if your global account has enough quota for this service plan using 'btp_list_entitlements'."
            elif "region" in error_msg.lower():
                hint = "\n💡 TIP: Run 'btp_list_regions' to see available technical region IDs."
            elif "already exists" in error_msg.lower():
                hint = "\n💡 TIP: Subdomains must be globally unique across all of BTP, not just your account."
                
            return f"⚠️ BTP CLI ERROR: {error_msg}{hint}\n(Return Code: {e.return_code})"
        except BTPError as e:
            return f"🚫 BTP SERVER ERROR: {str(e)}\nEnsure your internet connection is stable and the SAP BTP API is online."
        except Exception as e:
            logger.exception(f"Unexpected error in tool {func.__name__}")
            return f"❌ INTERNAL ERROR: An unexpected error occurred: {str(e)}"
    # Preserve function metadata for FastMCP
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

# ==================
# --- Core Tools ---
# ==================

@mcp.tool()
@handle_btp_errors
def btp_ping() -> str:
    """
    Diagnostic tool to verify connectivity and login status.
    Use this if you are unsure if the BTP CLI is configured correctly.
    """
    cli.ping()
    return "✅ Success: BTP CLI is accessible and you are currently logged in."

@mcp.tool()
@handle_btp_errors
def btp_execute_command(
    action: str = Field(..., description="The verb (e.g., 'list', 'get', 'create', 'delete', 'assign')."),
    group_object: str = Field(..., description="The resource category (e.g., 'accounts/subaccount', 'security/role-collection')."),
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs for parameters. Do NOT include '--' prefix. Example: {'subaccount': 'id'}"),
    flags: List[str] = Field(default_factory=list, description="List of boolean flags. Do NOT include '--' prefix. Example: ['confirm', 'verbose']")
) -> str:
    """
    Generic execution engine for ANY SAP BTP CLI command.
    Use this if a dedicated tool is not available for a specific resource type.
    
    Safety: This tool automatically handles JSON formatting and error detection.
    """
    result = cli.run_command(action, group_object, parameters, flags)
    return format_response(result)

# ==================================
# --- Account Management Tools ---
# ==================================

@mcp.tool()
@handle_btp_errors
def btp_list_subaccounts() -> str:
    """List all subaccounts in the current global account including their IDs, names, and states."""
    return format_response(cli.list_subaccounts())

@mcp.tool()
@handle_btp_errors
def btp_get_subaccount(
    subaccount_id: str = Field(..., description="The unique technical ID (GUID) of the subaccount.")
) -> str:
    """Get comprehensive details for a specific subaccount, including region, subdomain, and parent IDs."""
    if not re.match(r'^[0-9a-fA-F-]+$', subaccount_id):
        return "❌ Error: Invalid subaccount ID format. It should be a technical GUID."
    
    return format_response(cli.get_subaccount(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_create_subaccount(
    display_name: str = Field(..., description="Human-readable name. Min length 1."),
    region: str = Field(..., description="Technical region ID (e.g. 'us10', 'eu10', 'ap21')."),
    subdomain: str = Field(..., description="Unique URL prefix. Must be lowercase, start with a letter, and contain only letters, numbers, and hyphens.")
) -> str:
    """
    Provision a new subaccount in the current global account.
    This operation is asynchronous on the platform side but the tool waits for the initial response.
    """
    if not display_name or len(display_name.strip()) == 0:
        return "❌ Error: display_name cannot be empty."
    
    if not re.match(r'^[a-z0-9-]+$', region):
        return "❌ Error: region must be a technical ID (e.g., 'us10', 'cf-eu10')."

    if not re.match(r'^[a-z][a-z0-9-]{0,62}$', subdomain):
        return "❌ Error: subdomain must start with a letter, be lowercase, contain only letters/numbers/hyphens, and be max 63 chars."

    return format_response(cli.create_subaccount(display_name, region, subdomain))

@mcp.tool()
@handle_btp_errors
def btp_delete_subaccount(
    subaccount_id: str = Field(..., description="The GUID of the subaccount to delete."),
    confirm: bool = Field(False, description="Explicitly set to True to confirm deletion without a prompt.")
) -> str:
    """
    Delete a subaccount permanently. 
    WARNING: This will delete all resources within the subaccount.
    """
    return format_response(cli.delete_subaccount(subaccount_id, confirm))

@mcp.tool()
@handle_btp_errors
def btp_get_global_account() -> str:
    """Retrieve metadata about the current global account context, including its name and ID."""
    return format_response(cli.get_global_account())

@mcp.tool()
@handle_btp_errors
def btp_list_regions() -> str:
    """List all technical regions available in the global account (e.g., 'us10', 'eu10')."""
    return format_response(cli.list_regions())

@mcp.tool()
@handle_btp_errors
def btp_list_directories() -> str:
    """List all directories created within the global account hierarchy."""
    return format_response(cli.list_directories())

# ======================
# --- Security Tools ---
# ======================

@mcp.tool()
@handle_btp_errors
def btp_list_users() -> str:
    """List all users who have been added to the current global account or custom IdP."""
    return format_response(cli.list_users())

@mcp.tool()
@handle_btp_errors
def btp_get_user(
    email: str = Field(..., description="The login email address of the user.")
) -> str:
    """Get security details and role assignments for a specific user."""
    if "@" not in email:
        return "❌ Error: Please provide a valid email address."
    return format_response(cli.get_user(email))

@mcp.tool()
@handle_btp_errors
def btp_list_role_collections() -> str:
    """List all available role collections in the global account context."""
    return format_response(cli.list_role_collections())

@mcp.tool()
@handle_btp_errors
def btp_assign_role_collection(
    role_collection_name: str = Field(..., description="Exact name of the role collection."),
    user_email: str = Field(..., description="Email of the target user.")
) -> str:
    """Grant a role collection (group of permissions) to a user."""
    return format_response(cli.assign_role_collection(role_collection_name, user_email))

@mcp.tool()
@handle_btp_errors
def btp_unassign_role_collection(
    role_collection_name: str = Field(..., description="Name of the role collection to remove."),
    user_email: str = Field(..., description="Email of the user.")
) -> str:
    """Revoke a role collection from a user."""
    return format_response(cli.unassign_role_collection(role_collection_name, user_email))

# ==========================
# --- Entitlement Tools ---
# ==========================

@mcp.tool()
@handle_btp_errors
def btp_list_entitlements(
    subaccount_id: str = Field(..., description="GUID of the subaccount to check.")
) -> str:
    """
    List service plans and quotas (entitlements) assigned to a subaccount.
    Useful for checking if a subaccount has enough 'units' to provision a service.
    """
    return format_response(cli.list_entitlements(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_assign_entitlement(
    subaccount_id: str = Field(..., description="The ID of the subaccount to receive the entitlement."),
    service_name: str = Field(..., description="Technical name of the service (e.g. 'hana', 'it-rt')."),
    service_plan: str = Field(..., description="Name of the plan (e.g. 'hdi-shared', 'standard')."),
    amount: Optional[int] = Field(None, description="The quota amount/units to allocate. If None, it might assign the plan without specific quota if applicable.")
) -> str:
    """
    Assign or increase service plan quota for a subaccount.
    This enables you to then create service instances of that plan in that subaccount.
    """
    return format_response(cli.assign_entitlement(subaccount_id, service_name, service_plan, amount))

@mcp.tool()
@handle_btp_errors
def btp_remove_entitlement(
    subaccount_id: str = Field(..., description="The ID of the subaccount."),
    service_name: str = Field(..., description="Technical name of the service."),
    service_plan: str = Field(..., description="Name of the plan.")
) -> str:
    """
    Remove an entitlement (service plan quota) from a subaccount.
    Useful for freeing up global quota or cleaning up unused services.
    """
    return format_response(cli.remove_entitlement(subaccount_id, service_name, service_plan))

# =====================
# --- Service Tools ---
# =====================

@mcp.tool()
@handle_btp_errors
def btp_list_service_instances(
    subaccount_id: str = Field(..., description="The ID of the subaccount.")
) -> str:
    """List all service instances (active services) in a subaccount."""
    return format_response(cli.list_service_instances(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_list_service_bindings(
    subaccount_id: str = Field(..., description="The ID of the subaccount.")
) -> str:
    """List service bindings (credentials for applications) in a subaccount."""
    return format_response(cli.list_service_bindings(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_list_environment_instances(
    subaccount_id: str = Field(..., description="The ID of the subaccount.")
) -> str:
    """List all environment instances (e.g., Cloud Foundry, Kyma) in a subaccount."""
    return format_response(cli.list_environment_instances(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_list_subscriptions(
    subaccount_id: str = Field(..., description="The ID of the subaccount.")
) -> str:
    """List multi-tenant application subscriptions in a subaccount."""
    return format_response(cli.list_subscriptions(subaccount_id))

# ==========================
# --- Connectivity Tools ---
# ==========================

@mcp.tool()
@handle_btp_errors
def btp_list_destinations(
    subaccount_id: str = Field(..., description="The ID of the subaccount.")
) -> str:
    """List all destinations (HTTP/RFC connections) in a subaccount."""
    return format_response(cli.list_destinations(subaccount_id))

@mcp.tool()
@handle_btp_errors
def btp_get_destination(
    subaccount_id: str = Field(..., description="The ID of the subaccount."),
    destination_name: str = Field(..., description="Name of the destination.")
) -> str:
    """Get the full configuration (URL, authentication, proxy) of a specific destination."""
    return format_response(cli.get_destination(subaccount_id, destination_name))

def main():
    """Start the MCP server via stdio."""
    mcp.run()
