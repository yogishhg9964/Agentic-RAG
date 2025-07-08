import os
from dotenv import load_dotenv
import streamlit as st
from supabase.client import create_client
from tabs.chat_tab import chat_tab
from tabs.upload_documents_tab import upload_documents_tab
from tabs.debug_info_tab import debug_info_tab

# Load environment variables
load_dotenv()

# Initialize session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "docs_processed" not in st.session_state:
    st.session_state.docs_processed = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "debug_info" not in st.session_state:
    st.session_state.debug_info = ""

# Check environment variables
required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    st.stop()

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Set page configuration
st.set_page_config(page_title="Agentic RAG Chatbot", page_icon="🦜", layout="wide")
st.title("🦜 Agentic RAG Chatbot")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Chat", "Upload Documents", "Debug Info"])

with tab1:
    chat_tab(supabase)

with tab2:
    upload_documents_tab(supabase)

with tab3:
    debug_info_tab(supabase)