import streamlit as st
from utils.document_utils import process_uploaded_files, store_documents_in_supabase

def upload_documents_tab(supabase):
    st.header("Upload Documents")
    st.markdown("Upload your documents to include in the knowledge base.")
    
    doc_mode = st.radio(
        "Choose how to handle documents:",
        ["Append to existing documents", "Replace all existing documents"],
        index=0,
        help="Append will add documents to the existing knowledge base. Replace will clear all existing documents first."
    )
    
    uploaded_files = st.file_uploader(
        "Choose files to upload (PDF, TXT, CSV)",
        accept_multiple_files=True,
        type=["pdf", "txt", "csv"]
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Process Documents"):
            if uploaded_files:
                with st.spinner("Processing documents..."):
                    st.session_state.debug_info = "Starting document processing...\n"
                    mode = "replace" if "Replace" in doc_mode else "append"
                    st.session_state.debug_info += f"Using document mode: {mode}\n"
                    
                    docs, file_details = process_uploaded_files(uploaded_files)
                    if docs:
                        progress_bar = st.progress(0)
                        progress_text = st.empty()
                        progress_text.text("Storing documents in database...")
                        
                        vector_store = store_documents_in_supabase(docs, mode=mode)
                        progress_bar.progress(100)
                        progress_text.text("Document processing complete!")
                        
                        if vector_store:
                            st.session_state.docs_processed = True
                            st.success(f"Successfully processed {len(docs)} document chunks from {len(file_details)} files!")
                            for i, file_info in enumerate(file_details):
                                st.info(f"File {i+1}: {file_info['name']} - {file_info['chunks']} chunks")
                        else:
                            st.error("Failed to store documents in the database.")
                    else:
                        st.warning("No documents were processed. Please upload valid files.")
            else:
                st.warning("Please upload at least one file.")
    
    with col2:
        if st.button("View Document Count"):
            try:
                doc_count = supabase.table("documents").select("count", count="exact").execute()
                count = doc_count.count if hasattr(doc_count, 'count') else 0
                st.info(f"There are {count} document chunks in the database.")
                st.session_state.debug_info += f"Document count check: {count} chunks found\n"
            except Exception as e:
                st.error(f"Error checking document count: {str(e)}")
                st.session_state.debug_info += f"Error checking count: {str(e)}\n"