# RAG System - Data Ingestion Cloud Function

## Overview
This Google Cloud Function implements the data ingestion pipeline for a RAG (Retrieval-Augmented Generation) system. It scrapes website content, processes it into chunks, generates embeddings using Google Gemini AI, and stores them in a Pinecone vector database.

## Architecture
```
Website → Firecrawl (Scraping) → Text Chunking → Gemini Embeddings → Pinecone Vector DB
```

## Features
- **Smart Web Scraping**: Uses Firecrawl API for reliable content extraction
- **Crawl Modes**: 
  - `single`: Scrape one page
  - `crawl`: Scrape multiple pages and subdomains
- **Intelligent Chunking**: Overlapping text chunks for better context preservation
- **Vector Embeddings**: Google Gemini `text-embedding-004` model (768 dimensions)
- **Batch Processing**: Efficient uploads to Pinecone with configurable batch size
- **Unique ID Generation**: URL-based hashing prevents data overwriting from multiple sources

## Files
- `main.py` - Cloud Function entry point and core logic
- `requirements.txt` - Python dependencies

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TARGET_URL` | Website URL to scrape | No | `https://stripe.com/docs/billing` |
| `PINECONE_API_KEY` | Pinecone API key | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `FIRECRAWL_API_KEY` | Firecrawl API key | Yes | - |
| `INDEX_NAME` | Pinecone index name | No | `test-poc` |
| `CRAWL_MODE` | `single` or `crawl` | No | `single` |
| `MAX_PAGES` | Max pages to crawl | No | `10` |

## Configuration

### Chunking Parameters
- **Chunk Size**: 1000 characters
- **Overlap**: 50 characters
- **Batch Size**: 100 vectors per upload

### Vector Database
- **Dimensions**: 768
- **Metric**: Cosine similarity
- **Cloud**: AWS
- **Region**: us-east-1

## Deployment

### 1. Prerequisites
- Google Cloud Project with Cloud Functions enabled
- API keys for Pinecone, Gemini, and Firecrawl

### 2. Deploy to Google Cloud
```bash
gcloud functions deploy ingest_data \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point ingest_data \
  --set-env-vars PINECONE_API_KEY=your_key,GEMINI_API_KEY=your_key,FIRECRAWL_API_KEY=your_key
```

### 3. Function Entry Point
- **Function Name**: `ingest_data`
- **Trigger**: HTTP
- **Runtime**: Python 3.11

## Usage

### Scrape Single Page
```bash
curl -X POST https://YOUR_FUNCTION_URL \
  -H "Content-Type: application/json"
```

### Scrape Multiple Pages
Set environment variables:
```
CRAWL_MODE=crawl
MAX_PAGES=50
TARGET_URL=https://stripe.com/docs
```

## Response Format

**Success:**
```
Success! Uploaded 177 of 177 chunks from 1 pages to index 'test-poc'
Status: 200
```

**Error:**
```
Missing Environment Variables: PINECONE_API_KEY, GEMINI_API_KEY
Status: 500
```

## How It Works

1. **Web Scraping**: Firecrawl extracts clean markdown content from the target URL
2. **Text Processing**: Content is split into overlapping chunks (1000 chars, 50 overlap)
3. **Embedding Generation**: Each chunk is converted to a 768-dimensional vector using Gemini
4. **Vector Storage**: Embeddings are uploaded to Pinecone with metadata (text, source, index)
5. **Unique IDs**: URL hash ensures multiple sources can coexist without conflicts

## Error Handling
- Validates all required environment variables
- Handles API errors gracefully
- Skips problematic chunks without stopping the entire process
- Provides detailed logging for debugging

## Performance
- **Batch uploads**: 100 vectors per request
- **Concurrent processing**: Single-threaded for reliability
- **Average time**: ~2-5 seconds per chunk (including embedding generation)

## Integration with RAG Pipeline
This function is designed to work with an n8n/Make.com workflow:
1. **Ingestion** (This function): Populate vector database
2. **Query** (n8n/Make): Retrieve relevant context
3. **Generation** (LLM): Generate answers based on retrieved context

## Metadata Structure
Each vector includes:
```python
{
  'id': 'a3f4b21c-chunk-0',
  'values': [0.123, -0.456, ...],  # 768 dimensions
  'metadata': {
    'text': 'Chunk content...',
    'source': 'https://example.com/page',
    'chunk_index': 0
  }
}
```

## Troubleshooting

### Dimension Mismatch
Ensure Pinecone index dimension (768) matches the embedding model output.

### All Chunks Skipped
Check Gemini API response structure - update `generate_embedding()` function if needed.

### Firecrawl Errors
Verify API key and URL format (must start with `http://` or `https://`).

## Dependencies
- `firecrawl-py==1.5.0` - Web scraping
- `google-genai==0.2.2` - Embedding generation
- `pinecone==5.0.0` - Vector database

## License
This code is part of an AI Developer assignment for Hop Online.

## Author
Author: Rostislav Atanasov
Created as part of the RAG System Proof-of-Concept assignment.
