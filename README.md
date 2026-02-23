# 🚀 SAP BTP MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-blue.svg)](https://modelcontextprotocol.io)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-778899.svg)](https://www.python.org/)

A professional **Model Context Protocol (MCP)** server providing a robust natural language interface for **SAP Business Technology Platform (BTP)**. 

Manage your cloud infrastructure, security, and entitlements conversationally through AI agents (Claude, Gemini, etc.) using your local `btp` CLI session.

---

## 🌟 Key Features

- **Conversational Infrastructure**: Provision subaccounts and assign roles using simple language.
- **Fail-Safe Design**: Built-in timeouts, non-interactive execution, and resilient output parsing.
- **Secure by Design**: 
  - Runs entirely **locally**; no external credentials or tokens are stored.
  - Leverages your existing **BTP CLI authentication** (SSO/JWT).
- **Proactive Error Handling**: Provides clear instructions when authentication expires or inputs are invalid.
- **Automatic Discovery**: Intelligently locates the `btp` binary across Windows, macOS, and Linux.

---

## 🏗️ Fail-Proof Architecture

This server is designed for mission-critical AI automation:
*   **Intelligent Timeouts**: Prevents "hanging" on long SAP BTP API operations with 60s/120s thresholds.
*   **Deep JSON Recovery**: Automatically extracts valid data even if the CLI returns mixed output or warnings.
*   **Input Validation**: Pre-validates technical IDs (GUIDs) and Emails to prevent unnecessary CLI failures.
*   **Non-Interactivity**: Guaranteed non-blocking execution using CI-mode environments and null-input piping.

---

## 📋 Prerequisites

1.  **SAP BTP CLI**: Installed and in your system `PATH`.
    - [Download here](https://tools.hana.ondemand.com/#cloud)
2.  **Active Session**: You must be logged in. Verify with: `btp list accounts/global-account`
3.  **Python 3.10+**: Ensure a modern Python environment.

---

## 🛠️ Installation

### Using `uv` (Recommended)
```bash
uv tool install --from . btp-mcp-server
```

### Using `pip`
```bash
pip install .
```

---

## ⚙️ Configuration

Add the following to your MCP client config (e.g., `claude_desktop_config.json`):

### Using `uv` (Fastest)
```json
{
  "mcpServers": {
    "btp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/BTP MCP Server",
        "run",
        "btp-mcp-server"
      ]
    }
  }
}
```

### Using Python
```json
{
  "mcpServers": {
    "btp": {
      "command": "python3",
      "args": ["-m", "btp_mcp_server"],
      "env": { "PYTHONPATH": "/absolute/path/to/BTP MCP Server/src" }
    }
  }
}
```

---

## 🧠 Available Tools

| Category | Tool | Description |
| :--- | :--- | :--- |
| **System** | `btp_ping` | Checks CLI health and login status. |
| | `btp_execute_command` | Run *any* generic BTP CLI command. |
| **Accounts** | `btp_list_subaccounts` | List all accessible subaccounts. |
| | `btp_create_subaccount` | Provision a new subaccount with validation. |
| | `btp_delete_subaccount` | Permanent deletion of a subaccount. |
| | `btp_list_regions` | List available technical regions (us10, eu10, etc). |
| | `btp_list_directories` | List directories in the global account. |
| **Security** | `btp_list_users` | List global account users. |
| | `btp_assign_role_collection` | Grant roles (e.g., Admin) to a user. |
| **Resources** | `btp_list_entitlements` | Check available service plans/quotas. |
| | `btp_remove_entitlement` | Remove an assigned entitlement from a subaccount. |
| | `btp_list_service_instances` | List active services in a subaccount. |
| | `btp_list_environment_instances` | List environments like Cloud Foundry or Kyma. |
| | `btp_list_subscriptions` | List SaaS application subscriptions. |

---

## 💬 Usage Examples

- *"Check if my BTP session is still active using ping."*
- *"Show me all subaccounts in region eu10."*
- *"Assign the 'Subaccount Admin' role to colleague@example.com."*
- *"Create a development subaccount named 'Internal-Alpha' in us10."*

---

## 🆘 Troubleshooting

**Authentication Error (❌ AUTHENTICATION ERROR)**
If you see this, your BTP CLI session has expired.
1. Clear the error in the AI chat.
2. Run `btp login` in your terminal.
3. Refresh the AI session.

**CLI Not Found (⚠️ BTP CLI not found)**
Ensure `btp` is in your PATH. On macOS/Linux, try `ln -s /path/to/btp /usr/local/bin/btp`.

---

## 🏗️ System Design

The server follows a layered architecture to ensure separation of concerns and maximum stability:

*   **Tool Layer (`server.py`)**: Uses `FastMCP` to register Python functions as MCP tools. Implements strict Pydantic validation and maps technical exceptions to human-readable markdown tips.
*   **Service Layer (`btp_cli.py`)**: Orchestrates command execution. Manages the state of the CLI path, handles binary auto-discovery, and implements the "Deep JSON Recovery" algorithm.
*   **Execution Layer (`subprocess`)**: Interacts directly with the OS. Uses hardened environments (`CI=true`) and standard error redirection to maintain security and non-interactivity.
*   **Utility Layer (`utils.py`)**: Centralizes cross-cutting concerns like logging to `stderr` and custom domain-specific exceptions.

## 🔄 Control Flow

1.  **Request Intake**: The AI client (e.g., Antigravity) sends a JSON-RPC request to a registered tool (e.g., `btp_list_subaccounts`).
2.  **Pre-Validation**: The Tool Layer hydrates parameters and performs regex-based technical validation (IDs/GUIDs).
3.  **Execution**: The Service Layer constructs a safe CLI command, injecting `--format json` as a global prefix.
4.  **Retry & Recovery**: 
    - If the command times out, it retries with exponential backoff.
    - If the output contains warnings + JSON, the "Deep Recovery" engine extracts the valid payload.
5.  **Error Mapping**: If the CLI returns "Session Expired", the decorator catches it and provides the user with an exact `btp login` command for their specific binary path.
6.  **Structured Response**: The final JSON payload is beautified and returned to the AI as a markdown-formatted string.

---

## 📄 License
MIT License.

## 👤 Author
**Kallol Chakraborty** - [@kallolchakraborty](https://github.com/kallolchakraborty)
