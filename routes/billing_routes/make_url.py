from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from fastapi.security import HTTPBearer
import uuid
import os
from dotenv import load_dotenv
from autumn import Autumn
from db import pool
from Auth import supabase

load_dotenv()

router = APIRouter()



class CheckoutRequest(BaseModel):
    customer_id: str

class CheckoutResponse(BaseModel):
    checkout_url: Optional[str] = None
    success: bool
    message: str

autumn = Autumn(os.getenv("AUTUMN_KEY"))

security = HTTPBearer(auto_error=False)

@router.post("/make_url", response_model=CheckoutResponse)
async def create_checkout_url(
    body: CheckoutRequest,
    credentials=Depends(security)
):
    """
    Create a checkout URL using Autumn payment processor
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


        # get number of houses
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT households FROM orgs WHERE id = %s", (body.customer_id,))
                result = cur.fetchone()
                number_of_houses = result[0]    




        # Create checkout URL
        response = await autumn.checkout(
            customer_id=body.customer_id,
            product_id='standard',
            options=   [ { "feature_id": "houses", "quantity": number_of_houses }],
            success_url=f"{os.getenv('FRONTEND_URL')}/billing",
        )
        return CheckoutResponse(
            checkout_url=response.url,  
            success=True,
            message="Checkout URL created successfully"
        )
    except Exception as e:
        print("error: ", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout URL: {str(e)}"
        )