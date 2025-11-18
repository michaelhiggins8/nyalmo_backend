from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
from Auth import supabase
import uuid
from uuid import UUID
from db import pool
from dotenv import load_dotenv
import os
import resend


load_dotenv()

router = APIRouter()

security = HTTPBearer(auto_error=False)

class MailRulingSchema(BaseModel):
    id: int
    created_at: datetime
    org_id: int
    content: str
    subject: str
    sender_email: str
    sender_id: str
    label: str
    read_at: Optional[datetime] = None
    status: str
    notes: str









def send_email(status: str, notes: str, email: str, subject: str):



    html_body = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {email},</p>

            <p>Your HOA request titled <strong>{subject}</strong> has been reviewed by the board.</p>

            <p>
                <strong>Status:</strong> 
                <span style="color:{'green' if status.lower() == 'approve' else 'red'}; font-weight:bold;">
                    {status.capitalize()}
                </span>
            </p>

            <p><strong>Board Notes:</strong><br>{notes}</p>

            <p>Best regards,<br>Nyalmo community Assistant</p>
            <p>*please don't respond to this email. If you would like to send a new request do so through your community chat bot</p>
        </div>
    """




    
    resend.api_key = os.getenv("RESEND_KEY")
    params: resend.Emails.SendParams = {
        "from": "Nyalmo <rulings@nyalmo.com>",
        "to": [email],
        "subject": "Request Ruling",
        "html": html_body,
    }

    email = resend.Emails.send(params)
    #print(email)
    
    




def process_mail_ruling(sender_id: UUID, status: str, content: str, subject: str, notes: str, org_id: int, mail_id: int, sender_email: str):
    """
    Process a mail ruling by inserting into the 'rulings' table and deleting the corresponding mail entry.
    
    Args:
        sender_id: UUID of the applicant
        status: Status of the ruling
        content: Content of the ruling
        subject: Subject of the ruling
        notes: Additional notes
        org_id: Organization ID
        mail_id: ID of the mail entry to delete
        sender_email: Email of the sender
    """



    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Insert new row into rulings table
                # id is auto-generated, created_at will use current timestamp
                cur.execute("""
                    INSERT INTO rulings (org_id, status, applicant_id, content, subject, notes, applicant_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (org_id, status, sender_id, content, subject, notes, sender_email))
                
                # Get the inserted row data
                result = cur.fetchone()
                ruling_id, created_at = result
                
                # Delete the corresponding mail entry
                cur.execute("""
                    DELETE FROM mail WHERE id = %s
                """, (mail_id,))
                
                deleted_rows = cur.rowcount
                
                return {
                    "id": ruling_id,
                    "created_at": created_at,
                    "status": status,
                    "applicant_id": str(sender_id),
                    "org_id": org_id,
                    "mail_deleted": deleted_rows > 0,
                    "sender_email": sender_email
                }
                
    except Exception as e:
        print(f"Error processing mail ruling: {e}")
        raise e



@router.post("/make_ruling")
async def make_ruling(body: MailRulingSchema, credentials=Depends(security)):
    """
    Simple dummy route that accepts mail ruling data and prints out JSON key values
    """
    
    # check if token is valid
    token = credentials.credentials if (credentials and credentials.credentials != "undefined") else None
    

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])  # Get user ID from token
    except Exception as e:
        print(f"Token is invalid: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    

    
    #check if user is org owner




    #send email to sender
    send_email(body.status, body.notes, body.sender_email,body.subject)
    
    #insert ruling into database
    ruling_result = process_mail_ruling(
        sender_id=body.sender_id,
        status=body.status,
        content=body.content,
        subject=body.subject,
        notes=body.notes,
        org_id=body.org_id,
        mail_id=body.id,
        sender_email=body.sender_email      
    )





    # Return a simple success response
    return {
        "message": f"Mail ruling received successfully - Status: {body.status}",
        "mail_id": body.id,
        "status": body.status,
        "notes": body.notes,
        "sender_email": body.sender_email
    }
