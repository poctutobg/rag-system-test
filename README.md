## 💻 Code Overview: Data Ingestion Module (`main.py`)

This document details the Google Cloud Function responsible for the **Data Ingestion** pipeline of the RAG (Retrieval-Augmented Generation) system. It ensures content is reliably scraped, vectorized, and stored in a queryable format.

### Architecture

The pipeline is **event-driven** and **serverless**:

`HTTP Trigger` → `Firecrawl (Scraping)` → `Text Chunking` → `Gemini Embeddings` → `Pinecone Vector DB`

-----

## ✨ Technical Highlights and Features

| Functionality | Purpose | Technical Implementation |
| :--- | :--- | :--- |
| **Intelligent Chunking** | Splits large text into RAG-ready segments. | Uses the custom **`chunk_text`** function with a **1000-character chunk size** and **50-character overlap** to preserve context. |
| **Vector Embeddings** | Creates 768-dimensional vector representations. | Employs the **Gemini API** (`google.genai`) with the **`models/text-embedding-004`** model, guaranteeing dimensional consistency with the Pinecone index. |
| **Batch Processing** | Ensures efficient, reliable uploads to the vector database. | **Critically implements batch processing (`BATCH_SIZE = 100`)** during `pinecone.upsert` within the `ingest_data` function. This solves potential **out-of-memory errors** and **timeouts** in the serverless environment. |
| **Unique IDs** | Prevents data corruption on repeated ingestion. | IDs are generated using a URL hash concatenated with the chunk index (`{url_hash}-chunk-{i}`) to ensure every vector is unique upon upload. |
| **Configuration** | Manages environment secrets and settings. | All configuration (`PINECONE_API_KEY`, `GEMINI_API_KEY`, etc.) is securely loaded from **Google Cloud Environment Variables** using `os.environ.get()`. |

-----

## 🚀 Deployment and Usage

### Function Entry Point

  * **Function Name:** `ingest_data`
  * **Trigger:** **HTTP** (The function executes upon receiving a POST request to its public URL).

### Metadata Structure

Each vector includes the following metadata to enable RAG retrieval:

```json
{
  'metadata': {
    'text': 'Chunk content...',
    'source': 'https://example.com/page',
    'chunk_index': 0
  }
}
```

## Dependencies
- `firecrawl-py==1.5.0` - Web scraping
- `google-genai==0.2.2` - Embedding generation
- `pinecone==5.0.0` - Vector database

## License
This code is part of an AI Developer assignment for Hop Online.

## Author
Author: Rostislav Atanasov
Created as part of the RAG System Proof-of-Concept assignment.
