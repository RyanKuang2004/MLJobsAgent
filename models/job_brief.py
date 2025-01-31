from pydantic import BaseModel

class JobBrief(BaseModel):
    company_name: str
    job_id: str
    role: str
    location: str