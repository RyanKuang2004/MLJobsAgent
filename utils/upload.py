import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
import tempfile
import os
from populate_database import split_documents, add_to_chroma

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