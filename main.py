from db.mongodb_client import db
from scraper.job_briefs_scraper import scrape_job_briefs
import asyncio

async def main():
    job_briefs = await scrape_job_briefs()
    job_briefs = [job.model_dump() for job in job_briefs]
    
    # Store job briefs in MongoDB
    job_collection = db["job_briefs"]
    job_collection.insert_many(job_briefs)

if __name__ == "__main__":
    asyncio.run(main())