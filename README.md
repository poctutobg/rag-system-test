## 💻 Data Ingestion Module (`main.py`)

This Cloud Function powers the **data ingestion pipeline** for our Retrieval-Augmented Generation (RAG) system. It scrapes web content, chunks it for context preservation, embeds it using Gemini, and stores it in Pinecone for fast, semantic retrieval.

### ⚙️ Architecture

This is a fully **serverless**, **event-driven** pipeline:

```
HTTP Trigger → Firecrawl (Scraping) → Text Chunking → Gemini Embeddings → Pinecone Vector DB
```

Each step is modular, production-safe, and optimized for scale.

---

## ✨ Features and Engineering Notes

| Feature | Purpose | Implementation |
|--------|---------|----------------|
| **Smart Chunking** | Preserves context across long-form content. | `chunk_text()` splits input into 1000-character blocks with 50-character overlap. |
| **Consistent Embeddings** | Ensures compatibility with Pinecone. | Uses Gemini’s `text-embedding-004` model via `google.genai` (768-dim vectors). |
| **Batch Uploads** | Prevents memory blowouts and timeouts. | `ingest_data()` batches vectors (`BATCH_SIZE = 100`) before calling `pinecone.upsert`. |
| **Collision-Free IDs** | Avoids duplicate uploads. | Each chunk gets a unique ID: `{url_hash}-chunk-{i}`. |
| **Secure Config** | Keeps secrets out of the codebase. | API keys and settings are loaded via `os.environ.get()` from GCP env vars. |

---

## 🚀 Deployment & Usage

### Entry Point

- **Function Name:** `ingest_data`  
- **Trigger:** HTTP POST to the Cloud Function URL

### Metadata Format

Each vector includes metadata for traceability and retrieval:

```json
{
  "metadata": {
    "text": "Chunk content...",
    "source": "https://example.com/page",
    "chunk_index": 0
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
