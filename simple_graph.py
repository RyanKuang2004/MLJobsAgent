from typing import List, Literal
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, MessagesState
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from prompts import ROUTER_INSTRUCTIONS, DOCUMENT_GRADER_INSTRUCTIONS, RESPONSE_INSTRUCTIONS
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from pydantic import BaseModel, Field
from langchain_community.tools.tavily_search import TavilySearchResults
import os
from dotenv import load_dotenv
from IPython.display import Image, display
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = os.getenv(var)

_set_env("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "langchain-academy"

_set_env("OPENAI_API_KEY")
_set_env("TAVILY_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "true"

db_path = "./state_db/example.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)


llm = ChatOllama(model="deepseek-r1:7b")
llm_openai = ChatOpenAI(model="gpt-4o-mini")

class GraphState(MessagesState):
    summary = str

def generate_answer(state: GraphState):
    summary = state.get("summary", "")
     
    if summary:
        system_message = f"Summary of the conversation earlier: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = state["messages"]
        
    response = llm.invoke(messages)
    return {"messages": response}

def summarize_conversation(state: GraphState):
    
    # First, we get any existing summary
    summary = state.get("summary", "")

    # Create our summarization prompt 
    if summary:
        
        # A summary already exists
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
        
    else:
        summary_message = "Create a summary of the conversation above:"

    # Add prompt to our history
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = llm.invoke(messages)
    
    # Delete all but the 2 most recent messages
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}

def should_summarise(state: GraphState):
    summary = state.get("summary", "")
    
    if len(summary) > 6:
        return "summarize_conversation"
    return END

workflow = StateGraph(GraphState)

workflow.add_node("generate_answer", generate_answer)
workflow.add_node("summarize_conversation", summarize_conversation)

workflow.set_entry_point("generate_answer")
workflow.add_conditional_edges("generate_answer", should_summarise)
workflow.add_edge("summarize_conversation", END)

# Add memory
graph = workflow.compile(checkpointer=memory)
