from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from Auth import supabase

router = APIRouter()
security = HTTPBearer(auto_error=False)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/auth/change-password")
def change_password(request: ChangePasswordRequest, credentials=Depends(security)):
    """
    Change user password with current password verification.
    
    This endpoint:
    1. Validates the access token to get the user
    2. Verifies the current password by attempting to sign in
    3. Updates the password
    """
    try:
        # Get the token from the Authorization header
        token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None
        
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get user from token
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user_email = user_response.user.email
        
        # Verify current password by attempting to sign in
        try:
            verify_response = supabase.auth.sign_in_with_password({
                "email": user_email,
                "password": request.current_password
            })
            
            if not verify_response.user:
                raise HTTPException(status_code=401, detail="Current password is incorrect")
        except Exception as e:
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Update the password
        update_response = supabase.auth.update_user({
            "password": request.new_password
        })
        
        if not update_response.user:
            raise HTTPException(status_code=400, detail="Failed to update password")
        
        return {
            "message": "Password updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

