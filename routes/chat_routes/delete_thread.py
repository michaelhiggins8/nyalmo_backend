from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from Auth import supabase
from db import pool
import uuid

security = HTTPBearer()

router = APIRouter()

@router.delete("/delete_thread/{thread_id}")
def delete_thread(thread_id: str, credentials = Depends(security)):
    """
    Delete all data for a given LangGraph thread.
    
    Args:
        thread_id: The ID of the thread to delete
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing success message
    """
    try:
        # Verify authentication
        token = credentials.credentials
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        # Use the connection pool from db.py
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("BEGIN;")
                
                # Delete from all LangGraph tables
                cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s;", (thread_id,))
                cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s;", (thread_id,))
                cur.execute("DELETE FROM checkpoints WHERE thread_id = %s;", (thread_id,))
                
                # Delete from threads table
                cur.execute("DELETE FROM threads WHERE id = %s;", (thread_id,))
                cur.execute("COMMIT;")
        return {
            "message": f"✅ Deleted thread {thread_id} from LangGraph tables.",
            "thread_id": thread_id,
            "user_id": str(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting thread: {str(e)}")
