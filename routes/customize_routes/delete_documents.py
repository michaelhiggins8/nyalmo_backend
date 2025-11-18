from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List
import uuid
from Auth import supabase
from db import pool

security = HTTPBearer(auto_error=False)
router = APIRouter()

class DeleteDocumentsRequest(BaseModel):
    document_ids: List[str]

@router.post("/delete_documents")
async def delete_documents(request: DeleteDocumentsRequest, credentials=Depends(security)):
    """
    Delete documents from database and storage.
    Accepts a list of document IDs, verifies user access, and deletes both database records and storage files.
    """
    
    print(f"[DELETE_DOCUMENTS] Received request to delete {len(request.document_ids)} documents")
    print(f"[DELETE_DOCUMENTS] Document IDs received: {request.document_ids}")
    
    # Check if token is valid
    token = credentials.credentials if (credentials and credentials.credentials != "undefined") else None

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])
        print(f"[DELETE_DOCUMENTS] Authenticated user: {user_id}")
    except Exception as e:
        print(f"[DELETE_DOCUMENTS] Token is invalid: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate that we have document IDs
    if not request.document_ids or len(request.document_ids) == 0:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    # Get org_id from database
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT org_id FROM org_userships WHERE user_id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")
                
                user_org_id = result[0]
                print(f"[DELETE_DOCUMENTS] User org_id: {user_org_id}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE_DOCUMENTS] Error fetching org_id: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching organization: {str(e)}")

    # Get documents and verify ownership
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Convert string IDs to integers (documents table uses auto-incrementing int IDs)
                try:
                    print(f"[DELETE_DOCUMENTS] Converting {len(request.document_ids)} IDs to integers")
                    for i, doc_id in enumerate(request.document_ids):
                        print(f"[DELETE_DOCUMENTS] ID {i}: '{doc_id}' (type: {type(doc_id).__name__})")
                    document_ids = [int(doc_id) for doc_id in request.document_ids]
                    print(f"[DELETE_DOCUMENTS] Successfully converted to integers: {document_ids}")
                except ValueError as ve:
                    print(f"[DELETE_DOCUMENTS] Invalid ID format: {ve}")
                    raise HTTPException(status_code=400, detail=f"Invalid document ID format: {str(ve)}")
                
                # Fetch documents that belong to the user's org
                # Build placeholders for the IN clause
                placeholders = ','.join(['%s'] * len(document_ids))
                query = f"""
                    SELECT id, file_path, org_id 
                    FROM documents 
                    WHERE id IN ({placeholders}) AND org_id = %s
                """
                cur.execute(query, (*document_ids, user_org_id))
                documents = cur.fetchall()
                print(f"[DELETE_DOCUMENTS] Found {len(documents)} documents to delete")
                
                if not documents:
                    raise HTTPException(status_code=404, detail="No documents found or access denied")
                
                # Check if all requested documents were found
                found_ids = [str(doc[0]) for doc in documents]
                requested_ids_set = set(request.document_ids)
                found_ids_set = set(found_ids)
                
                if requested_ids_set != found_ids_set:
                    missing_ids = requested_ids_set - found_ids_set
                    print(f"Warning: Some documents not found or access denied: {missing_ids}")
                
                # Extract file paths for storage deletion
                file_paths = [doc[1] for doc in documents]
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE_DOCUMENTS] Error fetching documents: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

    # Delete from database (including chunks)
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # First, delete associated chunks by file_path
                for file_path in file_paths:
                    cur.execute(
                        "DELETE FROM chunks WHERE file_path = %s AND org_id = %s",
                        (file_path, user_org_id)
                    )
                
                # Then delete documents
                # Build placeholders for the IN clause
                placeholders = ','.join(['%s'] * len(document_ids))
                delete_query = f"DELETE FROM documents WHERE id IN ({placeholders}) AND org_id = %s"
                cur.execute(delete_query, (*document_ids, user_org_id))
                deleted_count = cur.rowcount
                conn.commit()
                print(f"[DELETE_DOCUMENTS] Deleted {deleted_count} documents from database")
                
                if deleted_count == 0:
                    raise HTTPException(status_code=404, detail="No documents were deleted")
                    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE_DOCUMENTS] Error deleting from database: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting from database: {str(e)}")

    # Delete from storage
    storage_errors = []
    deleted_files = []
    
    try:
        bucket_name = "documents"
        
        # Sanitize paths (strip leading '/')
        sanitized_paths = [path.lstrip('/') for path in file_paths]
        
        # Attempt deletion
        try:
            result = supabase.storage.from_(bucket_name).remove(sanitized_paths)
            
            # The remove method returns a list of deleted files
            # If successful, result should contain the list of deleted file objects
            if result:
                deleted_files = result
            else:
                storage_errors.append("No storage files were deleted (they may not exist)")
                
        except Exception as storage_error:
            error_msg = str(storage_error)
            print(f"Storage deletion error: {error_msg}")
            storage_errors.append(f"Storage deletion failed: {error_msg}")
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error during storage deletion: {error_msg}")
        storage_errors.append(f"Error during storage deletion: {error_msg}")

    # Prepare response
    response = {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} document(s)",
        "deleted_files_count": len(deleted_files) if deleted_files else 0
    }
    
    # Include storage errors if any (but still consider it success if DB deletion worked)
    if storage_errors:
        response["storage_warnings"] = storage_errors
        response["message"] += f" (with {len(storage_errors)} storage warning(s))"
    
    return response

