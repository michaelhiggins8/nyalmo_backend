from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from Auth import supabase
from db import pool
import uuid

security = HTTPBearer()

router = APIRouter()

@router.get("/share/get_org_key")
def get_org_key(credentials = Depends(security)):
    """
    Fetch the org_key for the authenticated user's organization.
    
    Args:
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing the org_key
    """
    try:
        # Verify authentication
        token = credentials.credentials
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        
        # Get user's org_id from org_userships table and org_key from orgs table
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get org_id from org_userships
                cur.execute(
                    "SELECT org_id FROM org_userships WHERE user_id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for user")
                
                org_id = result[0]
                
                # Fetch org_key from orgs table
                cur.execute(
                    "SELECT org_key FROM orgs WHERE id = %s",
                    (org_id,)
                )
                org_result = cur.fetchone()
                
                if not org_result:
                    raise HTTPException(status_code=404, detail="Organization not found")
                
                org_key = org_result[0]
        
        return {
            "org_key": org_key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching org_key: {str(e)}")

