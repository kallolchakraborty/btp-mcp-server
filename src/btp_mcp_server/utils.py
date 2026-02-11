import logging
import sys

# Configure logging to write to stderr so it doesn't interfere with stdio transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("btp-mcp-server")


class BTPError(Exception):
    """Base exception for BTP CLI errors."""

    def __init__(self, message: str, return_code: int = None, stdout: str = None, stderr: str = None):
        super().__init__(message)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class BTPLoginError(BTPError):
    """Raised when the user is not logged in."""
    pass


class BTPCommandError(BTPError):
    """Raised when the CLI returns a non-zero exit code."""
    pass
