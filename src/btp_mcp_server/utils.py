import logging
import sys
from typing import Optional

# --- Logging Configuration ---
# We configure the root logger to output to stderr.
# This is crucial for MCP (Model Context Protocol) servers using the stdio transport,
# as it ensures that log messages do not interfere with the JSON-RPC messages 
# being exchanged over stdout/stdin.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

# Standard logger for this project
logger = logging.getLogger("btp-mcp-server")


class BTPError(Exception):
    """
    Base exception class for all SAP BTP CLI related errors.
    
    Attributes:
        message (str): A human-readable error message.
        return_code (int, optional): The exit code from the BTP CLI process.
        stdout (str, optional): The standard output from the failed command.
        stderr (str, optional): The error output from the failed command.
    """

    def __init__(self, message: str, return_code: Optional[int] = None, stdout: Optional[str] = None, stderr: Optional[str] = None):
        super().__init__(message)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class BTPLoginError(BTPError):
    """
    Raised specifically when a command fails because the user is not 
    authenticated or the session has expired in the BTP CLI.
    """
    pass


class BTPCommandError(BTPError):
    """
    Raised when the BTP CLI returns a non-zero exit code due to 
    invalid arguments, missing permissions, or server-side issues.
    """
    pass

