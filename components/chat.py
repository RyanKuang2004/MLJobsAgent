import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from simple_graph import graph
from db.mongodb_client import db
from models.chat_thread_model import ChatThreadModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class ChatTitleResponse(BaseModel):
    chat_title: str = Field(
        None, description="The title for the current conversation"
    )
    
collection = db["chat_threads"]

def get_response(query, config):
    # Execute the graph with streaming
    inputs = {
        "messages": query,
    }
    
    for message_chunk, metadata in graph.stream(
        inputs, config, stream_mode="messages"
    ):
        if message_chunk.content and metadata["langgraph_node"] == "generate_answer":
            yield message_chunk.content
            
def create_chat_title(messages):
    llm = ChatOpenAI(model="gpt-4o-mini")
    title_generator = llm.with_structured_output(ChatTitleResponse)
    prompt = f"""Given the following conversation transcript:
    
    {messages}
    
    Generate a concise and engaging title that accurately reflects the main topic or theme discussed.  
    If the conversation covers multiple topics, focus on the most prominent or overarching theme. 
    """
    result = title_generator.invoke(prompt)
    
    return result.chat_title
            
def save_thread(thread_id):
    chat_thread = ChatThreadModel(thread_id=thread_id, chat_title="New Chat")
    collection.insert_one(chat_thread.model_dump())
    
def update_chat_title(thread_id, title):
    collection.update_one({"thread_id": thread_id}, { "$set": { 'chat_title': title } })

def create_chat():
    # React to user input
    if prompt := st.chat_input("Ask me anything!"):
        thread_id = st.session_state.config["configurable"]["thread_id"]
        
        # Save thread if new
        if not collection.find_one({"thread_id": thread_id}):
            save_thread(thread_id)
            # Refresh chat history
            st.session_state.chat_history = list(collection.find())
        
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append(HumanMessage(content=prompt))

        # Display assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            for chunk in get_response(prompt, st.session_state.config):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

        chat_title = create_chat_title(st.session_state.messages)
        update_chat_title(thread_id, chat_title)
        
        # Save assistant response
        st.session_state.messages.append(AIMessage(content=full_response))
        st.rerun()  # Ensure UI updates with new messages