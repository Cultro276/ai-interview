"""
Enterprise Data Encryption at Rest
Field-level encryption for sensitive personal data
GDPR/KVKK compliance for data protection
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import TypeDecorator, String, Text
from sqlalchemy.types import UserDefinedType
import base64
import os
from typing import Optional
import logging


class EncryptionManager:
    """
    Centralized encryption management for sensitive data
    Uses Fernet (AES 128 in CBC mode) for symmetric encryption
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")
        if not self.master_key:
            # Generate a new key for development (store securely in production)
            self.master_key = Fernet.generate_key().decode()
            logging.warning("Generated new encryption key - store securely in production!")
        
        self._cipher = None
    
    def _get_cipher(self) -> Fernet:
        """
        Get or create cipher instance
        """
        if self._cipher is None:
            # Ensure master key is available
            if not self.master_key:
                raise ValueError("Encryption master key not available")
            
            # Derive key from master key using PBKDF2
            password = self.master_key.encode()
            salt = b"interview_platform_salt"  # In production, use random salt per field
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self._cipher = Fernet(key)
        
        return self._cipher
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        """
        if not plaintext:
            return plaintext
        
        try:
            cipher = self._get_cipher()
            encrypted = cipher.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logging.error(f"Encryption failed: {e}")
            raise ValueError("Encryption failed")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        """
        if not ciphertext:
            return ciphertext
        
        try:
            cipher = self._get_cipher()
            encrypted_data = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted = cipher.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed")


# Global encryption manager instance
encryption_manager = EncryptionManager()


class EncryptedType(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted fields
    Automatically encrypts/decrypts data when saving/loading from database
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, max_length: Optional[int] = None):
        self.max_length = max_length
        super().__init__()
    
    def process_bind_param(self, value, dialect):
        """
        Encrypt value before storing in database
        """
        if value is None:
            return value
        
        if self.max_length and len(value) > self.max_length:
            raise ValueError(f"Value too long (max {self.max_length} characters)")
        
        return encryption_manager.encrypt(str(value))
    
    def process_result_value(self, value, dialect):
        """
        Decrypt value after loading from database
        """
        if value is None:
            return value
        
        return encryption_manager.decrypt(value)


class HashType(TypeDecorator):
    """
    SQLAlchemy custom type for hashed fields (one-way)
    Used for data that needs to be searchable but not readable
    """
    
    impl = String(64)  # SHA-256 hash length
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """
        Hash value before storing in database
        """
        if value is None:
            return value
        
        import hashlib
        return hashlib.sha256(str(value).encode('utf-8')).hexdigest()
    
    def process_result_value(self, value, dialect):
        """
        Return hash as-is (cannot decrypt)
        """
        return value


class TokenizedType(TypeDecorator):
    """
    SQLAlchemy custom type for tokenized fields
    Replaces sensitive data with reversible tokens
    """
    
    impl = String(64)
    cache_ok = True
    
    def __init__(self, token_prefix: str = "tok_"):
        self.token_prefix = token_prefix
        self._token_store = {}  # In production, use external token vault
        super().__init__()
    
    def process_bind_param(self, value, dialect):
        """
        Tokenize value before storing in database
        """
        if value is None:
            return value
        
        # Generate token
        import secrets
        token = f"{self.token_prefix}{secrets.token_urlsafe(32)}"
        
        # Store mapping (in production, use secure token vault)
        self._token_store[token] = encryption_manager.encrypt(str(value))
        
        return token
    
    def process_result_value(self, value, dialect):
        """
        Detokenize value after loading from database
        """
        if value is None or not value.startswith(self.token_prefix):
            return value
        
        # Retrieve original value (in production, query token vault)
        encrypted_value = self._token_store.get(value)
        if encrypted_value:
            return encryption_manager.decrypt(encrypted_value)
        
        return None


class EncryptedEmail(EncryptedType):
    """
    Specialized encrypted type for email addresses
    """
    
    def __init__(self):
        super().__init__(max_length=254)  # RFC 5321 limit
    
    def process_bind_param(self, value, dialect):
        """
        Validate and encrypt email
        """
        if value is None:
            return value
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError("Invalid email format")
        
        return super().process_bind_param(value.lower(), dialect)


class EncryptedPhone(EncryptedType):
    """
    Specialized encrypted type for phone numbers
    """
    
    def __init__(self):
        super().__init__(max_length=20)
    
    def process_bind_param(self, value, dialect):
        """
        Validate and encrypt phone number
        """
        if value is None:
            return value
        
        # Validate phone format
        import re
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, value):
            raise ValueError("Invalid phone number format")
        
        return super().process_bind_param(value, dialect)


class EncryptedPersonalData(EncryptedType):
    """
    Specialized encrypted type for personal data (names, addresses, etc.)
    """
    
    def __init__(self, max_length: int = 255):
        super().__init__(max_length=max_length)
    
    def process_bind_param(self, value, dialect):
        """
        Validate and encrypt personal data
        """
        if value is None:
            return value
        
        # Basic validation for personal data
        if len(value.strip()) < 2:
            raise ValueError("Personal data too short")
        
        return super().process_bind_param(value.strip(), dialect)


def encrypt_existing_data():
    """
    Utility function to encrypt existing plaintext data in database
    Run this during migration to encryption
    """
    from src.db.session import async_session_factory
    from src.db.models.candidate import Candidate
    from sqlalchemy import text
    import asyncio
    
    async def _encrypt_candidates():
        async with async_session_factory() as session:
            # Get all candidates with plaintext data
            result = await session.execute(
                text("SELECT id, name, email, phone FROM candidates WHERE name NOT LIKE 'gAAAAAB%'")
            )
            candidates = result.fetchall()
            
            for candidate in candidates:
                # Encrypt sensitive fields
                encrypted_name = encryption_manager.encrypt(candidate.name)
                encrypted_email = encryption_manager.encrypt(candidate.email)
                encrypted_phone = encryption_manager.encrypt(candidate.phone) if candidate.phone else None
                
                # Update with encrypted data
                await session.execute(
                    text("""
                        UPDATE candidates 
                        SET name = :name, email = :email, phone = :phone 
                        WHERE id = :id
                    """),
                    {
                        "name": encrypted_name,
                        "email": encrypted_email,
                        "phone": encrypted_phone,
                        "id": candidate.id
                    }
                )
            
            await session.commit()
            logging.info(f"Encrypted data for {len(candidates)} candidates")
    
    # Run encryption migration
    asyncio.run(_encrypt_candidates())


def create_encryption_key() -> str:
    """
    Generate new encryption key for production deployment
    Store this key securely (AWS KMS, Azure Key Vault, etc.)
    """
    return Fernet.generate_key().decode()


def rotate_encryption_key(old_key: str, new_key: str):
    """
    Rotate encryption keys for existing data
    """
    old_manager = EncryptionManager(old_key)
    new_manager = EncryptionManager(new_key)
    
    # Implementation would decrypt with old key and re-encrypt with new key
    # This is a critical operation that should be done with care
    pass


class EncryptionConfig:
    """
    Configuration for field-level encryption
    """
    
    # Define which fields should be encrypted
    ENCRYPTED_FIELDS = {
        'candidates': ['name', 'email', 'phone'],
        'users': ['first_name', 'last_name', 'email'],
        'candidate_profiles': ['phone', 'linkedin_url'],
        'conversation_messages': ['content'],  # Interview transcripts
    }
    
    # Define which fields should be hashed (searchable but not readable)
    HASHED_FIELDS = {
        'candidates': ['email_hash'],  # For duplicate detection
        'users': ['email_hash'],
    }
    
    # Define which fields should be tokenized
    TOKENIZED_FIELDS = {
        'candidates': ['resume_url'],  # File paths
        'interviews': ['audio_url', 'video_url'],
    }
    
    @classmethod
    def is_field_encrypted(cls, table: str, field: str) -> bool:
        """
        Check if a field should be encrypted
        """
        return field in cls.ENCRYPTED_FIELDS.get(table, [])
    
    @classmethod
    def is_field_hashed(cls, table: str, field: str) -> bool:
        """
        Check if a field should be hashed
        """
        return field in cls.HASHED_FIELDS.get(table, [])
    
    @classmethod
    def is_field_tokenized(cls, table: str, field: str) -> bool:
        """
        Check if a field should be tokenized
        """
        return field in cls.TOKENIZED_FIELDS.get(table, [])
