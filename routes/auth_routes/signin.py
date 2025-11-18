from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Auth import supabase

router = APIRouter()

class SignInRequest(BaseModel):
    email: str
    password: str

class SignInResponse(BaseModel):
    user: dict
    session: dict

@router.post("/auth/signin")
def signin(request: SignInRequest):
    """
    Sign in an existing user.
    
    This endpoint:
    1. Authenticates the user with Supabase
    2. Returns the user data and session tokens
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Return user data and session
        return {
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "user_metadata": auth_response.user.user_metadata,
                "created_at": auth_response.user.created_at
            },
            "session": {
                "access_token": auth_response.session.access_token if auth_response.session else None,
                "refresh_token": auth_response.session.refresh_token if auth_response.session else None,
                "expires_at": auth_response.session.expires_at if auth_response.session else None
            } if auth_response.session else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Check if it's an authentication error
        error_message = str(e)
        if "Invalid" in error_message or "credentials" in error_message.lower():
            raise HTTPException(status_code=401, detail="Invalid email or password")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

