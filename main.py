import os
import re
import time
from firecrawl import FirecrawlApp

from google import genai
from google.genai.errors import APIError
from pinecone import Pinecone, ServerlessSpec

# --- Configuration ---
TARGET_URL = os.environ.get('TARGET_URL', 'https://docs.stripe.com/api/')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
INDEX_NAME = os.environ.get('INDEX_NAME', 'stripe-api')
CRAWL_MODE = os.environ.get('CRAWL_MODE', 'single')  # 'single' or 'crawl'
MAX_PAGES = int(os.environ.get('MAX_PAGES', '10'))  # Maximum pages to crawl

# Constants
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 50
BATCH_SIZE = 100
EMBEDDING_DIMENSION = 768  # Match Pinecone index dimension


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Splits text into overlapping chunks.
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        
        if chunk:
            chunks.append(chunk)
        
        start += chunk_size - overlap
    
    return chunks


def scrape_with_firecrawl(url, api_key, mode='single', max_pages=10):
    """
    Scrapes website using Firecrawl.
    
    Args:
        url: Target URL
        api_key: Firecrawl API key
        mode: 'single' for one page, 'crawl' for multiple pages
        max_pages: Maximum number of pages to crawl
        
    Returns:
        List of dictionaries with 'url' and 'content' keys
    """
    try:
        app = FirecrawlApp(api_key=api_key)
        results = []
        
        if mode == 'crawl':
            print(f"Crawling website starting from: {url} (max {max_pages} pages)")
            
            # Crawl multiple pages
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
                        print(f"Crawled: {page.get('url', 'unknown')} ({len(page['markdown'])} chars)")
            
            print(f"Total pages crawled: {len(results)}")
            
        else:
            # Single page scrape
            print(f"Scraping single page: {url}")
            scrape_result = app.scrape_url(url, params={'formats': ['markdown']})
            
            if scrape_result and 'markdown' in scrape_result:
                results.append({
                    'url': url,
                    'content': scrape_result['markdown']
                })
                print(f"Scraped {len(scrape_result['markdown'])} characters")
        
        if not results:
            print("No content returned from Firecrawl")
            return None
            
        return results
            
    except Exception as e:
        print(f"Firecrawl error: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def generate_embedding(client, text):
    """
    Generates embedding vector for given text using Gemini API.
    Returns 512-dimensional vector to match Pinecone index.
    """
    try:
        # Try with output_dimensionality parameter first
        try:
            response = client.models.embed_content(
                model='models/text-embedding-004',
                contents=text,
                output_dimensionality=768
            )
        except TypeError:
            # If output_dimensionality is not supported, try without it
            # text-embedding-004 default is 768 anyway
            print("output_dimensionality parameter not supported, using default (768)")
            response = client.models.embed_content(
                model='models/text-embedding-004',
                contents=text
            )
        
        # Try multiple ways to access the embedding
        vector = None
        
        # Method 1: Direct embedding attribute
        if hasattr(response, 'embedding'):
            vector = response.embedding
            print("Using response.embedding")
        # Method 2: Check for embeddings list
        elif hasattr(response, 'embeddings'):
            if len(response.embeddings) > 0:
                emb = response.embeddings[0]
                # Check if it has values attribute
                if hasattr(emb, 'values'):
                    vector = list(emb.values)
                    print("Using response.embeddings[0].values")
                else:
                    vector = emb
                    print("Using response.embeddings[0]")
        # Method 3: Dictionary access
        elif isinstance(response, dict):
            if 'embedding' in response:
                vector = response['embedding']
                print("Using response['embedding']")
            elif 'embeddings' in response and len(response['embeddings']) > 0:
                vector = response['embeddings'][0]
                print("Using response['embeddings'][0]")
        
        if vector is None:
            print(f"Could not extract vector.")
            print(f"Response type: {type(response)}")
            print(f"Response dir: {[x for x in dir(response) if not x.startswith('_')]}")
            # Print first 200 chars of response
            response_str = str(response)[:200]
            print(f"Response preview: {response_str}")
            return None
        
        # Convert to list if needed
        if not isinstance(vector, list):
            vector = list(vector)
        
        actual_dim = len(vector)
        print(f"Generated vector with {actual_dim} dimensions")
        
        # Handle dimension mismatch
        if actual_dim == 768 and EMBEDDING_DIMENSION == 768:
            # Perfect match, no adjustment needed
            print("Dimension matches: 768")
        elif actual_dim == 512 and EMBEDDING_DIMENSION == 768:
            print(f"Warning: Got 512d but need 768d - cannot proceed")
            return None
        elif actual_dim != EMBEDDING_DIMENSION:
            print(f"Warning: Dimension mismatch - expected {EMBEDDING_DIMENSION}, got {actual_dim}")
            return None
        
        return vector
        
    except Exception as e:
        print(f"Error generating embedding: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def ingest_data(request):
    """
    Google Cloud Function for Data Ingestion.
    Scrapes website using Firecrawl, vectorizes content and uploads to Pinecone.
    """
    # Validation
    required_keys = {
        'PINECONE_API_KEY': PINECONE_API_KEY,
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'FIRECRAWL_API_KEY': FIRECRAWL_API_KEY
    }
    
    missing = [key for key, value in required_keys.items() if not value]
    
    if missing:
        error_msg = f"Missing Environment Variables: {', '.join(missing)}"
        print(error_msg)
        return error_msg, 500

    # Validate URL format
    if not TARGET_URL.startswith(('http://', 'https://')):
        error_msg = f"Invalid URL format: {TARGET_URL}. URL must start with http:// or https://"
        print(error_msg)
        return error_msg, 400

    try:
        # 1. Scrape with Firecrawl
        print(f"Scraping with Firecrawl: {TARGET_URL} (mode: {CRAWL_MODE})")
        scraped_pages = scrape_with_firecrawl(TARGET_URL, FIRECRAWL_API_KEY, CRAWL_MODE, MAX_PAGES)
        
        if not scraped_pages:
            return "Failed to scrape content with Firecrawl", 500
        
        # 2. Process all pages and create chunks
        all_chunks = []
        
        for page_data in scraped_pages:
            page_url = page_data['url']
            page_content = page_data['content']
            
            # Chunk the content
            chunks = chunk_text(page_content)
            
            # Add source URL to each chunk
            for chunk in chunks:
                all_chunks.append({
                    'text': chunk,
                    'source': page_url
                })
        
        print(f"Created {len(all_chunks)} total chunks from {len(scraped_pages)} pages")
        
        if not all_chunks:
            return "No text found for processing", 200

        # 3. Initialize clients
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # 4. Check index
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        
        if INDEX_NAME not in existing_indexes:
            print(f"Creating index: {INDEX_NAME}")
            pc.create_index(
                name=INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            time.sleep(10)
        
        index = pc.Index(INDEX_NAME)
        
        # 5. Vectorization and upload
        print("Starting vectorization...")
        vectors_batch = []
        uploaded_count = 0
        
        # Generate unique ID prefix based on URL
        import hashlib
        url_hash = hashlib.md5(TARGET_URL.encode()).hexdigest()[:8]

        for i, chunk_data in enumerate(all_chunks):
            text_content = chunk_data['text']
            chunk_source = chunk_data['source']
            
            # Generate embedding
            vector = generate_embedding(gemini_client, text_content)
            
            if vector is None:
                print(f"Skipping chunk {i}")
                continue
            
            # Create unique ID with URL hash to avoid overwriting
            unique_id = f"{url_hash}-chunk-{i}"
            
            # Prepare vector
            vectors_batch.append({
                'id': unique_id,
                'values': vector,
                'metadata': {
                    'text': text_content[:1000],
                    'source': chunk_source,
                    'chunk_index': i
                }
            })
            
            # Batch upload
            if len(vectors_batch) >= BATCH_SIZE:
                index.upsert(vectors=vectors_batch)
                uploaded_count += len(vectors_batch)
                print(f"Uploaded {uploaded_count} chunks")
                vectors_batch = []

        # Upload remaining batch
        if vectors_batch:
            index.upsert(vectors=vectors_batch)
            uploaded_count += len(vectors_batch)

        # Final result
        success_msg = f"Success! Uploaded {uploaded_count} of {len(all_chunks)} chunks from {len(scraped_pages)} pages to index '{INDEX_NAME}'"
        print(success_msg)
        
        return success_msg, 200

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        import traceback
        print(traceback.format_exc())

        return error_msg, 500
