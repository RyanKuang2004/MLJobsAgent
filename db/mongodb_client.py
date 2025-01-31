from pymongo import MongoClient
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from models.job_brief import JobBrief

# Load environment variables from .env file
load_dotenv()

class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("MONGODB_DATABASE")]
        self.collection = self.db[os.getenv("MONGODB_COLLECTION")]

    def insert_job_briefs(self, job_briefs: List[BaseModel]):
        """
        Insert a list of JobBrief objects into the MongoDB collection.
        
        Args:
            job_briefs: List of JobBrief objects
        """
        job_dicts = [job.model_dump() for job in job_briefs]
        result = self.collection.insert_many(job_dicts)
        print(f"Inserted {len(result.inserted_ids)} job briefs into MongoDB")
        
    def get_all_job_briefs(self) -> List[JobBrief]:
        """
        Retrieve all job briefs from the MongoDB collection.
        
        Returns:
            List of JobBrief objects
        """
        job_dicts = self.collection.find({})
        job_briefs = [JobBrief(**job) for job in job_dicts]
        return job_briefs

    def close(self):
        """
        Close the MongoDB connection.
        """
        self.client.close()