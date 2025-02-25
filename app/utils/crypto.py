from cryptography.fernet import Fernet
import base64
import os
import logging
import binascii

logger = logging.getLogger(__name__)

def generate_encryption_key():
    """Generate a new encryption key."""
    key = binascii.hexlify(os.urandom(32)).decode()
    logger.info("Generated new encryption key")
    return key

def get_encryption_key():
    """Get encryption key from environment."""
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        logger.error("ENCRYPTION_KEY not found in environment variables")
        raise ValueError("ENCRYPTION_KEY environment variable is required")

    try:
        # Validate key length and format
        if len(key) != 64:
            raise ValueError(f'ENCRYPTION_KEY must be 64 characters (got {len(key)})')

        # Try to decode hex
        try:
            key_bytes = bytes.fromhex(key)
        except ValueError:
            raise ValueError('ENCRYPTION_KEY must be a valid hexadecimal string')

        if len(key_bytes) != 32:
            raise ValueError(f'ENCRYPTION_KEY must decode to 32 bytes (got {len(key_bytes)})')

        # Convert to base64 for Fernet
        return base64.urlsafe_b64encode(key_bytes)
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY: {str(e)}")
        raise ValueError(f"Invalid ENCRYPTION_KEY: {str(e)}")

def encrypt_password(password: str) -> str:
    """Encrypt password."""
    if not password:
        raise ValueError("Password cannot be empty")

    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.encrypt(password.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt password: {str(e)}")
        raise ValueError(f"Failed to encrypt password: {str(e)}")

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt password."""
    if not encrypted_password:
        raise ValueError("Encrypted password cannot be empty")

    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt password: {str(e)}")
        raise ValueError(f"Failed to decrypt password: {str(e)}")

def validate_encryption_key() -> bool:
    """Validate that the encryption key is working correctly."""
    try:
        # First verify we can get a valid key
        key = get_encryption_key()
        f = Fernet(key)

        # Test encryption/decryption
        test_text = "test_encryption"
        encrypted = f.encrypt(test_text.encode())
        decrypted = f.decrypt(encrypted).decode()

        if decrypted != test_text:
            logger.error("Encryption validation failed: decrypted text does not match original")
            return False

        return True
    except Exception as e:
        logger.error(f"Encryption key validation failed: {str(e)}")
        return False 