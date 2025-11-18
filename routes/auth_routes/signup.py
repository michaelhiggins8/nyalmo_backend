from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Auth import supabase
from db import pool
import uuid

router = APIRouter()

class SignUpRequest(BaseModel):
    email: str
    password: str
    org_key: str

class SignUpResponse(BaseModel):
    user: dict
    session: dict
    message: str

@router.post("/auth/signup")
def signup(request: SignUpRequest):
    """
    Sign up a new user with organization validation.
    
    This endpoint:
    1. Validates the organization key exists
    2. Creates a new user in Supabase
    3. Adds the user to the org_userships table
    4. Returns the user data and session
    """
    try:
        # Validate org_key exists in the database using direct PostgreSQL connection
        with pool.connection() as conn:
            result = conn.execute("SELECT id FROM orgs WHERE org_key = %s", (request.org_key,)).fetchone()
            
            if result is None:
                raise HTTPException(status_code=400, detail="Invalid organization key")
            
            org_id = result[0]
        
        # Create user in Supabase with org_id in metadata
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "org_id": org_id
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        user_id = auth_response.user.id
        
        # Add user to org_userships table using direct PostgreSQL connection
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO org_userships (user_id, org_id) VALUES (%s, %s)",
                (user_id, org_id)
            )
            conn.commit()
        
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
            } if auth_response.session else None,
            "message": "Account created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

