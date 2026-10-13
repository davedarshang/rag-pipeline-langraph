import os
from pathlib import Path

import streamlit as st

from rag_pipeline import answer_question

st.set_page_config(page_title="Docs RAG Assistant", page_icon="📚", layout="wide")
st.title("Docs RAG Assistant")

with st.sidebar:
    st.header("Configuration")
    st.caption("This app answers questions from the docs folder using a LangGraph + vector search workflow.")
    st.caption(f"Docs directory: {Path('./docs').resolve()}")
    st.caption(f"Chroma DB: {Path('./chroma_db').resolve()}")

question = st.text_area("Ask a question about the project documentation", height=120)

if st.button("Ask") and question.strip():
    with st.spinner("Searching the documentation..."):
        answer = answer_question(question)
    st.markdown("### Answer")
    st.write(answer)
else:
    st.info("Type a question to begin.")

