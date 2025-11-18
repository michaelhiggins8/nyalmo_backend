from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from Auth import supabase
from db import pool
import uuid

security = HTTPBearer()

router = APIRouter()

@router.post("/share/refresh_org_key")
def refresh_org_key(credentials = Depends(security)):
    """
    Generate a new org_key (UUID) for the authenticated user's organization.
    This invalidates the old links and creates new ones.
    
    Args:
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing the new org_key
    """
    try:
        # Verify authentication
        token = credentials.credentials
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        
        # Get user's org_id and update org_key
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
                
                # Try to call the RPC function first (if it exists)
                try:
                    cur.execute(
                        "SELECT update_org_key(%s)",
                        (user_id,)
                    )
                    new_org_key = cur.fetchone()
                    
                    if new_org_key:
                        conn.commit()
                        return {
                            "org_key": new_org_key[0]
                        }
                except Exception as rpc_error:
                    # If RPC fails, fallback to manual update
                    print(f"RPC failed, using fallback: {rpc_error}")
                    pass
                
                # Fallback: Generate new UUID and update manually
                new_uuid = str(uuid.uuid4())
                
                cur.execute(
                    "UPDATE orgs SET org_key = %s WHERE id = %s RETURNING org_key",
                    (new_uuid, org_id)
                )
                updated_result = cur.fetchone()
                
                if not updated_result:
                    raise HTTPException(status_code=500, detail="Failed to update org_key")
                
                conn.commit()
                
                return {
                    "org_key": updated_result[0]
                }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing org_key: {str(e)}")

