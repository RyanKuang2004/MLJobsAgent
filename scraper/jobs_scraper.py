import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from .job_briefs_scraper import scrape_job_briefs
import time

# Load API key
load_dotenv()
api_key = os.getenv("JINA_API_KEY")
if not api_key:
    raise ValueError("JINA_API_KEY not found in .env file")

base_url = "https://r.jina.ai/https://www.seek.com.au/job/"
headers = {'Authorization': f'Bearer {api_key}'}

# Default rate limiting configuration
DEFAULT_RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds

class AdaptiveRateLimiter:
    def __init__(self, initial_rate_limit, window):
        self.rate_limit = initial_rate_limit
        self.window = window
        self.tokens = initial_rate_limit
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        self.retry_after = 0
    
    def update_rate_limit(self, response_headers):
        """Update rate limit based on API response headers"""
        # Common header names for rate limits
        remaining = response_headers.get('X-RateLimit-Remaining',
                      response_headers.get('RateLimit-Remaining',
                      response_headers.get('X-Rate-Limit-Remaining')))
        
        limit = response_headers.get('X-RateLimit-Limit',
                 response_headers.get('RateLimit-Limit',
                 response_headers.get('X-Rate-Limit-Limit')))
        
        reset = response_headers.get('X-RateLimit-Reset',
                response_headers.get('RateLimit-Reset',
                response_headers.get('X-Rate-Limit-Reset')))
        
        retry_after = response_headers.get('Retry-After')

        if limit:
            try:
                new_limit = int(limit)
                if new_limit != self.rate_limit:
                    print(f"Updating rate limit from {self.rate_limit} to {new_limit}")
                    self.rate_limit = new_limit
            except (ValueError, TypeError):
                pass

        if retry_after:
            try:
                self.retry_after = float(retry_after)
            except (ValueError, TypeError):
                pass

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            time_passed = now - self.last_update
            
            # Handle retry-after period
            if self.retry_after > 0:
                await asyncio.sleep(self.retry_after)
                self.retry_after = 0
                self.tokens = self.rate_limit
                self.last_update = now
                return
            
            # Replenish tokens based on time passed
            self.tokens = min(
                self.rate_limit,
                self.tokens + int((time_passed * self.rate_limit) / self.window)
            )
            
            if self.tokens <= 0:
                sleep_time = (self.window / self.rate_limit) - time_passed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                self.tokens = 1
            
            self.tokens -= 1
            self.last_update = now

class APIException(Exception):
    def __init__(self, message, should_retry=False, retry_after=None):
        super().__init__(message)
        self.should_retry = should_retry
        self.retry_after = retry_after

async def fetch_job_document(session, brief, rate_limiter, semaphore):
    """Fetch job details from Jina AI proxy API asynchronously with adaptive rate limiting."""
    url = f"{base_url}{brief.job_id}"
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        async with semaphore:
            await rate_limiter.acquire()
            print(f"Starting job: {brief.job_id} ({brief.role} at {brief.company_name})")
            
            try:
                async with session.get(url, headers=headers, timeout=10) as response:
                    # Update rate limiter based on response headers
                    rate_limiter.update_rate_limit(response.headers)
                    
                    if response.status == 429:  # Too Many Requests
                        retry_after = response.headers.get('Retry-After')
                        raise APIException(
                            "Rate limit exceeded",
                            should_retry=True,
                            retry_after=float(retry_after) if retry_after else 60
                        )
                    
                    response.raise_for_status()
                    content = await response.text()
                    print(f"Finished job: {brief.job_id} ({brief.role} at {brief.company_name})")
                    return Document(
                        page_content=content,
                        metadata={
                            "source": f"https://www.seek.com.au/job/{brief.job_id}",
                            "location": brief.location,
                            "role": brief.role,
                            "company_name": brief.company_name
                        }
                    )
                    
            except APIException as e:
                if e.should_retry and retry_count < max_retries:
                    retry_count += 1
                    if e.retry_after:
                        print(f"Rate limit exceeded. Waiting {e.retry_after} seconds...")
                        await asyncio.sleep(e.retry_after)
                    continue
                print(f"❌ Rate limit exceeded for {url} after {retry_count} retries")
                return None
                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                return None
        
        retry_count += 1
    
    return None

async def scrape_job_documents(job_briefs):
    """Scrape multiple job documents concurrently using Jina AI API with adaptive rate limiting."""
    print(f"Total jobs to process: {len(job_briefs)}")
    
    # Initialize rate limiter with default values
    rate_limiter = AdaptiveRateLimiter(DEFAULT_RATE_LIMIT, RATE_WINDOW)
    semaphore = asyncio.Semaphore(DEFAULT_RATE_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(
                fetch_job_document(session, brief, rate_limiter, semaphore)
            ) 
            for brief in job_briefs
        ]
        documents = await asyncio.gather(*tasks)

    successful_docs = [doc for doc in documents if doc is not None]
    print(f"✅ Processing complete. Retrieved {len(successful_docs)} successful documents.")
    return successful_docs

# Run the scraper
if __name__ == "__main__":
    print("🔎 Starting job scraping process...")
    
    # Scrape job briefs first
    job_briefs = scrape_job_briefs()
    
    # Run the async function
    documents = asyncio.run(scrape_job_documents(job_briefs))
    
    print("✅ Job scraping process completed.")

    # Print a preview of the first document's content
    if documents:
        print("\n📄 First document content preview:")
        print(documents[0].page_content[:500])