import re
from uuid import UUID
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage,SystemMessage, ToolMessage
from db import pool
from graphs.chat_model.tools import tool_list
from graphs.chat_model.system_prompt import SYSTEM_PROMPT
from typing import Optional

from langgraph.prebuilt import ToolNode

llm = init_chat_model("gpt-4o-mini", model_provider="openai")

llm = llm.bind_tools(tool_list)
class MyState(MessagesState):
    new_account_created_by_chat: bool = False
    email: str
    password: str
    user_id: Optional[str | UUID] = None
    


prompt = SYSTEM_PROMPT



def chat_node(state):
    messages = state["messages"]
    system_message = SystemMessage(content=prompt) 
    messages = [system_message] + messages
    
    response = llm.invoke(messages)

    return {"messages": [response]}
    

def tool_edge(state):
    if state["messages"][-1].tool_calls:
        return "tool_node"
    else:
        return END




builder = StateGraph(MyState)


builder.add_node("chat_node", chat_node)
builder.add_node("tool_node", ToolNode(tool_list))
builder.add_edge(START, "chat_node")
builder.add_conditional_edges("chat_node",tool_edge)
builder.add_edge("tool_node", "chat_node")





checkpointer = PostgresSaver(pool)
# checkpointer.setup()




chat_bot = builder.compile(checkpointer=checkpointer)

def chat(message,thread_id,org_id,user_id,org_key):
    thread = {"configurable": {"thread_id": thread_id,"user_id":user_id,"org_id":org_id,"org_key":org_key}}
    response = chat_bot.invoke({"messages": [HumanMessage(message)],"user_id":user_id}, thread)

    # Get the new_account_created_by_chat flag from the final state
    new_account_created_by_chat = response.get("new_account_created_by_chat", False)
    email = response.get("email", None)
    password = response.get("password", None)
    return response["messages"][-1].content, new_account_created_by_chat, email, password


