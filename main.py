import os
import tempfile
import streamlit as st
from streamlit_chat import message

# LangChain Community imports
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores.utils import filter_complex_metadata


class ChatPDFAssistant:
    """Handles PDF ingestion, query processing, and answering queries using a chat model."""
    
    def __init__(self, pdf_file_path):
        self.model = ChatOllama(model="mistral") # Modify based on actual implementation
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100)
        self.prompt = self._create_prompt_template()
        self.vector_store = None
        self.retriever = None
        self.chain = None
        
        self.ingest_pdf(pdf_file_path)

    @staticmethod
    def _create_prompt_template():
        return ChatPromptTemplate.from_template(
            """
            <s> [INST] 
            You are an AI assistant with access to specific text snippets for answering questions.
            Your answers must be directly based only on the provided context.
            If the context does not contain enough information for a definitive answer, say that you don't know and ask the user to provide additional information. 
            [/INST] </s> 
            [INST] 
            Question: {question} 
            Context: {context} 
            Answer: 
            [/INST]
            """
        )
        
    def ingest_pdf(self, pdf_file_path: str):
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)
        self.vector_store = Chroma.from_documents(documents=chunks, embedding=FastEmbedEmbeddings())
        self._prepare_retriever()

    def _prepare_retriever(self):
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.5},
        )
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.model
                      | StrOutputParser())

    def ask(self, query: str):
        if not self.chain:
            return "Please, add a PDF document first."
        return self.chain.invoke(query)

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None

def setup_streamlit_page():
    st.set_page_config(page_title="Chat privately with your PDFs using a local LLM (Mistral 7B) and RAG", layout="wide")
    st.sidebar.title("Document Management")
    st.sidebar.text("You provided the PDF file during development.")
    if "assistant" not in st.session_state:
        pdf_file_path = "fimmtech_com (8).pdf"  # Provide the path to your PDF file here
        st.session_state["assistant"] = ChatPDFAssistant(pdf_file_path)
def display_chat_interface():
    st.subheader("Local Chatbot")
    chat_container = st.container()
    with chat_container:
        if "messages" not in st.session_state:
            st.session_state["messages"] = []
        for i, (msg, is_user) in enumerate(st.session_state["messages"]):
            message(msg, is_user=is_user, key=str(i))
    if "thinking_spinner" not in st.session_state:
        st.session_state["thinking_spinner"] = st.empty()

def setup_chat_page():
    setup_sidebar()
    st.header("Chat privately with your PDFs using a local LLM (Mistral 7B) and RAG")
    display_chat_interface()
    st.text_input("Message", key="user_input", on_change=process_user_input)

def setup_sidebar():
    st.sidebar.text("You provided the PDF file during development.")
    st.sidebar.text("No option for user to upload PDF files.")

def process_user_input():
    user_text = st.session_state["user_input"].strip()
    if user_text:
        with st.session_state["thinking_spinner"], st.spinner("Thinking"):
            agent_text = st.session_state["assistant"].ask(user_text)

        st.session_state["messages"].append((user_text, True))
        st.session_state["messages"].append((agent_text, False))

if __name__ == "__main__":
    setup_streamlit_page()
    setup_chat_page()
