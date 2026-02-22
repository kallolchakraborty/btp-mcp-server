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
| **Security** | `btp_list_users` | List global account users. |
| | `btp_assign_role_collection` | Grant roles (e.g., Admin) to a user. |
| **Resources** | `btp_list_entitlements` | Check available service plans/quotas. |
| | `btp_list_service_instances` | List active services in a subaccount. |

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

## 📄 License
MIT License.

## 👤 Author
**Kallol Chakraborty** - [@kallolchakraborty](https://github.com/kallolchakraborty)
