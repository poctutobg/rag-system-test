# RAG System: Data Ingestion Cloud Function

This repository contains the Python source code for a serverless Google Cloud Function designed for the data ingestion pipeline of a Retrieval-Augmented Generation (RAG) system.

This function was created as part of a candidate assignment to demonstrate skills in cloud services, AI development, and automation.

## Overview

The function's core responsibility is to scrape web content from a specified URL, process it into smaller text chunks, generate vector embeddings for each chunk, and upload them to a Pinecone vector database. This creates a queryable knowledge base that a separate RAG pipeline can use to answer questions.

## Features

- **Flexible Scraping:** Utilizes the **Firecrawl API** for robust web scraping. It can be configured to either scrape a single page or crawl multiple pages of a website.
- **Content Processing:** Implements a text chunking strategy to split large documents into smaller, overlapping pieces, preserving semantic context.
- **Vectorization:** Leverages **Google's Gemini (`text-embedding-004`)** model to generate high-quality, 768-dimension vector embeddings for each text chunk.
- **Vector Storage:** Connects to a **Pinecone** vector database and uploads the vectors in batches to efficiently populate the index.
- **Configuration-Driven:** The entire process is controlled via environment variables, making it highly configurable without code changes.

## Technical Stack

- **Cloud Platform:** Google Cloud Platform (GCP)
- **Service:** Google Cloud Functions (2nd Gen)
- **Programming Language:** Python 3.12
- **Key Libraries:**
  - `google-generativeai`: For generating text embeddings.
  - `pinecone-client`: For interacting with the Pinecone vector database.
  - `firecrawl-py`: For reliable, Markdown-based web scraping.

## How to Use

This function is designed to be deployed as an HTTP-triggered Google Cloud Function.

### Environment Variables

The following environment variables must be configured in the GCP environment for the function to operate correctly:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `TARGET_URL` | The starting URL to scrape. | `https://stripe.com/docs/api` |
| `PINECONE_API_KEY` | Your API key for Pinecone. | `xxxx-xxxx-xxxx-xxxx` |
| `GEMINI_API_KEY` | Your API key for Google AI Studio. | `AIzaSy...` |
| `FIRECRAWL_API_KEY` | Your API key for Firecrawl. | `fc-xxxx...` |
| `INDEX_NAME` | The name of the target index in Pinecone. | `stripe-api-docs` |
| `CRAWL_MODE` | The scraping mode. Can be `single` or `crawl`. | `single` |
| `MAX_PAGES` | The maximum number of pages to scrape in `crawl` mode. | `5` |

### Triggering the Function

Once deployed, the function can be triggered by sending an HTTP GET request to its public URL. This will initiate the scraping and ingestion process. The function's logs can be monitored in the Google Cloud Logging (Cloud Logging ) interface to track progress.
