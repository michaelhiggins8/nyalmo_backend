from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from fastapi.security import HTTPBearer
import uuid
import os
from dotenv import load_dotenv
from autumn import Autumn
from Auth import supabase

load_dotenv()

router = APIRouter()

class CheckPlanRequest(BaseModel):
    org_id: str

class CheckPlanResponse(BaseModel):
    subscribed: bool
    success: bool
    message: str

autumn = Autumn(os.getenv("AUTUMN_KEY"))

security = HTTPBearer(auto_error=False)

@router.post("/check_plan", response_model=CheckPlanResponse)
async def check_subscription_plan(
    body: CheckPlanRequest,
    credentials=Depends(security)
):
    """
    Check if a customer is subscribed to the standard plan
    """
    try:
        # Validate authentication token if provided
        token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None

        user_id = None
        if token:
            try:
                claims = supabase.auth.get_claims(token)
                user_id = uuid.UUID(claims["claims"]["sub"])
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")

        # Check subscription status
        response = await autumn.check(
            customer_id=body.org_id,
            product_id='standard'
        )
        # Determine if subscribed based on the response
        # The autumn.check response typically returns subscription details
        #subscribed = response.get('allowed', False) if isinstance(response, dict) else bool(response)
        subscribed = response.allowed
        return CheckPlanResponse(
            subscribed=subscribed,
            success=True,
            message="Subscription status checked successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check subscription status: {str(e)}"
        )