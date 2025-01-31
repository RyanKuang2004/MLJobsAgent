from db.mongodb_client import MongoDBClient
from scraper.job_briefs_scraper import scrape_job_briefs
import asyncio

async def main():
    job_briefs = await scrape_job_briefs()
    
    # Store job briefs in MongoDB
    mongo_client = MongoDBClient()
    mongo_client.insert_job_briefs(job_briefs)
    mongo_client.close()

if __name__ == "__main__":
    asyncio.run(main())