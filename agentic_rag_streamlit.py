# import basics
import os
import tempfile
import uuid
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
import re
import sys

# import streamlit
import streamlit as st

# import langchain
from langchain.agents import AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# import supabase db
from supabase.client import create_client

# load environment variables
load_dotenv()

# Initialize session state variables
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "docs_processed" not in st.session_state:
    st.session_state.docs_processed = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "voice_messages" not in st.session_state:
    st.session_state.voice_messages = []
if "debug_info" not in st.session_state:
    st.session_state.debug_info = ""
if "voice_active" not in st.session_state:
    st.session_state.voice_active = False

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

# Initialize embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.environ.get("GEMINI_API_KEY"),
)

# Voice agent functions
def clean_text_for_speech(text):
    cleaned_text = re.sub(r'[\*\-#\[\]\(\)]', '', text)
    cleaned_text = ' '.join(cleaned_text.split())
    return cleaned_text

def process_response_for_speech(text, for_voice_tab=False):
    segments = []
    current_pos = 0
    
    code_regex = re.compile(r'<CODE>(.*?)</CODE>', re.DOTALL)
    explanation_regex = re.compile(r'<CODE_EXPLANATION>(.*?)</CODE_EXPLANATION>', re.DOTALL)
    
    while current_pos < len(text):
        code_match = code_regex.search(text, current_pos)
        exp_match = explanation_regex.search(text, current_pos)
        
        next_match = None
        if code_match and exp_match:
            next_match = code_match if code_match.start() < exp_match.start() else exp_match
        elif code_match:
            next_match = code_match
        elif exp_match:
            next_match = exp_match
        
        if not next_match:
            segments.append(('text', text[current_pos:]))
            break
        
        if next_match.start() > current_pos:
            segments.append(('text', text[current_pos:next_match.start()]))
        
        if next_match == code_match:
            segments.append(('code', next_match.group(1)))
        else:
            segments.append(('code_explanation', next_match.group(1)))
        
        current_pos = next_match.end()
    
    final_segments = []
    for seg_type, content in segments:
        if seg_type in ('code', 'code_explanation'):
            final_segments.append((seg_type, content))
            continue
        
        list_regex = re.compile(r'(\d+\.\s+[^\n]+)')
        list_matches = list_regex.finditer(content)
        last_pos = 0
        
        for match in list_matches:
            if match.start() > last_pos:
                final_segments.append(('text', content[last_pos:match.start()]))
            num = match.group(1).split('.')[0]
            item_text = match.group(0)[len(num)+2:].strip()
            final_segments.append(('list', f"Point {num}, {item_text}"))
            last_pos = match.end()
        
        if last_pos < len(content):
            remaining = content[last_pos:]
            sentences = re.split(r'(?<=[.!?])\s+', remaining)
            for sentence in sentences:
                if sentence.strip():
                    seg_type = 'question' if sentence.strip().endswith('?') else 'text'
                    final_segments.append((seg_type, sentence.strip()))
    
    if for_voice_tab:
        # For voice tab: only return code for display, speak text/list/question
        display_segments = [(seg_type, content) for seg_type, content in final_segments if seg_type == 'code']
        spoken_segments = [(seg_type, clean_text_for_speech(content)) for seg_type, content in final_segments if seg_type in ('text', 'list', 'question', 'code_explanation')]
        return display_segments, spoken_segments
    else:
        # For chat tab: return all segments for display and speech
        spoken_segments = [(seg_type, clean_text_for_speech(content)) for seg_type, content in final_segments]
        return final_segments, spoken_segments

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.session_state.debug_info += "Listening for voice input...\n"
        recognizer.adjust_for_ambient_noise(source, duration=2)
        recognizer.pause_threshold = 1.5
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            st.session_state.debug_info += "Processing audio...\n"
            text = recognizer.recognize_google(audio)
            st.session_state.debug_info += f"Recognized: {text}\n"
            return text
        except sr.UnknownValueError:
            st.session_state.debug_info += "Could not understand audio.\n"
            speak("Sorry, I didn't catch that. Could you please repeat?")
            return None
        except sr.RequestError as e:
            st.session_state.debug_info += f"Speech recognition error: {str(e)}\n"
            speak("I'm having trouble with speech recognition. Please try again.")
            return None
        except sr.WaitTimeoutError:
            st.session_state.debug_info += "Timed out waiting for speech.\n"
            return None

def speak(text, is_question=False):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        if is_question:
            engine.setProperty('pitch', 1.2)
        engine.say(text)
        engine.runAndWait()
        st.session_state.debug_info += f"Spoke: {text}\n"
    except Exception as e:
        st.session_state.debug_info += f"Speech synthesis error: {str(e)}\n"

def is_command(user_input, command_keywords):
    if user_input is None:
        return False
    return any(keyword in user_input.lower() for keyword in command_keywords)

# Document processing functions
def process_uploaded_files(uploaded_files):
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
                    st.warning(f"Unsupported file format: {file_extension}")
                
                st.session_state.debug_info += f"Loaded {len(docs)} documents from {uploaded_file.name}\n"
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                st.session_state.debug_info += f"Error with {uploaded_file.name}: {str(e)}\n"
        
        if not documents:
            return None, None
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        document_chunks = text_splitter.split_documents(documents)
        
        for i, chunk in enumerate(document_chunks):
            if "source" not in chunk.metadata:
                chunk.metadata["source"] = f"unknown_source_{i}"
            chunk.metadata["chunk_index"] = i
        
        st.session_state.debug_info += f"Created {len(document_chunks)} chunks from {len(documents)} documents\n"
        st.session_state.debug_info += f"File details: {str(file_details)}\n"
        return document_chunks, file_details

def store_documents_in_supabase(docs, mode="append"):
    try:
        if mode == "replace":
            try:
                st.session_state.debug_info += "Attempting to clear existing documents...\n"
                supabase.table("documents").delete().execute()
                st.session_state.debug_info += "Successfully cleared existing documents\n"
            except Exception as e:
                st.session_state.debug_info += f"Error clearing documents: {str(e)}\n"
        
        batch_size = 50
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            st.session_state.debug_info += f"Processing batch {i//batch_size + 1}/{(len(docs)-1)//batch_size + 1} ({len(batch)} chunks)...\n"
            
            vector_store = SupabaseVectorStore.from_documents(
                batch,
                embeddings,
                client=supabase,
                table_name="documents",
                query_name="match_documents",
            )
            
            st.session_state.debug_info += f"Successfully stored batch {i//batch_size + 1}\n"
        
        st.session_state.vector_store = SupabaseVectorStore(
            embedding=embeddings,
            client=supabase,
            table_name="documents",
            query_name="match_documents",
        )
        
        st.session_state.debug_info += "All documents successfully stored in Supabase\n"
        return st.session_state.vector_store
    except Exception as e:
        st.error(f"Error storing documents in Supabase: {str(e)}")
        st.session_state.debug_info += f"Error storing documents: {str(e)}\n"
        return None

def get_vector_store():
    if st.session_state.vector_store:
        return st.session_state.vector_store
    else:
        vector_store = SupabaseVectorStore(
            embedding=embeddings,
            client=supabase,
            table_name="documents",
            query_name="match_documents",
        )
        st.session_state.vector_store = vector_store
        return vector_store

# Set page configuration
st.set_page_config(page_title="Agentic RAG Chatbot with Voice", page_icon="🦜", layout="wide")
st.title("🦜 Agentic RAG Chatbot with Voice")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Chat", "Voice Assistant", "Upload Documents", "Debug Info"])

with tab3:
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

with tab4:
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

# Initialize LLM and Agent
vector_store = get_vector_store()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.2,
    max_output_tokens=4096,
    top_p=0.95,
)

AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an advanced AI research assistant designed to help students understand concepts from provided documents. Provide CLEAR, CONCISE, and STUDENT-FRIENDLY explanations based ONLY on the information in the documents.

    IMPORTANT RULES:
    1. ALWAYS use the retrieve_documents tool on EVERY question before answering.
    2. NEVER use your own knowledge. ONLY use information from the retrieved documents.
    3. If the documents don't contain the information, say "I don't have that information in my documents."
    4. Do not make up information or use any external knowledge.

    HOW TO PROVIDE EXCELLENT ANSWERS:
    1. Use the retrieve_documents tool to gather ALL relevant information.
    2. Explain concepts in a way that is easy for students to understand, using simple language and examples from the documents.
    3. Break down complex ideas into clear steps or points.
    4. For voice interactions, use conversational language with interactive cues like 'Let me explain,' 'Does that make sense?' or 'Want to dive deeper?'
    5. Include code snippets in <CODE>...</CODE> tags and explanations in <CODE_EXPLANATION>...</CODE_EXPLANATION> tags when relevant.
    6. Organize answers with bullet points or numbered lists for clarity.
    7. Cite specific quotes or references to the source documents.
    8. Ensure explanations are complete but concise, focusing on helping students grasp the concept.
    9. In voice mode, prioritize spoken explanations and minimize text output except for code or key points."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

DIRECT_RETRIEVAL_TEMPLATE = """You are an advanced AI research assistant designed to help students understand concepts from provided documents. Provide CLEAR, CONCISE, and STUDENT-FRIENDLY explanations based ONLY on the information in the documents.

If you don't know the answer based on the documents, say "I don't have that information in my documents." 
NEVER use any knowledge outside of the documents.

HOW TO PROVIDE EXCELLENT ANSWERS:
1. Analyze ALL information in the provided context.
2. Explain concepts in a way that is easy for students to understand, using simple language and examples.
3. Break down complex ideas into clear steps or points.
4. Include code snippets in <CODE>...</CODE> tags and explanations in <CODE_EXPLANATION>...</CODE_EXPLANATION> tags when relevant.
5. Organize answers with bullet points or numbered lists for clarity.
6. Cite specific quotes or references to the source documents.
7. Ensure explanations are complete but concise, focusing on helping students grasp the concept.

Context information from documents:
{context}

Question: {question}

Detailed and Comprehensive Answer:"""

@tool(response_format="content_and_artifact")
def retrieve_documents(query: str):
    """ALWAYS use this tool to retrieve information from documents before answering any question."""
    st.session_state.debug_info += f"Retrieving documents for query: {query}\n"
    try:
        retriever = get_vector_store().as_retriever(search_kwargs={"k": 15})
        retrieved_docs = retriever.get_relevant_documents(query)
        
        if not retrieved_docs:
            st.session_state.debug_info += "No documents retrieved!\n"
            return "No relevant documents found in the database.", []
        
        st.session_state.debug_info += f"Retrieved {len(retrieved_docs)} documents\n"
        
        sources = {}
        for doc in retrieved_docs:
            source = doc.metadata.get("source", "Unknown Source")
            if source not in sources:
                sources[source] = []
            sources[source].append(doc)
        
        formatted_results = []
        for source, docs in sources.items():
            source_text = f"## Source: {source}\n\n"
            for i, doc in enumerate(docs):
                source_text += f"### Excerpt {i+1}:\n{doc.page_content}\n\n"
            formatted_results.append(source_text)
        
        serialized = "\n\n".join(formatted_results)
        
        if retrieved_docs:
            st.session_state.debug_info += f"First document from: {retrieved_docs[0].metadata.get('source', 'Unknown')}\n"
            st.session_state.debug_info += f"Content preview: {retrieved_docs[0].page_content[:200]}...\n"
            st.session_state.debug_info += f"Total unique sources: {len(sources)}\n"
        
        return serialized, retrieved_docs
    except Exception as e:
        error_msg = f"Error retrieving documents: {str(e)}"
        st.session_state.debug_info += f"{error_msg}\n"
        return error_msg, []

retriever = vector_store.as_retriever(search_kwargs={"k": 8})
direct_qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={
        "prompt": PromptTemplate.from_template(DIRECT_RETRIEVAL_TEMPLATE),
        "verbose": True
    }
)

tools = [retrieve_documents]

agent = create_tool_calling_agent(llm, tools, AGENT_PROMPT)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    return_direct_tool_output=False,
)

# Voice command handling
def process_voice_command(user_input):
    upload_keywords = ["upload", "add document", "process file", "load pdf", "add pdf", "upload document"]
    clear_keywords = ["clear documents", "reset database", "delete documents"]
    query_keywords = ["search", "find", "what does", "tell me about", "query", "ask about"]
    exit_keywords = ["exit", "stop", "quit", "end"]
    
    if is_command(user_input, upload_keywords):
        return "upload"
    elif is_command(user_input, clear_keywords):
        return "clear"
    elif is_command(user_input, exit_keywords):
        return "exit"
    elif is_command(user_input, query_keywords) or not is_command(user_input, upload_keywords + clear_keywords + exit_keywords):
        return "query"
    return None

with tab1:
    # Chat Tab: Text and Voice Input (Existing Behavior)
    doc_count_info = ""
    try:
        doc_count = supabase.table("documents").select("count", count="exact").execute()
        count = doc_count.count if hasattr(doc_count, 'count') else 0
        if count == 0:
            doc_count_info = "⚠️ No documents found in the knowledge base. Please upload documents in the 'Upload Documents' tab."
        else:
            doc_count_info = f"📚 {count} document chunks in the knowledge base."
    except Exception as e:
        doc_count_info = "⚠️ Could not check document count."
        st.session_state.debug_info += f"Error checking document count: {str(e)}\n"
    
    st.markdown(doc_count_info)
    
    if st.button("🎤 Use Voice Input"):
        st.session_state.voice_active = True
        with st.spinner("Listening..."):
            user_input = recognize_speech()
            if user_input:
                st.session_state.debug_info += f"Voice command: {user_input}\n"
                command_type = process_voice_command(user_input)
                
                if command_type == "upload":
                    speak("Please use the file uploader in the Upload Documents tab to select your files, then say 'process files' to confirm.")
                    st.warning("Please upload files using the file uploader, then confirm with 'process files' via voice.")
                
                elif command_type == "clear":
                    speak("Clearing all documents from the database.")
                    try:
                        supabase.table("documents").delete().execute()
                        st.session_state.vector_store = None
                        st.session_state.docs_processed = False
                        st.success("All documents cleared from the database.")
                        st.session_state.debug_info += "Documents cleared from database\n"
                    except Exception as e:
                        st.error(f"Error clearing documents: {str(e)}")
                        st.session_state.debug_info += f"Error clearing documents: {str(e)}\n"
                
                elif command_type == "query" or command_type is None:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                        st.session_state.messages.append(HumanMessage(user_input))
                    
                    try:
                        if count == 0:
                            with st.chat_message("assistant"):
                                error_message = "I don't have any documents to search through. Please upload documents in the 'Upload Documents' tab first."
                                st.markdown(error_message)
                                speak(error_message)
                                st.session_state.messages.append(AIMessage(error_message))
                            st.session_state.voice_active = False
                            st.stop()
                    except Exception as e:
                        st.session_state.debug_info += f"Error checking count before query: {str(e)}\n"
                    
                    with st.spinner("Searching through documents..."):
                        try:
                            chat_history = []
                            for message in st.session_state.messages[:-1]:
                                if isinstance(message, HumanMessage):
                                    chat_history.append(("human", message.content))
                                elif isinstance(message, AIMessage):
                                    chat_history.append(("ai", message.content))
                            
                            try:
                                result = agent_executor.invoke({
                                    "input": user_input,
                                    "chat_history": chat_history
                                })
                                ai_message = result["output"]
                                st.session_state.debug_info += "Agent generated answer\n"
                            except Exception as agent_error:
                                st.session_state.debug_info += f"Agent error: {str(agent_error)}. Falling back to direct retrieval.\n"
                                result = direct_qa.invoke({"question": user_input})
                                ai_message = result["result"]
                                st.session_state.debug_info += "Direct retrieval generated answer\n"
                            
                            if "I don't have" not in ai_message and count < 3:
                                st.warning("⚠️ Warning: The assistant might be using information outside of your documents. Consider uploading more relevant documents.")
                            
                            with st.chat_message("assistant"):
                                st.markdown(ai_message)
                                display_segments, spoken_segments = process_response_for_speech(ai_message, for_voice_tab=False)
                                
                                for seg_type, content in display_segments:
                                    if seg_type == 'code':
                                        st.write("**Code:**")
                                        st.code(content, language="python")
                                    else:
                                        st.markdown(content)
                                
                                final_spoken = []
                                has_code = any(seg_type == 'code' for seg_type, _ in display_segments)
                                for seg_type, content in spoken_segments:
                                    final_spoken.append((seg_type, content))
                                if has_code:
                                    final_spoken.append(('text', "Try running this code and let me know how it goes!"))
                                
                                for seg_type, content in final_spoken:
                                    speak(content, is_question=(seg_type == 'question'))
                                
                                st.session_state.messages.append(AIMessage(ai_message))
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            st.session_state.debug_info += f"Error during query processing: {str(e)}\n"
                            with st.chat_message("assistant"):
                                error_message = "I encountered an error while trying to answer your question. Please try again or check the Debug tab for more information."
                                st.markdown(error_message)
                                speak(error_message)
                                st.session_state.messages.append(AIMessage(error_message))
                
                st.session_state.voice_active = False
    
    # Display chat history
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)
    
    # Manual text input
    user_question = st.chat_input("Ask a question about your documents...")
    if user_question:
        with st.chat_message("user"):
            st.markdown(user_question)
            st.session_state.messages.append(HumanMessage(user_question))
        
        try:
            doc_count = supabase.table("documents").select("count", count="exact").execute()
            count = doc_count.count if hasattr(doc_count, 'count') else 0
            if count == 0:
                with st.chat_message("assistant"):
                    error_message = "I don't have any documents to search through. Please upload documents in the 'Upload Documents' tab first."
                    st.markdown(error_message)
                    speak(error_message)
                    st.session_state.messages.append(AIMessage(error_message))
                st.stop()
        except Exception as e:
            st.session_state.debug_info += f"Error checking count before query: {str(e)}\n"
        
        with st.spinner("Searching through documents..."):
            try:
                chat_history = []
                for message in st.session_state.messages[:-1]:
                    if isinstance(message, HumanMessage):
                        chat_history.append(("human", message.content))
                    elif isinstance(message, AIMessage):
                        chat_history.append(("ai", message.content))
                
                try:
                    result = agent_executor.invoke({
                        "input": user_question,
                        "chat_history": chat_history
                    })
                    ai_message = result["output"]
                    st.session_state.debug_info += "Agent generated answer\n"
                except Exception as agent_error:
                    st.session_state.debug_info += f"Agent error: {str(agent_error)}. Falling back to direct retrieval.\n"
                    result = direct_qa.invoke({"question": user_question})
                    ai_message = result["result"]
                    st.session_state.debug_info += "Direct retrieval generated answer\n"
                
                if "I don't have" not in ai_message and count < 3:
                    st.warning("⚠️ Warning: The assistant might be using information outside of your documents. Consider uploading more relevant documents.")
                
                with st.chat_message("assistant"):
                    st.markdown(ai_message)
                    display_segments, spoken_segments = process_response_for_speech(ai_message, for_voice_tab=False)
                    
                    for seg_type, content in display_segments:
                        if seg_type == 'code':
                            st.write("**Code:**")
                            st.code(content, language="python")
                        else:
                            st.markdown(content)
                    
                    final_spoken = []
                    has_code = any(seg_type == 'code' for seg_type, _ in display_segments)
                    for seg_type, content in spoken_segments:
                        final_spoken.append((seg_type, content))
                    if has_code:
                        final_spoken.append(('text', "Try running this code and let me know how it goes!"))
                    
                    for seg_type, content in final_spoken:
                        speak(content, is_question=(seg_type == 'question'))
                    
                    st.session_state.messages.append(AIMessage(ai_message))
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.debug_info += f"Error during query processing: {str(e)}\n"
                with st.chat_message("assistant"):
                    error_message = "I encountered an error while trying to answer your question. Please try again or check the Debug tab for more information."
                    st.markdown(error_message)
                    speak(error_message)
                    st.session_state.messages.append(AIMessage(error_message))

with tab2:
    # Voice Assistant Tab: Voice-Only Interaction
    st.header("Voice Assistant")
    st.markdown("Interact with the assistant using voice to learn about your uploaded documents. Say 'exit' to stop.")
    
    if not st.session_state.voice_active:
        if st.button("🎤 Start Voice Assistant"):
            st.session_state.voice_active = True
            st.session_state.debug_info += "Started voice assistant\n"
            st.rerun()
    else:
        if st.button("🛑 Stop Voice Assistant"):
            st.session_state.voice_active = False
            st.session_state.debug_info += "Stopped voice assistant\n"
            speak("Voice assistant stopped. You can start it again anytime.")
            st.rerun()
        
        with st.spinner("Listening..."):
            user_input = recognize_speech()
            if user_input:
                st.session_state.debug_info += f"Voice command: {user_input}\n"
                command_type = process_voice_command(user_input)
                
                if command_type == "exit":
                    st.session_state.voice_active = False
                    st.session_state.debug_info += "Exiting voice assistant\n"
                    speak("Voice assistant stopped. You can start it again anytime.")
                    st.rerun()
                
                elif command_type == "upload":
                    speak("Please use the file uploader in the Upload Documents tab to select your files, then say 'process files' to confirm.")
                    st.warning("Please upload files using the file uploader in the Upload Documents tab.")
                    st.session_state.voice_messages.append({"role": "user", "content": user_input})
                    st.session_state.voice_messages.append({"role": "assistant", "content": "Directed to Upload Documents tab."})
                
                elif command_type == "clear":
                    speak("Clearing all documents from the database.")
                    try:
                        supabase.table("documents").delete().execute()
                        st.session_state.vector_store = None
                        st.session_state.docs_processed = False
                        st.success("All documents cleared from the database.")
                        st.session_state.debug_info += "Documents cleared from database\n"
                        st.session_state.voice_messages.append({"role": "user", "content": user_input})
                        st.session_state.voice_messages.append({"role": "assistant", "content": "All documents cleared."})
                    except Exception as e:
                        st.error(f"Error clearing documents: {str(e)}")
                        st.session_state.debug_info += f"Error clearing documents: {str(e)}\n"
                        st.session_state.voice_messages.append({"role": "user", "content": user_input})
                        st.session_state.voice_messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
                
                elif command_type == "query" or command_type is None:
                    st.session_state.voice_messages.append({"role": "user", "content": user_input})
                    
                    try:
                        doc_count = supabase.table("documents").select("count", count="exact").execute()
                        count = doc_count.count if hasattr(doc_count, 'count') else 0
                        if count == 0:
                            error_message = "I don't have any documents to search through. Please upload documents in the Upload Documents tab first."
                            speak(error_message)
                            st.warning(error_message)
                            st.session_state.voice_messages.append({"role": "assistant", "content": error_message})
                            st.rerun()
                    except Exception as e:
                        st.session_state.debug_info += f"Error checking count before query: {str(e)}\n"
                    
                    with st.spinner("Processing your question..."):
                        try:
                            chat_history = []
                            for message in st.session_state.voice_messages:
                                if message["role"] == "user":
                                    chat_history.append(("human", message["content"]))
                                elif message["role"] == "assistant":
                                    chat_history.append(("ai", message["content"]))
                            
                            try:
                                result = agent_executor.invoke({
                                    "input": user_input,
                                    "chat_history": chat_history
                                })
                                ai_message = result["output"]
                                st.session_state.debug_info += "Agent generated answer\n"
                            except Exception as agent_error:
                                st.session_state.debug_info += f"Agent error: {str(agent_error)}. Falling back to direct retrieval.\n"
                                result = direct_qa.invoke({"question": user_input})
                                ai_message = result["result"]
                                st.session_state.debug_info += "Direct retrieval generated answer\n"
                            
                            if "I don't have" not in ai_message and count < 3:
                                st.warning("⚠️ Warning: The assistant might be using information outside of your documents. Consider uploading more relevant documents.")
                            
                            display_segments, spoken_segments = process_response_for_speech(ai_message, for_voice_tab=True)
                            
                            # Display chat-like history
                            with st.chat_message("user"):
                                st.markdown(user_input)
                            
                            with st.chat_message("assistant"):
                                if not display_segments:
                                    st.markdown("Explained via voice. See code or key points below if any.")
                                for seg_type, content in display_segments:
                                    if seg_type == 'code':
                                        st.write("**Code:**")
                                        st.code(content, language="python")
                                
                                # Speak the response
                                final_spoken = []
                                has_code = any(seg_type == 'code' for seg_type, _ in display_segments)
                                for seg_type, content in spoken_segments:
                                    final_spoken.append((seg_type, content))
                                if has_code:
                                    final_spoken.append(('text', "I shared some code. Try running it and let me know how it goes!"))
                                final_spoken.append(('question', "Does that make sense? Ready for another question?"))
                                
                                for seg_type, content in final_spoken:
                                    speak(content, is_question=(seg_type == 'question'))
                            
                            st.session_state.voice_messages.append({"role": "assistant", "content": ai_message})
                        
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            st.session_state.debug_info += f"Error during query processing: {str(e)}\n"
                            error_message = "I encountered an error while trying to answer your question. Please try again or check the Debug tab."
                            speak(error_message)
                            st.session_state.voice_messages.append({"role": "assistant", "content": error_message})
        
        # Display voice interaction history
        for message in st.session_state.voice_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if st.session_state.voice_active:
            st.rerun()