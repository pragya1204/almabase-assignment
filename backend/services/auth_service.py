import os
from supabase import create_client, Client
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# Initialize Supabase client with the service role key for backend operations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing Supabase environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Use HTTPBearer to extract the Authorization header from incoming requests
security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    """
    Validates the JWT token with Supabase and returns the current user.
    """
    token = credentials.credentials
    try:
        # Validate the token by fetching the user details from Supabase Auth
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            # Reject unauthenticated access
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
        return User(id=user_response.user.id, email=user_response.user.email)
        
    except Exception as e:
        # Return 401 Unauthorized for expired tokens or invalid credentials
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")