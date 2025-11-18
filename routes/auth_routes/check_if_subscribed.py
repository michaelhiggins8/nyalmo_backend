from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from autumn import Autumn
from Auth import supabase
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
autumn = Autumn(os.getenv("AUTUMN_KEY"))

class CheckSubscribedRequest(BaseModel):
    customer_id: str

security = HTTPBearer(auto_error=False)

@router.post("/check_if_subscribed")
async def check_if_subscribed(request: CheckSubscribedRequest, credentials=Depends(security)):
    '''
    # Validate token
    token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Validate token with Supabase
        claims = supabase.auth.get_claims(token)
        authenticated_user_id = uuid.UUID(claims["claims"]["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    ''' 
    return {"allowed": True}   
    if request.customer_id == "1":
        return {"allowed": True}
    else:
        return {"allowed": False}

    try:
        # Directly await the autumn check call
        response = await autumn.check(
            customer_id=request.customer_id,
            product_id='standard'  
        )

        # Return the allowed status from the autumn response
        return {"allowed": response.allowed}

    except Exception as e:
        return {"allowed": "error"}
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")