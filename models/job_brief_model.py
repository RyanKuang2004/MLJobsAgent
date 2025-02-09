from pydantic import BaseModel

class JobBriefModel(BaseModel):
    company_name: str
    job_id: str
    role: str
    location: str