import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from fastapi import HTTPException, status
import secrets
import string

from app.config import get_settings

settings = get_settings()

class GoogleOAuthService:
    def __init__(self):
        self.client_id = settings["GOOGLE_CLIENT_ID"]
        self.client_secret = settings["GOOGLE_CLIENT_SECRET"]
        self.redirect_uri = settings["GOOGLE_REDIRECT_URI"]
        
        # OAuth scopes
        self.scopes = [
            "openid",
            "email", 
            "profile"
        ]
    
    def generate_auth_url(self, state=None):
        """Generate Google OAuth authorization URL"""
        try:
            # Create flow instance
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Generate state if not provided
            if not state:
                state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'
            )
            
            return auth_url, state
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate auth URL: {str(e)}"
            )
    
    async def verify_google_token(self, code, state=None):
        """Verify Google OAuth code and get user info"""
        try:
            # Create flow instance
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for token
            flow.fetch_token(code=code)
            
            # Get credentials
            credentials = flow.credentials
            
            # Verify ID token
            request = google_requests.Request()
            id_info = id_token.verify_oauth2_token(
                credentials.id_token, 
                request, 
                self.client_id
            )
            
            # Extract user information
            user_info = {
                "google_id": id_info.get("sub"),
                "email": id_info.get("email"),
                "email_verified": id_info.get("email_verified", False),
                "full_name": id_info.get("name", ""),
                "first_name": id_info.get("given_name", ""),
                "last_name": id_info.get("family_name", ""),
                "profile_picture": id_info.get("picture", ""),
                "locale": id_info.get("locale", "en")
            }
            
            return user_info
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to verify Google token: {str(e)}"
            )
    
    async def verify_google_id_token(self, id_token_str):
        """Verify Google ID token from frontend"""
        try:
            # Verify ID token
            request = google_requests.Request()
            id_info = id_token.verify_oauth2_token(
                id_token_str, 
                request, 
                self.client_id
            )
            
            # Extract user information
            user_info = {
                "google_id": id_info.get("sub"),
                "email": id_info.get("email"),
                "email_verified": id_info.get("email_verified", False),
                "full_name": id_info.get("name", ""),
                "first_name": id_info.get("given_name", ""),
                "last_name": id_info.get("family_name", ""),
                "profile_picture": id_info.get("picture", ""),
                "locale": id_info.get("locale", "en")
            }
            
            return user_info
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to verify Google ID token: {str(e)}"
            )
    
    async def get_user_info_from_token(self, access_token):
        """Get user info using access token"""
        try:
            # Call Google's userinfo endpoint
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from Google"
                )
            
            user_data = response.json()
            
            user_info = {
                "google_id": user_data.get("id"),
                "email": user_data.get("email"),
                "email_verified": user_data.get("verified_email", False),
                "full_name": user_data.get("name", ""),
                "first_name": user_data.get("given_name", ""),
                "last_name": user_data.get("family_name", ""),
                "profile_picture": user_data.get("picture", ""),
                "locale": user_data.get("locale", "en")
            }
            
            return user_info
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info: {str(e)}"
            )

# Create Google OAuth service instance
google_oauth_service = GoogleOAuthService()
