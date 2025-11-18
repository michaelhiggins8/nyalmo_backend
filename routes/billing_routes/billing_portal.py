from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.security import HTTPBearer
import uuid
import os
from dotenv import load_dotenv
from autumn import Autumn
from db import pool
from Auth import supabase

load_dotenv()

router = APIRouter()

class BillingPortalRequest(BaseModel):
    customer_id: str

class BillingPortalResponse(BaseModel):
    portal_url: Optional[str] = None
    success: bool
    message: str

autumn = Autumn(os.getenv("AUTUMN_KEY"))

security = HTTPBearer(auto_error=False)

@router.post("/billing_portal", response_model=BillingPortalResponse)
async def create_billing_portal_url(
    body: BillingPortalRequest,
    credentials=Depends(security)
):
    """
    Create a billing portal URL using Autumn payment processor
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
        # Create billing portal URL
        response = await autumn.customers.get_billing_portal(body.customer_id, return_url=f"{os.getenv('FRONTEND_URL')}/billing")
        return BillingPortalResponse(
            portal_url=response.url,
            success=True,
            message="Billing portal URL created successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create billing portal URL: {str(e)}"
        )