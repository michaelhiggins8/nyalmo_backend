from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from Auth import supabase

router = APIRouter()
security = HTTPBearer(auto_error=False)

class RefreshSessionRequest(BaseModel):
    refresh_token: str

@router.get("/auth/session")
def get_session(credentials=Depends(security)):
    """
    Get the current session information.
    
    This endpoint:
    1. Validates the access token
    2. Returns the current user and session data
    """
    try:
        # Get the token from the Authorization header
        token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None
        
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate token and get user
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return {
            "user": {
                "id": user_response.user.id,
                "email": user_response.user.email,
                "user_metadata": user_response.user.user_metadata,
                "created_at": user_response.user.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/auth/refresh")
def refresh_session(request: RefreshSessionRequest):
    """
    Refresh the session using a refresh token.
    
    This endpoint:
    1. Uses the refresh token to get a new access token
    2. Returns the new session data
    """
    try:
        # Refresh the session
        session_response = supabase.auth.refresh_session(request.refresh_token)
        
        if not session_response.session:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
        return {
            "user": {
                "id": session_response.user.id,
                "email": session_response.user.email,
                "user_metadata": session_response.user.user_metadata,
                "created_at": session_response.user.created_at
            } if session_response.user else None,
            "session": {
                "access_token": session_response.session.access_token,
                "refresh_token": session_response.session.refresh_token,
                "expires_at": session_response.session.expires_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to refresh session: {str(e)}")

