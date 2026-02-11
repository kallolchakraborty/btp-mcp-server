# SAP BTP MCP Server

A Model Context Protocol (MCP) server that provides a natural language interface for the SAP Business Technology Platform (BTP) CLI. 
This allows LLMs (like Claude, Gemini, etc.) to manage your BTP accounts, security, and environments directly.

## Features

- **Protocol**: Built on the official Model Context Protocol (MCP).
- **Security**: 
  - Runs locally on your machine.
  - Uses your existing BTP CLI authentication.
  - No credentials are stored in the server.
- **Robustness**: 
  - Validates commands against allowed BTP verbs.
  - Parses JSON output for reliable data interchange.
- **Scalability**: Generic `btp_execute_command` tool supports current and future BTP CLI commands.

## Prerequisites

1.  **SAP BTP CLI**: You must have the `btp` CLI installed and available in your system PATH.
    - [Download from SAP Development Tools](https://tools.hana.ondemand.com/#cloud)
    - Verify installation: `btp --version`
2.  **Authentication**: You must be logged in to the BTP CLI.
    - Run: `btp login` (and follow the prompts)
3.  **Python**: Version 3.10 or higher.
4.  **UV** (Optional but recommended): For easy tool management.

## Installation

### Using uv (Recommended)

```bash
uv tool install --from . btp-mcp-server
```

### Manual Installation

```bash
pip install .
```

## Configuration

Add the server to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "btp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/btp-mcp-server",
        "run",
        "btp-mcp-server"
      ]
    }
  }
}
```

## Usage

Once connected, you can ask your LLM to perform BTP tasks:

- "List all my subaccounts in the global account"
- "Create a new subaccount named 'DevTest' in region 'us10'"
- "Show me the details for subaccount ending in '...3a'"
- "Assign the 'Global Account Administrator' role to 'colleague@example.com'"

## Development

### Running Tests

To run the unit tests (which mock the BTP CLI interactions):

```bash
PYTHONPATH=src python3 -m unittest discover tests
```

## License

MIT License. See LICENSE file for details.

## Author

Kallol Chakraborty
