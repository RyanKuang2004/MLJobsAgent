import uuid
from db.mongodb_client import db

collection = db["chat_threads"]
    
def create_chat_config():
    thread_id = str(uuid.uuid4())
    return {"configurable": {"thread_id": thread_id}}

