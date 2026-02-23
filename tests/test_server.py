import unittest
from unittest.mock import MagicMock, patch
import json
from btp_mcp_server.server import (
    btp_ping, btp_list_subaccounts, btp_get_subaccount, 
    btp_create_subaccount, btp_get_global_account, handle_btp_errors
)
from btp_mcp_server.btp_cli import BTPLoginError, BTPCommandError, BTPError

class TestServerTools(unittest.TestCase):

    @patch("btp_mcp_server.server.cli")
    def test_btp_ping_success(self, mock_cli):
        mock_cli.ping.return_value = True
        result = btp_ping()
        self.assertIn("✅ Success", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_ping_login_error(self, mock_cli):
        mock_cli.ping.side_effect = BTPLoginError("Not logged in", 1, "", "Please log in")
        result = btp_ping()
        self.assertIn("❌ AUTHENTICATION ERROR", result)
        self.assertIn("btp login", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_list_subaccounts(self, mock_cli):
        mock_cli.list_subaccounts.return_value = {"items": [{"id": "sub1", "name": "Sub 1"}]}
        result = btp_list_subaccounts()
        data = json.loads(result)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "sub1")

    @patch("btp_mcp_server.server.cli")
    def test_btp_get_subaccount_invalid_id(self, mock_cli):
        result = btp_get_subaccount(subaccount_id="invalid id!")
        self.assertIn("❌ Error: Invalid subaccount ID format", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_create_subaccount_validation(self, mock_cli):
        # Empty display name
        result = btp_create_subaccount(display_name="", region="us10", subdomain="test")
        self.assertIn("❌ Error: display_name cannot be empty", result)
        
        # Invalid subdomain
        result = btp_create_subaccount(display_name="Test", region="us10", subdomain="Invalid_Subdomain")
        self.assertIn("❌ Error: subdomain must be lowercase", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_get_global_account(self, mock_cli):
        mock_cli.get_global_account.return_value = {"name": "Global Admin"}
        result = btp_get_global_account()
        self.assertIn("Global Admin", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_list_regions(self, mock_cli):
        mock_cli.list_regions.return_value = [{"name": "us10"}]
        from btp_mcp_server.server import btp_list_regions
        result = btp_list_regions()
        self.assertIn("us10", result)

    @patch("btp_mcp_server.server.cli")
    def test_btp_list_environment_instances(self, mock_cli):
        mock_cli.list_environment_instances.return_value = [{"id": "env1"}]
        from btp_mcp_server.server import btp_list_environment_instances
        result = btp_list_environment_instances("sub1")
        self.assertIn("env1", result)

if __name__ == "__main__":
    unittest.main()
