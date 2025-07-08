import streamlit as st
from utils.document_utils import get_vector_store
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

def debug_info_tab(supabase):
    st.header("Debug Information")
    debug_tabs = st.tabs(["Log Messages", "Document Explorer", "Database Test"])
    
    with debug_tabs[0]:
        st.text_area("Debug Logs", value=st.session_state.debug_info, height=400, disabled=True)
    
    with debug_tabs[1]:
        st.subheader("Explore Documents in Database")
        try:
            st.write("Looking for document sources in the database...")
            sample_docs = supabase.table("documents").select("content, metadata").limit(10).execute()
            
            if sample_docs and hasattr(sample_docs, 'data') and sample_docs.data:
                sources = {}
                for doc in sample_docs.data:
                    if isinstance(doc.get('metadata'), dict) and 'source' in doc['metadata']:
                        source = doc['metadata']['source']
                        if source not in sources:
                            sources[source] = 0
                        sources[source] += 1
                
                if sources:
                    st.success(f"Found {len(sources)} different document sources")
                    for source, count in sources.items():
                        st.info(f"Source: {source} (at least {count} chunks)")
                else:
                    st.warning("No source information found in document metadata.")
                
                st.subheader("Sample Document Chunks")
                for i, doc in enumerate(sample_docs.data[:3]):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.write("**Metadata:**")
                        st.write(doc.get('metadata', {}))
                    with col2:
                        st.text_area(f"Content {i+1}", value=doc.get('content', '')[:500] + "...", height=150)
            else:
                st.warning("No document chunks found in the database.")
        except Exception as e:
            st.error(f"Error exploring documents: {str(e)}")
    
    with debug_tabs[2]:
        st.subheader("Database Connection Tests")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Test Database Connection"):
                try:
                    test_result = supabase.table("documents").select("id").limit(1).execute()
                    st.session_state.debug_info += f"Database connection test result: {test_result}\n"
                    st.success("Successfully connected to database!")
                except Exception as e:
                    st.session_state.debug_info += f"Database connection error: {str(e)}\n"
                    st.error(f"Connection error: {str(e)}")
            
            if st.button("Count Documents"):
                try:
                    doc_count = supabase.table("documents").select("count", count="exact").execute()
                    count = doc_count.count if hasattr(doc_count, 'count') else 0
                    st.info(f"There are {count} document chunks in the database.")
                    st.session_state.debug_info += f"Document count check: {count} chunks found\n"
                except Exception as e:
                    st.error(f"Error checking document count: {str(e)}")
                    st.session_state.debug_info += f"Error checking count: {str(e)}\n"
        
        with col2:
            if st.button("Test Embeddings"):
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/embedding-001",
                        google_api_key=os.environ.get("GEMINI_API_KEY"),
                    )
                    st.info("Testing embedding generation...")
                    test_embedding = embeddings.embed_query("This is a test query")
                    st.success(f"Successfully generated embedding vector of dimension {len(test_embedding)}")
                    st.session_state.debug_info += f"Embedding test successful. Vector dimension: {len(test_embedding)}\n"
                except Exception as e:
                    st.error(f"Embedding error: {str(e)}")
                    st.session_state.debug_info += f"Embedding test error: {str(e)}\n"
            
            if st.button("Test Vector Search"):
                try:
                    st.info("Testing vector search functionality...")
                    vs = get_vector_store()
                    results = vs.similarity_search("test query", k=1)
                    if results:
                        st.success("Vector search working correctly!")
                        st.session_state.debug_info += "Vector search test successful\n"
                    else:
                        st.warning("Vector search returned no results")
                        st.session_state.debug_info += "Vector search test: no results returned\n"
                except Exception as e:
                    st.error(f"Vector search error: {str(e)}")
                    st.session_state.debug_info += f"Vector search test error: {str(e)}\n"