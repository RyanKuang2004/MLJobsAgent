import agentql
from playwright.async_api import async_playwright, Error as PlaywrightError
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import List
import os
import sys
from models.job_brief import JobBrief

# Load environment variables from .env file
load_dotenv()

def deduplicate_jobs(jobs: List[JobBrief]) -> List[JobBrief]:
    """
    Remove duplicate job entries based on company_name and role combination.
    Keeps the first occurrence of each unique combination.
    
    Args:
        jobs: List of JobBrief objects
        
    Returns:
        List of JobBrief objects with duplicates removed
    """
    seen = set()
    unique_jobs = []
    
    for job in jobs:
        # Create a tuple of company_name and role to use as a unique identifier
        key = (job.company_name, job.role)
        
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
            
    print(f"Removed {len(jobs) - len(unique_jobs)} duplicate job listings")       
            
    return unique_jobs

async def scrape_job_briefs():
    try:
        api_key = os.getenv("AGENTQL_API_KEY")
        if not api_key:
            raise ValueError("AGENTQL_API_KEY not found in .env file")

        base_url = "https://www.seek.com.au/machine-learning-jobs"
        NUM_PAGES = 15
        JOBS_QUERY = """{
            jobs[] {
                company_name
                job_id
                role
                location
            }
        }"""

        async with async_playwright() as playwright, \
                  await playwright.chromium.launch(headless=False) as browser:
            page = await agentql.wrap_async(browser.new_page())
            
            try:
                jobs = []
                error_count = 0
                
                for page_num in range(1, NUM_PAGES+1):
                    current_url = f"{base_url}?page={page_num}"
                    try:
                        await page.goto(current_url)
                        print(f"Successfully navigated to page {page_num}: {current_url}")
                    except PlaywrightError as e:
                        print(f"Browser error on page {page_num}: {e}", file=sys.stderr)
                        continue

                    try:
                        response = await page.query_data(JOBS_QUERY)
                        print(f"Successfully queried page {page_num}")
                    except Exception as e:
                        print(f"Query failed on page {page_num}: {e}", file=sys.stderr)
                        continue

                    if 'jobs' not in response:
                        print(f"No jobs found on page {page_num}", file=sys.stderr)
                        continue

                    # Process jobs from current page
                    for job_data in response['jobs']:
                        try:
                            job = JobBrief(**job_data)
                            jobs.append(job)
                        except ValidationError as e:
                            error_count += 1
                            print(f"Validation error on page {page_num}: {e}", file=sys.stderr)

                print(f"\nSuccessfully processed {len(jobs)} jobs from all pages")
                if error_count > 0:
                    print(f"Encountered {error_count} validation errors across all pages")
                    
                job_briefs = deduplicate_jobs(jobs)
                
                return job_briefs
                
            except Exception as e:
                print(f"Error during scraping: {e}", file=sys.stderr)
                raise
                
    except Exception as e:
        print(f"Unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        print("\nScraping process completed")
