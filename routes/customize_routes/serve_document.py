from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import HTTPBearer
from fastapi.responses import StreamingResponse
import uuid
import io
from Auth import supabase
from db import pool

security = HTTPBearer(auto_error=False)
router = APIRouter()

@router.api_route("/serve_document/{file_path:path}", methods=["GET", "HEAD"])
async def serve_document(request: Request, file_path: str, token: str = None, credentials=Depends(security)):
    """
    Serve a document from Supabase storage.
    """
    
    # Check if token is valid
    auth_token = credentials.credentials if (credentials and credentials.credentials != "undefined") else token
    
    if not auth_token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(auth_token)
        user_id = uuid.UUID(claims["claims"]["sub"])
    except Exception as e:
        print(f"Token is invalid: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Verify user has access to this document by checking org_id
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get user's org_id
                cur.execute(
                    "SELECT org_id FROM org_userships WHERE user_id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")
                
                user_org_id = result[0]
                
                # Check if the file path belongs to this org
                # File path format: /{org_id}/{uuid}_{filename}
                if not file_path.startswith(f"/{user_org_id}/"):
                    raise HTTPException(status_code=403, detail="Access denied to this document")
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying access: {e}")
        raise HTTPException(status_code=500, detail=f"Error verifying access: {str(e)}")

    # Download file from Supabase storage
    try:
        bucket_name = "documents"
        file_data = supabase.storage.from_(bucket_name).download(file_path)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Determine content type based on file extension
        file_extension = file_path.split('.')[-1].lower()
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'csv': 'text/csv'
        }
        
        content_type = content_type_map.get(file_extension, 'application/octet-stream')
        
        # Extract filename for download
        filename = file_path.split('/')[-1]
        # Remove UUID prefix if present
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) == 2 and len(parts[0]) == 36:  # UUID is 36 characters
                filename = parts[1]
        
        headers = {
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "public, max-age=3600",
            "Content-Length": str(len(file_data))
        }
        
        # For HEAD requests, return just headers without body
        if request.method == "HEAD":
            return Response(status_code=200, headers=headers)
        
        # For GET requests, return the full file
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers=headers
        )
        
    except Exception as e:
        print(f"Error serving document: {e}")
        raise HTTPException(status_code=500, detail=f"Error serving document: {str(e)}")
