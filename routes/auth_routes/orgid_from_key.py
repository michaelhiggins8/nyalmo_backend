from fastapi import APIRouter
from pydantic import BaseModel
from db import pool


class OrgIdFromKeyRequest(BaseModel):
    key: str



router = APIRouter()


@router.post("/orgid_from_key")
def orgid_from_key(request: OrgIdFromKeyRequest):

    with pool.connection() as conn:
        result = conn.execute("SELECT id FROM orgs WHERE org_key = %s", (request.key,)).fetchone()
        if result is None:
            return {"success": False, "message": "Organization not found"}
        org_id = result[0]  # type: ignore  
        return {"success": True, "org_id": org_id}




