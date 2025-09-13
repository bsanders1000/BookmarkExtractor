#!/usr/bin/env python3
"""
Secure credential management functionality
"""
import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Manages secure storage and retrieval of browser credentials
    """
    
    def __init__(self, storage_path: Path):
        """
        Initialize the credential manager
        
        Args:
            storage_path: Path to the encrypted credential file
        """
        self.storage_path = storage_path
        self.credentials = {}
        self.fernet = None
        self.initialized = False
    
    def initialize(self, master_password: str) -> bool:
        """
        Initialize the credential manager with a master password
        
        Args:
            master_password: Master password for encrypting/decrypting credentials
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Generate a random salt if it doesn't exist
            salt_path = self.storage_path.with_suffix('.salt')
            if not salt_path.exists():
                salt = os.urandom(16)
                with open(salt_path, 'wb') as f:
                    f.write(salt)
            else:
                with open(salt_path, 'rb') as f:
                    salt = f.read()
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            self.fernet = Fernet(key)
            
            # Load existing credentials if available
            if self.storage_path.exists():
                try:
                    self._load_credentials()
                except Exception as e:
                    logger.error(f"Failed to decrypt credentials: {e}")
                    return False
            
            self.initialized = True
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize credential manager: {e}")
            return False
    
    def store_credentials(self, browser_id: str, username: str, password: str) -> bool:
        """
        Store credentials for a browser
        
        Args:
            browser_id: Unique identifier for the browser
            username: Username for the browser profile
            password: Password for the browser profile
            
        Returns:
            bool: True if credentials stored successfully, False otherwise
        """
        if not self.initialized:
            logger.error("Credential manager not initialized")
            return False
        
        try:
            self.credentials[browser_id] = {
                'username': username,
                'password': password
            }
            return self._save_credentials()
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False
    
    def get_credentials(self, browser_id: str) -> Optional[Dict[str, str]]:
        """
        Get credentials for a browser
        
        Args:
            browser_id: Unique identifier for the browser
            
        Returns:
            Optional[Dict[str, str]]: Dictionary with username and password, or None if not found
        """
        if not self.initialized:
            logger.error("Credential manager not initialized")
            return None
        
        return self.credentials.get(browser_id)
    
    def has_credentials(self, browser_id: str) -> bool:
        """
        Check if credentials exist for a browser
        
        Args:
            browser_id: Unique identifier for the browser
            
        Returns:
            bool: True if credentials exist, False otherwise
        """
        if not self.initialized:
            return False
        
        return browser_id in self.credentials
    
    def _save_credentials(self) -> bool:
        """
        Save credentials to encrypted storage
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.initialized:
            return False
        
        try:
            data = json.dumps(self.credentials).encode()
            encrypted_data = self.fernet.encrypt(data)
            
            with open(self.storage_path, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    def _load_credentials(self) -> bool:
        """
        Load credentials from encrypted storage
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not self.initialized:
            return False
        
        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()
            
            data = self.fernet.decrypt(encrypted_data)
            self.credentials = json.loads(data.decode())
            
            return True
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return False