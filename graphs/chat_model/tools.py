from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from typing import Literal, Union, Optional
from db import pool
from Auth import supabase
import os
from openai import OpenAI
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated
from langchain_core.tools import InjectedToolCallId
from langgraph.graph import END
from langgraph.types import Command
import uuid
from uuid import UUID
from langgraph.prebuilt import InjectedState

@tool
def send_message_to_the_board(content: str, subject: str, sender_email: str, label: Literal["change_request", "violation_report", "general_message"], config: RunnableConfig,user_id: Annotated[Optional[Union[str, UUID]], InjectedState("user_id")]) -> str:
    """
    user this tool to send a message to the board
    
    Args:
        sender_email: the email of the sender
        label: the label of the message
        content: the content of the message
        subject: the subject of the message
    """
    org_id = config["configurable"]["org_id"]

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO mail (org_id, content, subject, sender_email, sender_id, label) VALUES (%s, %s, %s, %s, %s, %s)", (org_id, content, subject, sender_email, user_id, label))
    return "Message sent to the board"







@tool
def make_account(email: str, password: str, config: RunnableConfig, tool_call_id: Annotated[str, InjectedToolCallId]) -> Union[str, Command]:
    """
    Create a user account using Supabase best practices.

    Args:
        email: The email address for the new account
        password: The password for the new account
        config: Configuration containing org_key
    """
    org_key = config["configurable"]["org_key"]

    # First, get the organization ID from the database
    with pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                org_id = cur.execute("SELECT id FROM orgs WHERE org_key = %s", (org_key,)).fetchone()[0]
            except Exception as e:
                return "Organization not found"

    try:
        # Use Supabase Admin API to create the user
        user_data = {
            "email": email,
            "password": password,
            "user_metadata": {
                "org_id": org_id
            },
            "email_confirm": True  # Auto-confirm email for admin-created accounts
        }

        response = supabase.auth.admin.create_user(user_data)

        if response.user:
            user_id = response.user.id

            # Add user to org_userships table
            membership_data = {
                "user_id": user_id,
                "org_id": org_id
            }

            supabase.table("org_userships").insert(membership_data).execute()



            success_message = f"Account created successfully for email: {email} with password: {password}"
            # Return Command to update state and provide success message
            return Command(
                update={
                    "new_account_created_by_chat": True,
                    "messages": [ToolMessage(content=success_message,tool_call_id=tool_call_id)],
                    "email": email,
                    "password": password,
                    "user_id": user_id

                },
                goto="chat_node"
            )

            
              
              
        

        else:
            return "Failed to create account"

    except Exception as e:
        if "already_registered" in str(e).lower() or "user already exists" in str(e).lower():
            return "User account already exists"
        else:
            return f"Error creating account: {str(e)}"
    





@tool
def get_rules(query: str, config: RunnableConfig) -> str:
    """
    Search for relevant organizational rules and documents using RAG retrieval.
    If a user asks a rule question use this to check the rules

    Args:
        query: The search query to find relevant rules or documents
        config: Configuration containing org_id
    """
    org_id = config["configurable"]["org_id"]

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        # Generate embedding for the query
        embedding_response = openai_client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = embedding_response.data[0].embedding

        # Perform vector similarity search in pgvector
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Get top 5 closest matches using cosine distance (<=>)
                cur.execute("""
                    SELECT content, file_path, (embedding <=> %s::vector(1536)) as distance
                    FROM chunks
                    WHERE org_id = %s
                    ORDER BY embedding <=> %s::vector(1536)
                    LIMIT 5
                """, (query_embedding, org_id, query_embedding))

                results = cur.fetchall()

        if not results:
            return "No relevant rules or documents found for the given query."

        # Format the results
        # Format the results
        formatted_results = []
        for i, (content, file_path, distance) in enumerate(results, 1):
            similarity = 1 - distance
            # no slicing!
            formatted_results.append(
                f"Result {i} (Similarity: {similarity:.3f}):\n{content}\nSource: {file_path}"
            )
        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Error performing RAG retrieval: {str(e)}"




@tool 
def check_if_logged_in(user_id: Annotated[Optional[Union[str, UUID]], InjectedState("user_id")]) -> str: 
    """                                        
    Check if the user is logged in.
    """
    if user_id is None or user_id == "":
        return "User is not logged in"
    return "User is logged in"






tool_list = [send_message_to_the_board, make_account, get_rules,check_if_logged_in]