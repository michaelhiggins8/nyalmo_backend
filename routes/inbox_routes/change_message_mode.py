from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Literal
from Auth import supabase
import uuid
from db import pool

router = APIRouter()
security = HTTPBearer(auto_error=False)

class ChangeMessageModeRequest(BaseModel):
    org_id: str
    message_mode: Literal['local_portal', 'foreign_portal']

@router.post("/change_message_mode")
def change_message_mode(request: ChangeMessageModeRequest, credentials=Depends(security)):
    """
    Change the message mode for an organization.

    This endpoint:
    1. Validates the access token to get the user
    2. Verifies the user is the owner of the organization
    3. Updates the message_mode column in the orgs table
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

        user_id = user_response.user.id

        # Validate message_mode value
        if request.message_mode not in ['local_portal', 'foreign_portal']:
            raise HTTPException(status_code=400, detail="Invalid message_mode. Must be 'local_portal' or 'foreign_portal'")

        # Verify ownership and update message mode
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get owner_id for the organization
                cur.execute("""
                    SELECT owner_id
                    FROM orgs
                    WHERE id = %s
                """, (request.org_id,))

                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found")

                owner_id = result[0]

                # Verify user is the owner
                if str(owner_id) != user_id:
                    raise HTTPException(status_code=403, detail="Only organization owners can change message mode")

                # Update message_mode
                cur.execute("""
                    UPDATE orgs
                    SET message_mode = %s
                    WHERE id = %s
                """, (request.message_mode, request.org_id))

                if cur.rowcount == 0:
                    raise HTTPException(status_code=500, detail="Failed to update message mode")

        return {
            "message": "Message mode updated successfully",
            "org_id": request.org_id,
            "message_mode": request.message_mode
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
