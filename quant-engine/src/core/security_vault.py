import os
from loguru import logger
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityVault:
    """
    Phase 10.1 & 11.1: Cryptographic Key Management.
    Secure vault for loading API credentials and hashing user passwords/API keys.
    """
    
    def __init__(self):
        self._load_secrets()

    def _load_secrets(self):
        """Load and securely store credentials in memory."""
        self._api_key = os.getenv("BROKER_API_KEY", "MOCK_API_KEY_12345")
        self._api_secret = os.getenv("BROKER_API_SECRET", "MOCK_API_SECRET_67890")
        self._account_id = os.getenv("BROKER_ACCOUNT_ID", "MOCK_ACC_001")
        
        if self._api_key == "MOCK_API_KEY_12345":
            logger.warning("Security Vault: Running with MOCK broker credentials.")
        else:
            logger.info("Security Vault: Live broker credentials loaded securely.")

    def get_credentials(self) -> dict:
        """Securely return credentials. Never log this output."""
        return {
            "api_key": self._api_key,
            "api_secret": self._api_secret,
            "account_id": self._account_id
        }

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
