from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from typing import Optional
import uuid
import traceback
from Auth import supabase
from db import pool

router = APIRouter()

security = HTTPBearer(auto_error=False)


@router.get("/fetch_rulings")
async def fetch_rulings(
    page: int = Query(0, ge=0),
    page_size: int = Query(9, ge=1, le=100),
    credentials=Depends(security)
):
    """
    Fetch rulings with pagination support.
    
    For admin users: Returns all rulings for their organization
    For non-admin users: Returns only rulings where they are the applicant
    
    Args:
        page: Page number (0-indexed)
        page_size: Number of rulings per page (default 9)
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing:
        - rulings: List of ruling objects
        - total_count: Total number of rulings
        - total_pages: Total number of pages
        - has_more: Whether there are more pages
    """
    
    # Check if token is valid
    token = credentials.credentials if (credentials and credentials.credentials != "undefined") else None
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        print(f"User authenticated: {user_id}")
    except Exception as e:
        print(f"Token is invalid: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # First, get org_id from org_userships
                print(f"Querying org for user_id: {user_id}")
                cur.execute("""
                    SELECT org_id 
                    FROM org_userships 
                    WHERE user_id = %s 
                    LIMIT 1
                """, (user_id,))
                
                org_result = cur.fetchone()
                print(f"Org result: {org_result}")
                
                if not org_result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")
                
                org_id = org_result[0]
                print(f"User org_id: {org_id}")
                
                # Check if user is board member (owner of the organization)
                cur.execute("""
                    SELECT owner_id 
                    FROM orgs 
                    WHERE id = %s
                """, (org_id,))
                
                owner_result = cur.fetchone()
                if not owner_result:
                    raise HTTPException(status_code=404, detail="Organization not found")
                
                owner_id = owner_result[0]
                is_board = (owner_id == user_id)
                print(f"Owner ID: {owner_id}, User is board: {is_board}")
                
                # Calculate offset for pagination
                offset = page * page_size
                limit = page_size
                
                if is_board:
                    # Admin logic: Fetch rulings for the organization
                    if not org_id:
                        raise HTTPException(status_code=400, detail="No organization found for this user")
                    
                    # Get total count
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM rulings 
                        WHERE org_id = %s
                    """, (org_id,))
                    
                    total_count = cur.fetchone()[0]
                    
                    # Get rulings with pagination
                    cur.execute("""
                        SELECT created_at, status, content, subject, notes, applicant_email
                        FROM rulings
                        WHERE org_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (org_id, limit, offset))
                    
                else:
                    # Non-admin logic: Fetch rulings where user is the applicant
                    # Get total count
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM rulings 
                        WHERE applicant_id = %s
                    """, (user_id,))
                    
                    total_count = cur.fetchone()[0]
                    
                    # Get rulings with pagination
                    cur.execute("""
                        SELECT created_at, status, content, subject, notes, applicant_email
                        FROM rulings
                        WHERE applicant_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (user_id, limit, offset))
                
                rulings_data = cur.fetchall()
                print(f"Fetched {len(rulings_data)} rulings")
                
                # Convert to list of dictionaries
                rulings = []
                for idx, ruling in enumerate(rulings_data):
                    try:
                        ruling_dict = {
                            "created_at": ruling[0].isoformat() if ruling[0] else None,
                            "status": ruling[1],
                            "content": ruling[2],
                            "subject": ruling[3],
                            "notes": ruling[4],
                            "applicant_email": ruling[5]
                        }
                        rulings.append(ruling_dict)
                    except Exception as e:
                        print(f"Error processing ruling {idx}: {e}")
                        print(f"Ruling data: {ruling}")
                        raise
                
                # Calculate pagination info
                total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
                has_more = total_count > (offset + page_size)
                
                return {
                    "rulings": rulings,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "current_page": page
                }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching rulings: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching rulings: {str(e)}")

