from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Auth import supabase

router = APIRouter()

class PasswordResetRequest(BaseModel):
    email: str
    redirect_to: str

class PasswordUpdateRequest(BaseModel):
    access_token: str
    password: str

@router.post("/auth/reset-password-request")
def reset_password_request(request: PasswordResetRequest):
    """
    Request a password reset email.
    
    This endpoint:
    1. Sends a password reset email to the user
    2. The email contains a link with tokens to reset the password
    """
    try:
        # Request password reset from Supabase
        supabase.auth.reset_password_email(
            email=request.email,
            options={"redirect_to": request.redirect_to}
        )
        
        return {
            "message": "Password reset email sent successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/auth/update-password")
def update_password(request: PasswordUpdateRequest):
    """
    Update user password using the reset token.
    
    This endpoint:
    1. Uses the access token from the reset link to authenticate
    2. Updates the user's password
    """
    try:
        # Set the session with the access token from the reset link
        session_response = supabase.auth.set_session(request.access_token)
        
        if not session_response:
            raise HTTPException(status_code=401, detail="Invalid or expired reset token")
        
        # Update the user's password
        update_response = supabase.auth.update_user({
            "password": request.password
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

