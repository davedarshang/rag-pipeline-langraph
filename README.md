# LangGraph + Python RAG Documentation Assistant

This project creates a retrieval-augmented generation (RAG) system for repository documentation using:

- Python
- LangGraph
- LangChain
- OpenAI embeddings and chat models
- ChromaDB
- FastAPI
- Streamlit

## Architecture

The system loads documentation from a `docs/` directory, splits it into chunks, embeds those chunks, stores them in ChromaDB, and retrieves the most relevant segments for a user question before generating a grounded answer.

## Project structure

```text
.
├── api.py
├── app.py
├── rag_pipeline.py
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   └── README.md
└── chroma_db/
```

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
```

Then update `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
DOCS_DIR=./docs
CHROMA_DIR=./chroma_db
COLLECTION_NAME=ecommerce_docs
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=5
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

4. Add files to `docs/`.

## Run the CLI workflow

```bash
python rag_pipeline.py
```

## Run the API

```bash
uvicorn api:app --reload
```

Then open:

- `http://localhost:8000/docs` for Swagger UI
- `http://localhost:8000/health` for health check

Example request:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What does this project do?"}'
```

## Run the Streamlit app

```bash
streamlit run app.py
```

## Example document structure

```text
docs/
├── architecture.md
├── process.md
├── system-overview.md
└── api.md
```

## Notes

- The system persists the vector database under `./chroma_db`.
- If no `docs/` folder exists, the app will show a clear message rather than crashing.
- Use `.md`, `.txt`, `.json`, `.yaml`, `.html`, `.xml`, and `.pdf` files in the docs folder.

