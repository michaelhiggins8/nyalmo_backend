from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from autumn import Autumn
from Auth import supabase
import uuid
import os
from dotenv import load_dotenv

from autumn import Autumn




load_dotenv()

router = APIRouter()
autumn = Autumn(os.getenv("AUTUMN_KEY"))

class CheckCustomerFactRequest(BaseModel):
    customer_id: str

security = HTTPBearer(auto_error=False)

@router.post("/check_customer_facts")
async def check_customer_facts(request: CheckCustomerFactRequest, credentials=Depends(security)):
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
    #return {"allowed": True}   


    try:


        response = await autumn.customers.get(
            customer_id=request.customer_id,
        )









        # Return the allowed status from the autumn response
        return {"started_at": response.products[0].started_at,"households":response.features["houses"].included_usage}

    except Exception as e:
        return {"started_at": "error"}
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")