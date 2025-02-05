from typing import List, Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from prompts import ROUTER_INSTRUCTIONS
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

db = Chroma(
    persist_directory='./chroma',
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small")
)

llm = ChatOllama(model="deepseek-r1:7b")
llm_openai = ChatOpenAI(model="gpt-4o-mini")

class GraphState(TypedDict):
    documents: List[str]
    question: str
    answer: str
    
class RouterAnswer(BaseModel):
    search_type: Literal[str]
    

def route(state: GraphState): 
    router_llm = llm_openai.with_structured_output(RouterAnswer)
    
    result = llm.invoke(
        [SystemMessage(ROUTER_INSTRUCTIONS)]
        + [HumanMessage(state['question'])]
    ])
    source = result["search_type"]
    


workflow = StateGraph(GraphState)