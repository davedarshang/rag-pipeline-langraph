# RAG Pipeline for Docs (LangGraph + Python)

This project builds a retrieval-augmented generation (RAG) pipeline using LangGraph and Python to answer questions from a repository's `docs/` folder.

## Features
- Loads documents recursively from `docs/`
- Supports `.md`, `.txt`, `.rst`, `.csv`, `.json`, `.yaml`, `.yml`, and `.pdf`
- Splits content into chunks
- Embeds chunks with OpenAI embeddings
- Stores vectors in ChromaDB
- Retrieves relevant context using similarity search
- Uses a LangGraph workflow to answer questions

## Project structure

```text
.
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── rag_pipeline.py
├── docs/
├── chroma_db/
└── .venv/
```

## Setup

1. Clone the repository.
2. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the environment template and add your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

5. Add your files into the `docs/` directory.

## Run the pipeline

Interactive mode:

```bash
python rag_pipeline.py
```

You can then ask questions like:

```text
Ask a question about the docs (or type 'exit'): What is the architecture of the platform?
```

## Python API usage

```python
from rag_pipeline import answer_question

response = answer_question("What is the architecture of the platform?")
print(response)
```

## Notes
- The default documents directory is `./docs`.
- If the folder does not exist, the pipeline will return a graceful message.
- ChromaDB data is persisted in `./chroma_db`.

## Dependencies

Main libraries:
- langchain
- langchain-community
- langchain-openai
- langgraph
- chromadb
- python-dotenv
- pypdf

## License

MIT
