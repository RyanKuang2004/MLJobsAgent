import streamlit as st
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from simple_graph import graph
import uuid
from models.chat_thread_model import ChatThreadModel
from db.mongodb_client import db
from langchain_community.document_loaders import PyPDFLoader
import tempfile
import os
from populate_database import split_documents, add_to_chroma

def create_page():
    return

    
@st.dialog("Upload documents")
def upload_dialog():
    with st.form("upload-form", clear_on_submit=True):
        uploaded_files = st.file_uploader("Choose a document to upload", accept_multiple_files=True)
        
        if st.form_submit_button("Upload", use_container_width=True):
            upload_files(uploaded_files)

def upload_files(files):
    if files is None or len(files) == 0:
        st.warning("Please select at least one file to upload.")
        return 
    
    valid_files = []
    for file in files:
        if file.type == "application/pdf":
            valid_files.append(file)
        else:
            st.warning(f"Skipping non-PDF file: {file.name}")
            
    if len(valid_files) == 0:
        st.warning("No valid PDF files were uploaded.")
        return

    with st.spinner("Uploading documents to Chroma. Please wait...", show_time=True):
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        for uploaded_file in valid_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(file_path)
    
        documents = []
        for file_path in file_paths:
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
        
        chunks = split_documents(documents)
        num_uploaded_docs = add_to_chroma(chunks)

        # Clean up: Remove the temporary files
        for file_path in file_paths:
            os.remove(file_path)
        os.rmdir(temp_dir)
    
    st.success(f'Successfully uploaded {num_uploaded_docs} to Chroma', icon="✅")

def save_thread(thread_id):
    chat_thread = ChatThreadModel(thread_id=thread_id, chat_title="New chat")
    collection.insert_one(chat_thread.model_dump())

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
            
def configure_model(model_name):
    model_mapper = {
        "gpt-4o-mini": ChatOpenAI(model=model_name),
        "deepseek-r1:7b": ChatOllama(model=model_name)
    }
    return model_mapper[model_name]

def create_chat_config():
    thread_id = str(uuid.uuid4())
    return {"configurable": {"thread_id": thread_id}}

# Initialize MongoDB collection
collection = db["chat_threads"]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = list(collection.find())

# Initialize config if not present
if "config" not in st.session_state:
    st.session_state.config = create_chat_config()

st.set_page_config(page_title="Local Rag", page_icon="📝")

# Create sidebar
with st.sidebar:
    # Input field and add button in the same row
    if st.button("New chat", use_container_width=True):
        new_config = create_chat_config()
        st.session_state.config = new_config
        # Immediately create empty messages for new chat
        st.session_state.messages = []
    
    model_options = [
        "deepseek-r1:7b",
        "gpt-4o-mini",
    ]
    selected_model = st.selectbox(
        "LLM Model",
        model_options,
        index=0
    )
    
    if st.button("Upload documents", use_container_width=True):
        upload_dialog()

    st.subheader("Chat History")
     
    # Handle empty chat history
    reversed_chat_history = st.session_state.chat_history[::-1]
    if reversed_chat_history:
        chat_titles = [thread["chat_title"] for thread in reversed_chat_history]
        
        selected_index = st.selectbox(
            "Select a chat", 
            range(len(chat_titles)), 
            format_func=lambda i: chat_titles[i],
            key="chat_selector"
        )

        current_chat = reversed_chat_history[selected_index]
        
        # Update config when chat selection changes
        new_thread_id = current_chat["thread_id"]
        if st.session_state.get("current_thread_id") != new_thread_id:
            st.session_state.current_thread_id = new_thread_id
            st.session_state.config = {"configurable": {"thread_id": new_thread_id}}
    else:
        st.info("No chat history yet. Start a new chat!")
        chat_titles = ["New Chat"]
        selected_index = 0

# Track thread ID changes and reload messages
current_thread_id = st.session_state.config["configurable"]["thread_id"]
if "prev_thread_id" not in st.session_state:
    st.session_state.prev_thread_id = current_thread_id

if st.session_state.prev_thread_id != current_thread_id:
    # Thread ID changed, reload messages
    st.session_state.prev_thread_id = current_thread_id
    messages = graph.get_state(st.session_state.config).values.get("messages", [])
    st.session_state.messages = messages

# Initialize messages if empty
if "messages" not in st.session_state:
    messages = graph.get_state(st.session_state.config).values.get("messages", [])
    st.session_state.messages = messages

# Display header based on chat history
st.header(chat_titles[selected_index])

# Display chat messages
for message in st.session_state.messages:
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content, unsafe_allow_html=True)

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

    # Save assistant response
    st.session_state.messages.append(AIMessage(content=full_response))
    st.rerun()  # Ensure UI updates with new messages