import unittest
from unittest.mock import MagicMock, patch
import json
from btp_mcp_server.btp_cli import BTPCLI, BTPError, BTPCommandError, BTPLoginError

class TestBTPCLI(unittest.TestCase):

    def setUp(self):
        self.btp = BTPCLI(cli_path="/mock/btp")

    @patch("subprocess.run")
    def test_execute_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"key": "value"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = self.btp._execute(["test", "command"])
        self.assertEqual(result, {"key": "value"})

    @patch("subprocess.run")
    def test_create_subaccount(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"id": "new-subaccount-id"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        self.btp.create_subaccount("My Subaccount", "us10", "my-subdomain")
        
        args, _ = mock_run.call_args
        cmd_list = args[0]
        self.assertIn("create", cmd_list)
        self.assertIn("accounts/subaccount", cmd_list)
        self.assertIn("My Subaccount", cmd_list)
        self.assertIn("us10", cmd_list)
        self.assertIn("my-subdomain", cmd_list)

    @patch("subprocess.run")
    def test_entitlements(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "{}"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        self.btp.assign_entitlement("sub-id", "service-x", "plan-y", 5)
        
        args, _ = mock_run.call_args
        cmd_list = args[0]
        self.assertIn("assign", cmd_list)
        self.assertIn("accounts/entitlement", cmd_list)
        self.assertIn("--amount", cmd_list)
        self.assertIn("5", cmd_list)

    @patch("subprocess.run")
    def test_security_tools(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "{}"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        self.btp.assign_role_collection("Admin", "user@test.com")
        
        args, _ = mock_run.call_args
        cmd_list = args[0]
        self.assertIn("assign", cmd_list)
        self.assertIn("security/role-collection", cmd_list)
        self.assertIn("Admin", cmd_list)
        self.assertIn("user@test.com", cmd_list)

    @patch("subprocess.run")
    def test_list_regions(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '[]'
        mock_run.return_value = mock_result
        self.btp.list_regions()
        args, _ = mock_run.call_args
        self.assertIn("accounts/region", args[0])

    @patch("subprocess.run")
    def test_list_environment_instances(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '[]'
        mock_run.return_value = mock_result
        self.btp.list_environment_instances("sub1")
        args, _ = mock_run.call_args
        self.assertIn("accounts/environment-instance", args[0])
        self.assertIn("sub1", args[0])

if __name__ == "__main__":
    unittest.main()
