from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer
from db import pool
from Auth import supabase
import uuid

router = APIRouter()

class CheckBoardRequest(BaseModel):
    user_id: str  # UUID as string
    org_id: int   # int8 as int

security = HTTPBearer(auto_error=False)

@router.post("/check_if_board")
def check_if_board(request: CheckBoardRequest, credentials=Depends(security)):
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

    try:
        user_id = uuid.UUID(request.user_id)
        org_id = request.org_id

        with pool.connection() as conn:
            # Query the orgs table for owner_id where id matches org_id
            result = conn.execute(
                "SELECT owner_id FROM orgs WHERE id = %s",
                (org_id,)
            ).fetchone()

            if result is None:
                raise HTTPException(status_code=404, detail="Organization not found")

            owner_id = result[0]

            # Check if owner_id matches user_id
            is_board = owner_id == user_id

            return {"is_board": is_board}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format for user_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
