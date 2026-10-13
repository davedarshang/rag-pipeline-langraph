import os
from pathlib import Path
from typing import List, TypedDict

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph

load_dotenv()

DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "./chroma_db")).resolve()
COLLECTION_NAME = "ecommerce_docs"


class RAGState(TypedDict):
    question: str
    documents: List[Document]
    chunks: List[Document]
    retrieved_docs: List[Document]
    answer: str


def _load_text_file(file_path: Path) -> List[Document]:
    try:
        loader = TextLoader(str(file_path), encoding="utf-8")
        return loader.load()
    except Exception as exc:
        print(f"Could not read text file {file_path}: {exc}")
        return []


def _load_pdf(file_path: Path) -> List[Document]:
    try:
        loader = PyPDFLoader(str(file_path))
        return loader.load()
    except Exception as exc:
        print(f"Could not read PDF {file_path}: {exc}")
        return []


def load_documents(docs_dir: Path = DOCS_DIR) -> List[Document]:
    """Load documents from a directory recursively."""
    if not docs_dir.exists():
        print(f"Docs directory not found: {docs_dir}. Add a docs/ folder or set DOCS_DIR.")
        return []

    supported_text_exts = {
        ".md",
        ".txt",
        ".rst",
        ".csv",
        ".json",
        ".yaml",
        ".yml",
    }

    documents: List[Document] = []

    for file_path in sorted(docs_dir.rglob("*")):
        if file_path.is_dir():
            continue

        suffix = file_path.suffix.lower()

        if suffix in supported_text_exts:
            docs = _load_text_file(file_path)
            documents.extend(docs)
        elif suffix == ".pdf":
            docs = _load_pdf(file_path)
            documents.extend(docs)

    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def build_vectorstore(chunks: List[Document]) -> Chroma:
    if not chunks:
        raise ValueError("No document chunks available to index.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )

    return vectorstore


def retrieve_context(state: RAGState) -> RAGState:
    question = state["question"]
    chunks = state["chunks"]

    if not chunks:
        state["retrieved_docs"] = []
        return state

    vectorstore = build_vectorstore(chunks)
    retrieved_docs = vectorstore.similarity_search(question, k=5)
    state["retrieved_docs"] = retrieved_docs
    return state


def generate_answer(state: RAGState) -> RAGState:
    question = state["question"]
    retrieved_docs = state["retrieved_docs"]

    if not retrieved_docs:
        state["answer"] = (
            "I couldn't find relevant information in the docs folder. "
            "Please make sure the docs directory contains supported files and try again."
        )
        return state

    context = "\n\n---\n\n".join(
        [
            f"Source: {doc.metadata.get('source', 'unknown')}\n\n{doc.page_content}"
            for doc in retrieved_docs
        ]
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = f"""
You are a helpful assistant that answers questions using the project's documentation.

Use only the context below to answer the question. If the answer is not in the context, say so clearly.

Context:
{context}

Question:
{question}

Answer in a clear and concise way and cite relevant sources when possible.
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    state["answer"] = response.content
    return state


def create_rag_pipeline() -> StateGraph:
    workflow = StateGraph(RAGState)

    workflow.add_node(
        "load_documents",
        lambda state: {
            "question": state["question"],
            "documents": load_documents(),
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
            "chunks": split_documents(state["documents"]),
            "retrieved_docs": [],
            "answer": "",
        },
    )

    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_answer", generate_answer)

    workflow.set_entry_point("load_documents")
    workflow.add_edge("load_documents", "split_documents")
    workflow.add_edge("split_documents", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


def answer_question(question: str) -> str:
    app = create_rag_pipeline()
    result = app.invoke(
        {
            "question": question,
            "documents": [],
            "chunks": [],
            "retrieved_docs": [],
            "answer": "",
        }
    )
    return result["answer"]


if __name__ == "__main__":
    print("RAG documentation assistant is ready.")
    print(f"Looking for docs under: {DOCS_DIR}")

    while True:
        question = input("\nAsk a question about the docs (or type 'exit'): ")
        if question.strip().lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break

        if not question.strip():
            continue

        answer = answer_question(question)
        print("\nAnswer:\n")
        print(answer)
