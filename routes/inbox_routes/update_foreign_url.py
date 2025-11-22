from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from Auth import supabase
from db import pool

router = APIRouter()
security = HTTPBearer(auto_error=False)

class UpdateForeignUrlRequest(BaseModel):
    org_id: str
    foreign_portal_link: str

@router.post("/update_foreign_url")
def update_foreign_url(request: UpdateForeignUrlRequest, credentials=Depends(security)):
    """
    Update the foreign_portal_link for an organization.

    This endpoint:
    1. Validates the access token to get the user
    2. Verifies the user is the owner of the organization
    3. Updates the foreign_portal_link column in the orgs table
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

        # Verify ownership and update foreign_portal_link
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
                    raise HTTPException(status_code=403, detail="Only organization owners can update foreign portal link")

                # Update foreign_portal_link
                cur.execute("""
                    UPDATE orgs
                    SET foreign_portal_link = %s
                    WHERE id = %s
                """, (request.foreign_portal_link, request.org_id))

                if cur.rowcount == 0:
                    raise HTTPException(status_code=500, detail="Failed to update foreign portal link")

        return {
            "message": "Foreign portal link updated successfully",
            "org_id": request.org_id,
            "foreign_portal_link": request.foreign_portal_link
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

