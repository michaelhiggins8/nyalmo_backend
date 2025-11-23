from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from typing import Optional
import uuid
import traceback
from Auth import supabase
from db import pool

router = APIRouter()

security = HTTPBearer(auto_error=False)


@router.get("/fetch_mails")
async def fetch_mails(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
    label: Optional[str] = Query(None),
    credentials=Depends(security)
):
    """
    Fetch mails with pagination and optional label filtering.
    
    Args:
        page: Page number (0-indexed)
        page_size: Number of mails per page (default 10)
        label: Optional label filter (e.g., 'change_request', 'violation_report', 'general_message')
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing:
        - mails: List of mail objects
        - total_count: Total number of mails
        - total_pages: Total number of pages
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
                
                # Calculate offset for pagination
                offset = page * page_size
                limit = page_size
                
                # Build the query based on whether label filter is provided
                if label is not None:
                    # Get total count with label filter
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM mail 
                        WHERE org_id = %s AND label = %s
                    """, (org_id, label))
                    
                    total_count = cur.fetchone()[0]
                    
                    # Get mails with label filter and pagination
                    cur.execute("""
                        SELECT id, created_at, org_id, content, subject, sender_email, sender_id, label, read_at
                        FROM mail
                        WHERE org_id = %s AND label = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (org_id, label, limit, offset))
                else:
                    # Get total count without label filter
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM mail 
                        WHERE org_id = %s
                    """, (org_id,))
                    
                    total_count = cur.fetchone()[0]
                    
                    # Get all mails without label filter and pagination
                    cur.execute("""
                        SELECT id, created_at, org_id, content, subject, sender_email, sender_id, label, read_at
                        FROM mail
                        WHERE org_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (org_id, limit, offset))
                
                mails_data = cur.fetchall()
                print(f"Fetched {len(mails_data)} mails")
                
                # Convert to list of dictionaries
                mails = []
                for idx, mail in enumerate(mails_data):
                    try:
                        mail_dict = {
                            "id": mail[0],
                            "created_at": mail[1].isoformat() if mail[1] else None,
                            "org_id": mail[2],
                            "content": mail[3],
                            "subject": mail[4],
                            "sender_email": mail[5],
                            "sender_id": mail[6],
                            "label": mail[7],
                            "read_at": mail[8].isoformat() if mail[8] else None
                        }
                        mails.append(mail_dict)
                    except Exception as e:
                        print(f"Error processing mail {idx}: {e}")
                        print(f"Mail data: {mail}")
                        raise
                
                # Calculate pagination info
                total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
                
                return {
                    "mails": mails,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "current_page": page
                }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching mails: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching mails: {str(e)}")

