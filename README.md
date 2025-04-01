# Google Drive Document RAG with PostgreSQL Vector Search

This application allows you to search and query your Google Drive documents using Retrieval-Augmented Generation (RAG). It downloads documents from your Google Drive, creates embeddings, and stores them in a PostgreSQL database using Timescale's vector search capabilities. You can then ask questions about your documents and receive AI-generated answers based on their content.

## Features

- Connect to Google Drive API to access your documents
- Search for documents by name in your Google Drive
- Download and process documents (supports Google Docs, Google Sheets, Word documents, text files)
- Extract text content from various file formats including PDFs and DOCX files
- Generate embeddings using OpenAI's `text-embedding-3-small` model
- Store embeddings in PostgreSQL for efficient vector search
- Web interface with FastAPI for easy document processing and querying
- REST API endpoints for integrating with other applications
- Interactive command-line interface for document processing and querying
- AI-powered question answering based on your document content
- Detailed thought process and context sufficiency information with query results

## Pgvectorscale Documentation

For more information about using PostgreSQL as a vector database in AI applications with Timescale, check out these resources:

- [GitHub Repository: pgvectorscale](https://github.com/timescale/pgvectorscale)
- [Blog Post: PostgreSQL and Pgvector: Now Faster Than Pinecone, 75% Cheaper, and 100% Open Source](https://www.timescale.com/blog/pgvector-is-now-as-fast-as-pinecone-at-75-less-cost/)
- [Blog Post: RAG Is More Than Just Vector Search](https://www.timescale.com/blog/rag-is-more-than-just-vector-search/)
- [Blog Post: A Python Library for Using PostgreSQL as a Vector Database in AI Applications](https://www.timescale.com/blog/a-python-library-for-using-postgresql-as-a-vector-database-in-ai-applications/)

## Why PostgreSQL?

Using PostgreSQL with pgvectorscale as your vector database offers several key advantages over dedicated vector databases:

- PostgreSQL is a robust, open-source database with a rich ecosystem of tools, drivers, and connectors. This ensures transparency, community support, and continuous improvements.

- By using PostgreSQL, you can manage both your relational and vector data within a single database. This reduces operational complexity, as there's no need to maintain and synchronize multiple databases.

- Pgvectorscale enhances pgvector with faster search capabilities, higher recall, and efficient time-based filtering. It leverages advanced indexing techniques, such as the DiskANN-inspired index, to significantly speed up Approximate Nearest Neighbor (ANN) searches.

Pgvectorscale Vector builds on top of [pgvector](https://github.com/pgvector/pgvector), offering improved performance and additional features, making PostgreSQL a powerful and versatile choice for AI applications.

## Prerequisites

- Docker
- Python 3.7+
- OpenAI API key
- PostgreSQL GUI client

## Steps

1. Set up Docker environment
2. Connect to the database using a PostgreSQL GUI client (I use TablePlus)
3. Create a Python script to insert document chunks as vectors using OpenAI embeddings
4. Create a Python function to perform similarity search

## Detailed Instructions

### 1. Set up Docker environment

Create a `docker-compose.yml` file with the following content:

```yaml
name: googledrive-embeddings

services:
  timescaledb:
    image: timescale/timescaledb-ha:pg16
    container_name: timescaledb
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5433:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - app-network

  webapi:
    build:
      context: ../
      dockerfile: docker/Dockerfile
    container_name: googledrive-api
    environment:
      - TIMESCALE_SERVICE_URL=postgres://postgres:password@timescaledb:5432/postgres
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ../:/app
      - ../token.json:/app/token.json
      - ../client_secret_1054911966299-ntoekdnpbnl07lr76fjsnkjh0c288r72.apps.googleusercontent.com.json:/app/client_secret_1054911966299-ntoekdnpbnl07lr76fjsnkjh0c288r72.apps.googleusercontent.com.json
    ports:
      - "8000:8000"
    depends_on:
      - timescaledb
    restart: unless-stopped
    networks:
      - app-network

volumes:
  timescaledb_data:

networks:
  app-network:
    driver: bridge
```

Run the Docker container:

```bash
cd docker
docker-compose up -d
```

This will start both the database and the web API on http://localhost:8000

### 2. Connect to the database using a PostgreSQL GUI client

- Open client
- Create a new connection with the following details:
  - Host: localhost
  - Port: 5432
  - User: postgres
  - Password: password
  - Database: postgres

### 3. Create a Python script to insert document chunks as vectors

See `insert_vectors.py` for the implementation. This script uses OpenAI's `text-embedding-3-small` model to generate embeddings.

### 4. Create a Python function to perform similarity search

See `similarity_search.py` for the implementation. This script also uses OpenAI's `text-embedding-3-small` model for query embedding.

## Usage

1. Create a `.env` file in the `app` directory with the following content:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TIMESCALE_SERVICE_URL=postgres://postgres:password@localhost:5433/postgres
   ```

2. Run the Docker container:
   ```bash
   cd docker
   docker-compose up -d
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application in one of two ways:

   a. Using the web interface (recommended):
   ```bash
   cd app
   python main.py
   ```
   Then open http://localhost:8000 in your browser
   
   b. Using the command-line interface:
   ```bash
   cd app
   python google_drive_processor.py
   ```

5. With the web interface:
   - Navigate to the "Process File" tab to process files from Google Drive
   - Navigate to the "Ask Questions" tab to query your documents
   - You'll be prompted to authenticate via OAuth during first use
   
   Or follow the interactive command-line prompts to:
   - Process a file from your Google Drive
   - Ask questions about your documents
   
6. API Endpoints (for developers):
   - `POST /api/process`: Process a file from Google Drive
     ```json
     {
       "file_name": "Your Document Name"
     }
     ```
   - `POST /api/query`: Ask a question about your documents
     ```json
     {
       "query": "Your question here?",
       "limit": 5
     }
     ```

## Using ANN search indexes to speed up queries

Timescale Vector offers indexing options to accelerate similarity queries, particularly beneficial for large vector datasets (10k+ vectors):

1. Supported indexes:
   - timescale_vector_index (default): A DiskANN-inspired graph index
   - pgvector's HNSW: Hierarchical Navigable Small World graph index
   - pgvector's IVFFLAT: Inverted file index

2. The DiskANN-inspired index is Timescale's latest offering, providing improved performance. Refer to the [Timescale Vector explainer blog](https://www.timescale.com/blog/pgvector-is-now-as-fast-as-pinecone-at-75-less-cost/) for detailed information and benchmarks.

For optimal query performance, creating an index on the embedding column is recommended, especially for large vector datasets.

## Cosine Similarity in Vector Search

### What is Cosine Similarity?

Cosine similarity measures the cosine of the angle between two vectors in a multi-dimensional space. It's a measure of orientation rather than magnitude.

- Range: -1 to 1 (for normalized vectors, which is typical in text embeddings)
- 1: Vectors point in the same direction (most similar)
- 0: Vectors are orthogonal (unrelated)
- -1: Vectors point in opposite directions (most dissimilar)

### Cosine Distance

In pgvector, the `<=>` operator computes cosine distance, which is 1 - cosine similarity.

- Range: 0 to 2
- 0: Identical vectors (most similar)
- 1: Orthogonal vectors
- 2: Opposite vectors (most dissimilar)

### Interpreting Results

When you get results from similarity_search:

- Lower distance values indicate higher similarity.
- A distance of 0 would mean exact match (rarely happens with embeddings).
- Distances closer to 0 indicate high similarity.
- Distances around 1 suggest little to no similarity.
- Distances approaching 2 indicate opposite meanings (rare in practice).
