import os
import tempfile
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase.client import create_client
import sys

def process_uploaded_files(uploaded_files):
    """Process Streamlit uploaded files and convert them to document chunks."""
    with tempfile.TemporaryDirectory() as temp_dir:
        documents = []
        file_details = []
        
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            try:
                if file_extension == ".pdf":
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = uploaded_file.name
                        doc.metadata["file_type"] = "pdf"
                    documents.extend(docs)
                    file_details.append({"name": uploaded_file.name, "type": "pdf", "chunks": len(docs)})
                elif file_extension == ".txt":
                    loader = TextLoader(file_path)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = uploaded_file.name
                        doc.metadata["file_type"] = "txt"
                    documents.extend(docs)
                    file_details.append({"name": uploaded_file.name, "type": "txt", "chunks": len(docs)})
                elif file_extension == ".csv":
                    loader = CSVLoader(file_path)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = uploaded_file.name
                        doc.metadata["file_type"] = "csv"
                    documents.extend(docs)
                    file_details.append({"name": uploaded_file.name, "type": "csv", "chunks": len(docs)})
                else:
                    if 'st' in globals():
                        st.warning(f"Unsupported file format: {file_extension}")
                
                if 'st' in globals() and hasattr(st.session_state, 'debug_info'):
                    st.session_state.debug_info += f"Loaded {len(docs)} documents from {uploaded_file.name}\n"
            except Exception as e:
                if 'st' in globals():
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                    if hasattr(st.session_state, 'debug_info'):
                        st.session_state.debug_info += f"Error with {uploaded_file.name}: {str(e)}\n"
        
        if not documents:
            return None, None
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        document_chunks = text_splitter.split_documents(documents)
        
        for i, chunk in enumerate(document_chunks):
            if "source" not in chunk.metadata:
                chunk.metadata["source"] = f"unknown_source_{i}"
            chunk.metadata["chunk_index"] = i
        
        if 'st' in globals() and hasattr(st.session_state, 'debug_info'):
            st.session_state.debug_info += f"Created {len(document_chunks)} chunks from {len(documents)} documents\n"
            st.session_state.debug_info += f"File details: {str(file_details)}\n"
        
        return document_chunks, file_details

def process_files_from_paths(file_paths):
    documents = []
    file_details = []
    
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1].lower()
        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = file_name
                    doc.metadata["file_type"] = "pdf"
                documents.extend(docs)
                file_details.append({"name": file_name, "type": "pdf", "chunks": len(docs)})
            elif file_extension == ".txt":
                loader = TextLoader(file_path)
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = file_name
                    doc.metadata["file_type"] = "txt"
                documents.extend(docs)
                file_details.append({"name": file_name, "type": "txt", "chunks": len(docs)})
            elif file_extension == ".csv":
                loader = CSVLoader(file_path)
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = file_name
                    doc.metadata["file_type"] = "csv"
                documents.extend(docs)
                file_details.append({"name": file_name, "type": "csv", "chunks": len(docs)})
            else:
                print(f"Unsupported file format: {file_extension}", file=sys.stderr)
            
            print(f"Loaded {len(docs)} documents from {file_name}")
        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}", file=sys.stderr)
    
    if not documents:
        return None, None
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    document_chunks = text_splitter.split_documents(documents)
    
    for i, chunk in enumerate(document_chunks):
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = f"unknown_source_{i}"
        chunk.metadata["chunk_index"] = i
    
    print(f"Created {len(document_chunks)} chunks from {len(documents)} documents")
    print(f"File details: {str(file_details)}")
    return document_chunks, file_details

def store_documents_in_supabase(docs, mode="append"):
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        if mode == "replace":
            try:
                print("Attempting to clear existing documents...")
                response = supabase.table("documents").delete().neq("id", -1).execute()
                print(f"Successfully cleared existing documents. Response: {response}")
            except Exception as e:
                print(f"Error clearing documents: {str(e)}", file=sys.stderr)
        
        print(f"Generating embeddings for {len(docs)} documents...")
        
        # Process documents in batches
        batch_size = 50
        total_batches = (len(docs) - 1) // batch_size + 1
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            batch_num = i // batch_size + 1
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
            
            # Generate embeddings for this batch
            texts = [doc.page_content for doc in batch]
            embeddings_list = embeddings.embed_documents(texts)
            
            # Prepare documents for insertion
            documents_to_insert = []
            for j, doc in enumerate(batch):
                document_data = {
                    # Don't include 'id' - let the database auto-generate it
                    "content": doc.page_content,
                    "metadata": doc.metadata if doc.metadata else {},
                    "embedding": embeddings_list[j]
                }
                documents_to_insert.append(document_data)
            
            # Insert documents into Supabase
            try:
                response = supabase.table("documents").insert(documents_to_insert).execute()
                print(f"Successfully stored batch {batch_num}: {len(response.data)} documents inserted")
            except Exception as e:
                print(f"Error inserting batch {batch_num}: {str(e)}", file=sys.stderr)
                raise
        
        # Create and return a vector store instance for querying
        vector_store = SupabaseVectorStore(
            client=supabase,
            embedding=embeddings,
            table_name="documents"
            # Remove query_name since the function doesn't exist yet
        )
        
        print(f"Successfully stored all {len(docs)} document chunks")
        return vector_store
        
    except Exception as e:
        print(f"Error storing documents in Supabase: {str(e)}", file=sys.stderr)
        raise

def get_vector_store():
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Create a simple vector store without the match_documents function
        # We'll handle similarity search manually in the agent tools
        vector_store = SupabaseVectorStore(
            client=supabase,
            embedding=embeddings,
            table_name="documents"
            # Remove query_name since the function doesn't exist
        )
        print("Vector store initialized successfully.")
        return vector_store
    except Exception as e:
        print(f"Error initializing vector store: {str(e)}", file=sys.stderr)
        return None
