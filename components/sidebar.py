import streamlit as st
from utils.selection import configure_model
from utils.upload import upload_dialog
from utils.config import create_chat_config

def create_sidebar():
    # Create sidebar
    with st.sidebar:
        # Input field and add button in the same row
        if st.button(":material/new_window: New Chat", use_container_width=True):
            new_config = create_chat_config()
            st.session_state.config = new_config
            st.session_state.chat_title = "New Chat"
            # Immediately create empty messages for new chat
            st.session_state.messages = []
            
        if st.button(":material/draft: Upload Documents", use_container_width=True):
            upload_dialog()
            
        with st.popover(":material/settings: Settings", use_container_width=True):
            model_options = ["deepseek-r1:7b","gpt-4o-mini"]
            selected_model = configure_model(st.selectbox("Select a model",model_options,index=0))
            agent_options = ["general","document-writer"]
            selected_agent = st.selectbox("Select an agent",agent_options,index=0)
            selected_collection = st.selectbox("Select a collection", model_options, index=0)
        
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
                st.session_state.chat_title = chat_titles[selected_index]
        else:
            st.info("No chat history yet. Start a new chat!")
            chat_titles = ["New Chat"]
            selected_index = 0