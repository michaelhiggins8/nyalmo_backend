from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from Auth import supabase
from db import pool
import uuid

security = HTTPBearer()

router = APIRouter()

@router.get("/fetch_threads")
def fetch_threads(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
    credentials = Depends(security)
):
    """
    Fetch threads for the authenticated user with pagination.
    
    Args:
        page: Page number (0-indexed)
        page_size: Number of threads per page
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing threads array and pagination info
    """
    try:
        # Verify authentication
        token = credentials.credentials
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        
        # Calculate offset for pagination
        offset = page * page_size
        
        # Use the connection pool from db.py
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Fetch threads for the user with pagination
                cur.execute(
                    """
                    SELECT id, title, created_at, preview, user_id
                    FROM threads
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (str(user_id), page_size, offset)
                )
                
                rows = cur.fetchall()
                
                # Format the results to match the frontend expectations
                threads = []
                for row in rows:
                    threads.append({
                        "id": row[0],
                        "title": row[1],
                        "created_at": row[2].isoformat() if row[2] else None,
                        "preview": row[3],
                        "user_id": row[4]
                    })
                
                # Check if there are more threads
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM threads 
                    WHERE user_id = %s
                    """,
                    (str(user_id),)
                )
                total_count = cur.fetchone()[0]
                
        return {
            "threads": threads,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "has_more": (offset + len(threads)) < total_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching threads: {str(e)}")

