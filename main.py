import os
import time
from firecrawl import FirecrawlApp
from google import genai
from pinecone import Pinecone

# Configuration from environment variables
TARGET_URL = os.environ.get('TARGET_URL', 'https://docs.stripe.com/api/')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
INDEX_NAME = os.environ.get('INDEX_NAME', 'stripe-api')


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


def ingest_data(request):
    """Main function - scrapes website and uploads to Pinecone"""
    
    # Check required API keys
    if not all([PINECONE_API_KEY, GEMINI_API_KEY, FIRECRAWL_API_KEY]):
        return "Error: Missing API keys", 500
    
    try:
        print(f"Starting ingestion for: {TARGET_URL}")
        
        # Step 1: Scrape website with Firecrawl
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        result = app.scrape_url(TARGET_URL, params={'formats': ['markdown']})
        
        if not result or 'markdown' not in result:
            return "Error: Failed to scrape content", 500
        
        content = result['markdown']
        print(f"Scraped {len(content)} characters")
        
        # Step 2: Split into chunks
        chunks = chunk_text(content)
        print(f"Created {len(chunks)} chunks")
        
        if not chunks:
            return "No content to process", 200
        
        # Step 3: Initialize Gemini and Pinecone
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(INDEX_NAME)
        
        # Step 4: Generate embeddings and upload to Pinecone
        uploaded = 0
        batch = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                response = gemini_client.models.embed_content(
                    model='models/text-embedding-004',
                    contents=chunk
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
                        'text': chunk[:500],
                        'source': TARGET_URL
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
        
        print(f"Complete! Uploaded {uploaded} chunks")
        return f"Success: Uploaded {uploaded} chunks to {INDEX_NAME}", 200
        
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {str(e)}", 500
