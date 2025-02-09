import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from simple_graph import graph
from db.mongodb_client import db
from utils.config import create_chat_config
from components.chat import create_chat
from components.sidebar import create_sidebar

# Initialize MongoDB collection
collection = db["chat_threads"]
st.set_page_config(page_title="Local RAG")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = list(collection.find())

# Initialize config if not present
if "config" not in st.session_state:
    st.session_state.config = create_chat_config()
    
create_sidebar()

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
st.header(st.session_state.chat_title if "chat_title" in st.session_state else "New Chat")

# Display chat messages
for message in st.session_state.messages:
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content, unsafe_allow_html=True)

create_chat()