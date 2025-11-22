from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from Auth import supabase
import uuid
from db import pool

router = APIRouter()
security = HTTPBearer(auto_error=False)

@router.get("/get_message_mode")
def get_message_mode(credentials=Depends(security)):
    """
    Get the message mode for the user's organization.
    
    This endpoint:
    1. Validates the access token to get the user
    2. Gets the user's organization ID from org_userships table
    3. Returns the message_mode from the orgs table
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

        # Get org_id from org_userships table and then get message_mode from orgs table
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get org_id for the user
                cur.execute("""
                    SELECT org_id
                    FROM org_userships
                    WHERE user_id = %s
                    LIMIT 1
                """, (user_id,))

                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")

                org_id = result[0]

                # Get message_mode and foreign_portal_link for the organization
                cur.execute("""
                    SELECT message_mode, foreign_portal_link
                    FROM orgs
                    WHERE id = %s
                """, (org_id,))

                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found")

                message_mode, foreign_portal_link = result

                # Convert backend format to frontend format
                frontend_message_mode = 'foreign' if message_mode == 'foreign_portal' else 'local'

        return {
            "message_mode": frontend_message_mode,
            "foreign_portal_link": foreign_portal_link,
            "org_id": org_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
