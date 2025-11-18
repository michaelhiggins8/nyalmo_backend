from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from graphs.chat_model.chat_model import chat_bot
import uuid
from Auth import supabase

security = HTTPBearer()

router = APIRouter()

@router.get("/collect_thread/{thread_id}")
def collect_thread(thread_id: str, credentials = Depends(security)):
    """
    Collect conversation messages from a specific thread.
    
    Args:
        thread_id: The ID of the thread to collect messages from
        credentials: JWT token for authentication
        
    Returns:
        Dictionary containing the conversation messages
    """
    
    try:
        
        # Verify authentication
        token = credentials.credentials
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        
        # Get the conversation state from the chat bot
        snapshot = chat_bot.get_state({"configurable": {"thread_id": thread_id}})
        conversation = snapshot.values["messages"]
        
        return {
            "thread_id": thread_id,
            "messages": conversation,
            "user_id": str(user_id)
        }
        
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Error collecting thread: {str(e)}")
