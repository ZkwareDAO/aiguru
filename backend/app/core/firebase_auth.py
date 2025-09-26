"""Firebase Authentication integration."""

import json
import logging
from typing import Dict, Optional

import firebase_admin
from firebase_admin import auth, credentials
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FirebaseUser(BaseModel):
    """Firebase user model."""
    uid: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    phone_number: Optional[str] = None
    disabled: bool = False
    custom_claims: Dict = {}


class FirebaseAuthManager:
    """Firebase Authentication manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self._app: Optional[firebase_admin.App] = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Firebase Admin SDK."""
        if self._initialized:
            return True
        
        try:
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                self._app = firebase_admin.get_app()
                self._initialized = True
                logger.info("Firebase Admin SDK already initialized")
                return True
            
            # Get Firebase configuration from environment
            firebase_config = self._get_firebase_config()
            if not firebase_config:
                logger.warning("Firebase configuration not found")
                return False
            
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(firebase_config)
            self._app = firebase_admin.initialize_app(cred)
            self._initialized = True
            
            logger.info("Firebase Admin SDK initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            return False
    
    def _get_firebase_config(self) -> Optional[Dict]:
        """Get Firebase configuration from environment variables."""
        try:
            # Check if we have all required Firebase environment variables
            required_vars = [
                'FIREBASE_PROJECT_ID',
                'FIREBASE_CLIENT_EMAIL', 
                'FIREBASE_PRIVATE_KEY'
            ]
            
            config_values = {}
            for var in required_vars:
                value = getattr(self.settings, var, None)
                if not value:
                    logger.warning(f"Missing Firebase configuration: {var}")
                    return None
                config_values[var] = value
            
            # Create Firebase service account configuration
            firebase_config = {
                "type": "service_account",
                "project_id": config_values['FIREBASE_PROJECT_ID'],
                "client_email": config_values['FIREBASE_CLIENT_EMAIL'],
                "private_key": config_values['FIREBASE_PRIVATE_KEY'].replace('\\n', '\n'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{config_values['FIREBASE_CLIENT_EMAIL']}"
            }
            
            return firebase_config
            
        except Exception as e:
            logger.error(f"Error creating Firebase configuration: {e}")
            return None
    
    async def verify_token(self, id_token: str) -> Optional[FirebaseUser]:
        """Verify Firebase ID token and return user information."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            
            # Get user information
            uid = decoded_token['uid']
            user_record = auth.get_user(uid)
            
            # Create FirebaseUser object
            firebase_user = FirebaseUser(
                uid=user_record.uid,
                email=user_record.email,
                email_verified=user_record.email_verified,
                display_name=user_record.display_name,
                photo_url=user_record.photo_url,
                phone_number=user_record.phone_number,
                disabled=user_record.disabled,
                custom_claims=user_record.custom_claims or {}
            )
            
            return firebase_user
            
        except auth.InvalidIdTokenError:
            logger.warning("Invalid Firebase ID token")
            return None
        except auth.ExpiredIdTokenError:
            logger.warning("Expired Firebase ID token")
            return None
        except Exception as e:
            logger.error(f"Error verifying Firebase token: {e}")
            return None
    
    async def create_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        email_verified: bool = False
    ) -> Optional[FirebaseUser]:
        """Create a new Firebase user."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=email_verified
            )
            
            firebase_user = FirebaseUser(
                uid=user_record.uid,
                email=user_record.email,
                email_verified=user_record.email_verified,
                display_name=user_record.display_name,
                photo_url=user_record.photo_url,
                phone_number=user_record.phone_number,
                disabled=user_record.disabled,
                custom_claims=user_record.custom_claims or {}
            )
            
            logger.info(f"Created Firebase user: {user_record.uid}")
            return firebase_user
            
        except auth.EmailAlreadyExistsError:
            logger.warning(f"Firebase user with email {email} already exists")
            return None
        except Exception as e:
            logger.error(f"Error creating Firebase user: {e}")
            return None
    
    async def update_user(
        self,
        uid: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        email_verified: Optional[bool] = None,
        disabled: Optional[bool] = None
    ) -> Optional[FirebaseUser]:
        """Update Firebase user information."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            update_data = {}
            if email is not None:
                update_data['email'] = email
            if display_name is not None:
                update_data['display_name'] = display_name
            if email_verified is not None:
                update_data['email_verified'] = email_verified
            if disabled is not None:
                update_data['disabled'] = disabled
            
            user_record = auth.update_user(uid, **update_data)
            
            firebase_user = FirebaseUser(
                uid=user_record.uid,
                email=user_record.email,
                email_verified=user_record.email_verified,
                display_name=user_record.display_name,
                photo_url=user_record.photo_url,
                phone_number=user_record.phone_number,
                disabled=user_record.disabled,
                custom_claims=user_record.custom_claims or {}
            )
            
            logger.info(f"Updated Firebase user: {uid}")
            return firebase_user
            
        except auth.UserNotFoundError:
            logger.warning(f"Firebase user not found: {uid}")
            return None
        except Exception as e:
            logger.error(f"Error updating Firebase user: {e}")
            return None
    
    async def delete_user(self, uid: str) -> bool:
        """Delete Firebase user."""
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            auth.delete_user(uid)
            logger.info(f"Deleted Firebase user: {uid}")
            return True
            
        except auth.UserNotFoundError:
            logger.warning(f"Firebase user not found: {uid}")
            return False
        except Exception as e:
            logger.error(f"Error deleting Firebase user: {e}")
            return False
    
    async def set_custom_claims(self, uid: str, custom_claims: Dict) -> bool:
        """Set custom claims for Firebase user."""
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            auth.set_custom_user_claims(uid, custom_claims)
            logger.info(f"Set custom claims for Firebase user: {uid}")
            return True
            
        except auth.UserNotFoundError:
            logger.warning(f"Firebase user not found: {uid}")
            return False
        except Exception as e:
            logger.error(f"Error setting custom claims: {e}")
            return False


# Global Firebase auth manager instance
firebase_auth_manager = FirebaseAuthManager()
