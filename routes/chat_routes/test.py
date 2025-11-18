from fastapi import APIRouter, Depends,Request

from pydantic import BaseModel
from fastapi.security import HTTPBearer
from db import pool
from typing import Optional
from langchain.chat_models import init_chat_model
import uuid
from Auth import supabase
from graphs.chat_model.chat_model import chat
import os
from dotenv import load_dotenv

load_dotenv()


router = APIRouter()



class ChatSchema(BaseModel):
    message:str
    thread_id:Optional[str] = None
    org_key:Optional[str] = None




security = HTTPBearer(auto_error=False)







import asyncio
from autumn import Autumn

autumn = Autumn(os.getenv("AUTUMN_KEY"))


async def track_message(org_id):
        response = await autumn.track(
        customer_id=str(org_id),
        feature_id='chats',
        value=1
                                       )















@router.post("/test")
def test(body: ChatSchema,credentials=Depends(security)):

    token = credentials.credentials if (credentials and credentials.credentials not in ["undefined", "null"]) else None
    with pool.connection() as conn:
        # user_id
        user_id = None 
        #guest
        if not token:

            result = conn.execute("SELECT org_key FROM orgs WHERE org_key = %s", (body.org_key,)).fetchone()
            
            
            if result is None:
                #guest with fake org key
                return {"message": "invalid org key"}

        #member
        else:
            try:
                #valid token
                claims = supabase.auth.get_claims(token)
                user_id = uuid.UUID(claims["claims"]["sub"])
                

            except Exception:
                # invalid token
                return {"message": "invalid token"}
        




        # thread_id and org_id
        thread_id = None
        org_id = None
        
        #guest
        if user_id is None:
            #org_id
            org_id = conn.execute("SELECT id FROM orgs WHERE org_key = %s", (body.org_key,)).fetchone()[0]
            
            #thread_id   
            #new chat          
            if body.thread_id is None:
                
                thread_id = uuid.uuid4()
                conn.execute("INSERT INTO threads (id, user_role,title) VALUES (%s, %s, %s)", (thread_id, 'GUEST',body.message[:15]))
                thread_id = str(thread_id)
                
            #in chat
            else:
                
                thread_id = body.thread_id
        
        #member
        else:

            #org_id
            org_id = conn.execute("SELECT org_id FROM org_userships WHERE user_id = %s", (user_id,)).fetchone()[0]
            
            #thread_id
            if body.thread_id is None:
                
                #new chat

                llm = init_chat_model("gpt-4o-mini", model_provider="openai")
                response = llm.invoke(f"Generate a short title for the chat starting with '{body.message}'").content
                thread_id = uuid.uuid4()
                conn.execute("INSERT INTO threads (id, user_id, user_role,title,preview) VALUES (%s, %s, %s, %s, %s)", (thread_id, user_id, 'MEMBER',response,body.message))
                thread_id = str(thread_id)
            else:
                
                #in chat
                thread_id = body.thread_id

    response, new_account_created_by_chat, email, password = chat(body.message,thread_id,org_id,user_id,body.org_key)

    try:
        asyncio.run(track_message(org_id))
    except Exception as e:
        print("Failed to track message: ", e)

    return{"message": response,"thread_id": thread_id,"new_account_created_by_chat": new_account_created_by_chat,"email": email,"password": password}



