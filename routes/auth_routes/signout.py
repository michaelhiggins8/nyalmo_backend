from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from Auth import supabase

router = APIRouter()
security = HTTPBearer(auto_error=False)

@router.post("/auth/signout")
def signout(credentials=Depends(security)):
    """
    Sign out the current user.
    
    This endpoint:
    1. Validates the access token
    2. Signs out the user from Supabase
    """
    try:
        # Get the token from the Authorization header
        token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None
        
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Sign out from Supabase
        supabase.auth.sign_out()
        
        return {
            "message": "Signed out successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

