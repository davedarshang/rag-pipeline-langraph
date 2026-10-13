from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph

load_dotenv()


@dataclass
class RAGConfig:
    docs_dir: Path = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", "./chroma_db")).resolve()
    collection_name: str = os.getenv("COLLECTION_NAME", "ecommerce_docs")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")


class RAGState(TypedDict):
    question: str
    documents: List[Document]
    chunks: List[Document]
    retrieved_docs: List[Document]
    answer: str


SUPPORTED_TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".xml",
}


class RAGService:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.vectorstore: Optional[Chroma] = None
        self._initialize()

    def _initialize(self) -> None:
        docs = self.load_documents()
        if not docs:
            self.vectorstore = None
            return

        chunks = split_documents(docs, self.config)
        self.vectorstore = build_vectorstore(chunks, self.config)

    def load_documents(self) -> List[Document]:
        if not self.config.docs_dir.exists():
            print(f"Docs directory not found: {self.config.docs_dir}. Create a docs folder or set DOCS_DIR.")
            return []

        docs: List[Document] = []
        for file_path in sorted(self.config.docs_dir.rglob("*")):
            if file_path.is_dir():
                continue

            suffix = file_path.suffix.lower()
            if suffix in SUPPORTED_TEXT_EXTENSIONS:
                docs.extend(load_text_file(file_path))
            elif suffix == ".pdf":
                docs.extend(load_pdf_file(file_path))

        return docs

    def ask(self, question: str) -> str:
        if not question or not question.strip():
            return "Please enter a valid question."

        if self.vectorstore is None:
            return (
                "No documentation was loaded. Add files under the docs folder and ensure "
                "the environment is configured with OPENAI_API_KEY."
            )

        retrieved_docs = self.vectorstore.similarity_search(question, k=self.config.top_k)

        if not retrieved_docs:
            return "I could not find relevant information in the loaded documentation."

        llm = ChatOpenAI(model=self.config.llm_model, temperature=0)
        context = "\n\n---\n\n".join(
            [
                f"Source: {doc.metadata.get('source', 'unknown')}\n\n{doc.page_content}"
                for doc in retrieved_docs
            ]
        )

        prompt = f"""
You are a helpful assistant that answers questions using the project documentation.

Use only the information in the context below.
If the answer is not present, say so clearly.

Context:
{context}

Question:
{question}

Answer concisely and cite the relevant source file names when possible.
"""

        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content


def load_text_file(file_path: Path) -> List[Document]:
    try:
        loader = TextLoader(str(file_path), encoding="utf-8")
        return loader.load()
    except Exception as exc:
        print(f"Could not read text file {file_path}: {exc}")
        return []


def load_pdf_file(file_path: Path) -> List[Document]:
    try:
        loader = PyPDFLoader(str(file_path))
        return loader.load()
    except Exception as exc:
        print(f"Could not read PDF {file_path}: {exc}")
        return []


def split_documents(documents: List[Document], config: RAGConfig) -> List[Document]:
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def build_vectorstore(chunks: List[Document], config: RAGConfig) -> Chroma:
    if not chunks:
        raise ValueError("No document chunks available to index.")

    embeddings = OpenAIEmbeddings(model=config.embedding_model)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=config.collection_name,
        persist_directory=str(config.chroma_dir),
    )
    return vectorstore


def create_rag_pipeline(config: Optional[RAGConfig] = None) -> StateGraph:
    cfg = config or RAGConfig()

    class WorkflowState(TypedDict):
        question: str
        documents: List[Document]
        chunks: List[Document]
        retrieved_docs: List[Document]
        answer: str

    workflow = StateGraph(WorkflowState)

    workflow.add_node(
        "load_documents",
        lambda state: {
            "question": state["question"],
            "documents": load_documents_from_path(cfg.docs_dir),
            "chunks": [],
            "retrieved_docs": [],
            "answer": "",
        },
    )

    workflow.add_node(
        "split_documents",
        lambda state: {
            "question": state["question"],
            "documents": state["documents"],
            "chunks": split_documents(state["documents"], cfg),
            "retrieved_docs": [],
            "answer": "",
        },
    )

    workflow.add_node("retrieve_context", lambda state: retrieve_context(state, cfg))
    workflow.add_node("generate_answer", lambda state: generate_answer(state, cfg))

    workflow.set_entry_point("load_documents")
    workflow.add_edge("load_documents", "split_documents")
    workflow.add_edge("split_documents", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


def load_documents_from_path(docs_dir: Path) -> List[Document]:
    if not docs_dir.exists():
        return []

    documents: List[Document] = []
    for file_path in sorted(docs_dir.rglob("*")):
        if file_path.is_dir():
            continue
        suffix = file_path.suffix.lower()
        if suffix in SUPPORTED_TEXT_EXTENSIONS:
            documents.extend(load_text_file(file_path))
        elif suffix == ".pdf":
            documents.extend(load_pdf_file(file_path))

    return documents


def retrieve_context(state: dict[str, Any], config: RAGConfig) -> dict[str, Any]:
    question = state["question"]
    chunks = state["chunks"]

    if not chunks:
        state["retrieved_docs"] = []
        return state

    vectorstore = build_vectorstore(chunks, config)
    state["retrieved_docs"] = vectorstore.similarity_search(question, k=config.top_k)
    return state


def generate_answer(state: dict[str, Any], config: RAGConfig) -> dict[str, Any]:
    question = state["question"]
    docs = state["retrieved_docs"]

    if not docs:
        state["answer"] = "I could not find relevant information in the docs."
        return state

    context = "\n\n---\n\n".join(
        [
            f"Source: {doc.metadata.get('source', 'unknown')}\n\n{doc.page_content}"
            for doc in docs
        ]
    )

    llm = ChatOpenAI(model=config.llm_model, temperature=0)
    prompt = f"""
You are a helpful assistant using project documentation.

Context:
{context}

User question:
{question}

Answer using only the retrieved context. If the answer is not contained in the context, say so clearly.
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    state["answer"] = response.content
    return state


_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _service
    if _service is None:
        _service = RAGService()
    return _service


def answer_question(question: str) -> str:
    service = get_rag_service()
    return service.ask(question)


if __name__ == "__main__":
    print("LangGraph RAG documentation assistant")
    print(f"Docs path: {RAGConfig().docs_dir}")
    while True:
        question = input("\nAsk a question about the docs or type 'exit': ")
        if question.strip().lower() in {"exit", "quit", "q"}:
            break
        print("\nAnswer:\n")
        print(answer_question(question))

