from datetime import datetime
from pydantic import BaseModel, Field

class ChatThreadModel(BaseModel):
    thread_id: str
    chat_title: str
    created_at: datetime = Field(default_factory=datetime.now)
    