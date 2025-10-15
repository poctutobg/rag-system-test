import os
import time
from firecrawl import FirecrawlApp
from google import genai
from pinecone import Pinecone

# Configuration from environment variables
TARGET_URL = os.environ.get('TARGET_URL', 'https://docs.stripe.com/api')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
INDEX_NAME = os.environ.get('INDEX_NAME', 'stripe-api')
CRAWL_MODE = os.environ.get('CRAWL_MODE', 'crawl')  # 'single' or 'crawl'
MAX_PAGES = int(os.environ.get('MAX_PAGES', '5'))  # Max pages when crawling


def chunk_text(text, chunk_size=1000, overlap=50):
    """Split text into overlapping chunks"""
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def scrape_content(url, api_key, mode='single', max_pages=5):
    """Scrape website using Firecrawl - supports single page or crawl mode"""
    app = FirecrawlApp(api_key=api_key)
    results = []
    
    if mode == 'crawl':
        print(f"Crawling website: {url} (max {max_pages} pages)")
        
        crawl_result = app.crawl_url(
            url,
            params={
                'limit': max_pages,
                'scrapeOptions': {
                    'formats': ['markdown']
                }
            }
        )
        
        if crawl_result and 'data' in crawl_result:
            for page in crawl_result['data']:
                if 'markdown' in page and page['markdown']:
                    results.append({
                        'url': page.get('url', url),
                        'content': page['markdown']
                    })
                    print(f"Crawled: {page.get('url', 'unknown')}")
        
        print(f"Total pages crawled: {len(results)}")
    
    else:
        # Single page mode
        print(f"Scraping single page: {url}")
        result = app.scrape_url(url, params={'formats': ['markdown']})
        
        if result and 'markdown' in result:
            results.append({
                'url': url,
                'content': result['markdown']
            })
            print(f"Scraped {len(result['markdown'])} characters")
    
    return results if results else None


def ingest_data(request):
    """Main function - scrapes website and uploads to Pinecone"""
    
    # Check required API keys
    if not all([PINECONE_API_KEY, GEMINI_API_KEY, FIRECRAWL_API_KEY]):
        return "Error: Missing API keys", 500
    
    try:
        print(f"Starting ingestion for: {TARGET_URL} (mode: {CRAWL_MODE})")
        
        # Step 1: Scrape website with Firecrawl
        scraped_pages = scrape_content(TARGET_URL, FIRECRAWL_API_KEY, CRAWL_MODE, MAX_PAGES)
        
        if not scraped_pages:
            return "Error: Failed to scrape content", 500
        
        # Step 2: Process all pages and create chunks
        all_chunks = []
        for page in scraped_pages:
            chunks = chunk_text(page['content'])
            for chunk in chunks:
                all_chunks.append({
                    'text': chunk,
                    'source': page['url']
                })
        
        print(f"Created {len(all_chunks)} chunks from {len(scraped_pages)} pages")
        
        if not all_chunks:
            return "No content to process", 200
        
        # Step 3: Initialize Gemini and Pinecone
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(INDEX_NAME)
        
        # Step 4: Generate embeddings and upload to Pinecone
        uploaded = 0
        batch = []
        
        for i, chunk_data in enumerate(all_chunks):
            try:
                # Generate embedding
                response = gemini_client.models.embed_content(
                    model='models/text-embedding-004',
                    contents=chunk_data['text']
                )
                
                # Extract vector
                if hasattr(response, 'embedding'):
                    vector = list(response.embedding)
                elif hasattr(response, 'embeddings'):
                    vector = list(response.embeddings[0].values)
                else:
                    print(f"Skipping chunk {i}: couldn't extract embedding")
                    continue
                
                # Add to batch
                batch.append({
                    'id': f'chunk-{i}',
                    'values': vector,
                    'metadata': {
                        'text': chunk_data['text'][:500],
                        'source': chunk_data['source']
                    }
                })
                
                # Upload in batches of 50
                if len(batch) >= 50:
                    index.upsert(vectors=batch)
                    uploaded += len(batch)
                    print(f"Uploaded {uploaded} chunks")
                    batch = []
                    time.sleep(0.5)  # Small delay to avoid rate limits
                
            except Exception as e:
                print(f"Error on chunk {i}: {e}")
                continue
        
        # Upload remaining chunks
        if batch:
            index.upsert(vectors=batch)
            uploaded += len(batch)
        
        print(f"Complete! Uploaded {uploaded} chunks from {len(scraped_pages)} pages")
        return f"Success: Uploaded {uploaded} chunks from {len(scraped_pages)} pages to {INDEX_NAME}", 200
        
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {str(e)}", 500
