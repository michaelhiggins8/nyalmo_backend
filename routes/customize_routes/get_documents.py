from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from typing import Optional
import uuid
from Auth import supabase
from db import pool

security = HTTPBearer(auto_error=False)
router = APIRouter()

@router.get("/get_documents")
async def get_documents(
    page: int = Query(0, ge=0, description="Page number (0-indexed)"),
    page_size: int = Query(7, ge=1, le=100, description="Number of documents per page"),
    credentials=Depends(security)
):
    """
    Fetch documents for the user's organization with pagination.
    
    Returns:
    - documents: List of documents with id, file_path, and created_at
    - total_count: Total number of documents
    - total_pages: Total number of pages
    - current_page: Current page number
    - has_more: Whether there are more pages
    """
    
    # Check if token is valid
    token = credentials.credentials if (credentials and credentials.credentials != "undefined") else None

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        print("user_id000000000000", user_id)
    except Exception as e:
        print(f"Token is invalid: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get org_id from database
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get org_id from org_userships
                cur.execute(
                    "SELECT org_id FROM org_userships WHERE user_id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")
                
                org_id = result[0]
                print("org_id000000000000", org_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching org_id: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching organization: {str(e)}")

    # Fetch documents with pagination
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute(
                    "SELECT COUNT(*) FROM documents WHERE org_id = %s",
                    (org_id,)
                )
                total_count = cur.fetchone()[0]
                
                # Calculate pagination info
                total_pages = max(1, (total_count + page_size - 1) // page_size)  # Ceiling division
                offset = page * page_size
                has_more = (offset + page_size) < total_count
                
                # Fetch documents for current page
                cur.execute(
                    """
                    SELECT id, file_path, created_at 
                    FROM documents 
                    WHERE org_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                    """,
                    (org_id, page_size, offset)
                )
                rows = cur.fetchall()
                
                # Format documents
                documents = [
                    {
                        "id": str(row[0]),
                        "file_path": row[1],
                        "created_at": row[2].isoformat() if row[2] else None
                    }
                    for row in rows
                ]
                
                return {
                    "documents": documents,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "current_page": page,
                    "has_more": has_more,
                    "page_size": page_size
                }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

