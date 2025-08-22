import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.chains import RetrievalQA
import sys
import streamlit as st

# Function to get environment variable or Streamlit secret
def get_env_var(key):
    # First try environment variables
    value = os.environ.get(key)
    if value:
        return value
    
    # Then try Streamlit secrets
    try:
        return st.secrets[key]
    except:
        return None

_agent_executor = None
_direct_qa = None
_vector_store_cache = None

def get_cached_vector_store(supabase_client, embeddings_instance):
    global _vector_store_cache
    if _vector_store_cache is None:
        print("Initializing vector store for agent_utils...")
        _vector_store_cache = SupabaseVectorStore(
            client=supabase_client,
            embedding=embeddings_instance,
            table_name="documents",
            query_name="match_documents"
        )
        print("Vector store initialized and cached in agent_utils.")
    return _vector_store_cache

def initialize_agent_and_qa(supabase_client):
    global _agent_executor, _direct_qa

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=get_env_var("GEMINI_API_KEY"),
        temperature=0.2,
        max_output_tokens=4096,
        top_p=0.95,
    )
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=get_env_var("GEMINI_API_KEY"),
    )

    vector_store = get_cached_vector_store(supabase_client, embeddings)
    if vector_store is None:
        print("Failed to initialize vector store for agent.", file=sys.stderr)
        return None, None, [] # Ensure three values are always returned

    print("Initializing agent and QA chain...")

    AGENT_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """You are an advanced AI research assistant with access to uploaded documents. Your primary goal is to help students understand concepts from their uploaded materials.

        CRITICAL RULE: You MUST ALWAYS call the retrieve_documents tool FIRST before answering ANY question, regardless of the topic.

        HOW TO ANSWER:
        1. ALWAYS start by calling the retrieve_documents tool with the user's question or relevant keywords.
        2. If the retrieve_documents tool returns relevant information from uploaded documents:
            - Base your answer ONLY on the information from these documents.
            - Provide CLEAR, CONCISE, and STUDENT-FRIENDLY explanations.
            - Cite specific quotes or references to the source documents.
            - Start your response with "Based on your uploaded documents..."
        3. If the retrieve_documents tool returns "No relevant documents found" or no useful information:
            - Inform the user that you couldn't find specific information in their documents.
            - Then, proceed to answer using your general knowledge.
            - Clearly state: "I couldn't find specific information about this in your uploaded documents, but I can provide general information..."
        4. NEVER answer questions without first checking the uploaded documents using the retrieve_documents tool.

        ANSWERING STYLE:
        - Explain concepts in a way that is easy for students to understand, using simple language and examples.
        - Break down complex ideas into clear steps or points.
        - For voice interactions, use conversational language with interactive cues like 'Let me explain,' 'Does that make sense?' or 'Want to dive deeper?'
        - Include code snippets in <CODE>...</CODE> tags and explanations in <CODE_EXPLANATION>...</CODE_EXPLANATION> tags when relevant.
        - Organize answers with bullet points or numbered lists for clarity.
        - Ensure explanations are complete but concise.
        - In voice mode, prioritize spoken explanations and minimize text output except for code or key points."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    DIRECT_RETRIEVAL_TEMPLATE = """You are an AI assistant. Based ONLY on the context information from documents provided below, answer the question.

    Context information from documents:
    {context}

    Question: {question}

    If the provided context does not contain the information to answer the question, you MUST state only: "I don't have that information in my documents."
    Do NOT use any external knowledge or make up information.
    If the context is sufficient, provide a clear, concise, and student-friendly explanation based ONLY on the provided context.
    
    Detailed and Comprehensive Answer (based ONLY on context):"""
    
    agent_debug_log = []

    @tool(response_format="content_and_artifact")
    def retrieve_documents(query: str):
        """Retrieves relevant document excerpts from the vector store based on the user's query. 
        This tool should be used to gather information from the uploaded documents to answer user questions.
        The query should be a clear question or topic to search for in the documents.
        Returns a formatted string of the retrieved document sections and a list of the raw document objects.
        """
        log_entry = f"Retrieving documents for query: {query}"
        print(log_entry)
        agent_debug_log.append(log_entry)
        try:
            # First, try to get documents using simple text search since vector search might not be working
            from supabase.client import create_client
            import os
            
            supabase_url = get_env_var("SUPABASE_URL")
            supabase_key = get_env_var("SUPABASE_SERVICE_KEY")
            supabase = create_client(supabase_url, supabase_key)
            
            # Get all documents and filter by content similarity
            response = supabase.table("documents").select("*").execute()
            all_docs = response.data
            
            if not all_docs:
                log_entry = "No documents found in database!"
                print(log_entry)
                agent_debug_log.append(log_entry)
                return "No documents found in the database. Please upload documents first.", []
            
            log_entry = f"Found {len(all_docs)} total documents in database"
            print(log_entry)
            agent_debug_log.append(log_entry)
            
            # Simple keyword matching for now (since vector search is not working)
            query_words = query.lower().split()
            scored_docs = []
            
            for doc in all_docs:
                content = doc["content"].lower()
                score = 0
                for word in query_words:
                    if word in content:
                        score += content.count(word)
                
                if score > 0:
                    scored_docs.append((score, doc))
            
            # Sort by score and take top results
            scored_docs.sort(reverse=True, key=lambda x: x[0])
            retrieved_docs = [doc for score, doc in scored_docs[:7]]  # Take top 7
            
            if not retrieved_docs:
                # If no keyword matches, return all documents
                log_entry = "No keyword matches found, returning all documents"
                print(log_entry)
                agent_debug_log.append(log_entry)
                retrieved_docs = all_docs[:7]  # Return first 7 documents
            
            log_entry = f"Retrieved {len(retrieved_docs)} relevant documents"
            print(log_entry)
            agent_debug_log.append(log_entry)
            
            # Format the results
            sources = {}
            for doc in retrieved_docs:
                source = doc["metadata"].get("source", "Unknown Source")
                if source not in sources:
                    sources[source] = []
                sources[source].append(doc)
            
            formatted_results = []
            for source, docs in sources.items():
                source_text = f"## Source: {source}\n\n"
                for i, doc in enumerate(docs):
                    source_text += f"### Excerpt {i+1}:\n{doc['content']}\n\n"
                formatted_results.append(source_text)
            
            serialized = "\n\n".join(formatted_results)
            
            # Convert to LangChain Document format for compatibility
            from langchain.schema import Document
            langchain_docs = []
            for doc in retrieved_docs:
                langchain_doc = Document(
                    page_content=doc["content"],
                    metadata=doc["metadata"]
                )
                langchain_docs.append(langchain_doc)
            
            return serialized, langchain_docs
            
        except Exception as e:
            error_msg = f"Error retrieving documents: {str(e)}"
            print(error_msg, file=sys.stderr)
            agent_debug_log.append(error_msg)
            import traceback
            traceback.print_exc()
            return error_msg, []
    
    tools = [retrieve_documents]
    
    agent = create_tool_calling_agent(llm, tools, AGENT_PROMPT)
    
    _agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        return_direct_tool_output=False,
    )
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 8})
    _direct_qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={
            "prompt": PromptTemplate.from_template(DIRECT_RETRIEVAL_TEMPLATE),
            "verbose": True
        }
    )
    
    print("Agent and QA chain initialized successfully.")
    return _agent_executor, _direct_qa, agent_debug_log