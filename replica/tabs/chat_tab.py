import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from utils.agent_utils import initialize_agent_and_qa
from utils.document_utils import get_vector_store

def chat_tab(supabase):
    # Initialize vector store and agent
    vector_store = get_vector_store()
    agent_executor, direct_qa, _ = initialize_agent_and_qa(supabase)
    
    # Document count info
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
                    st.session_state.messages.append(AIMessage(error_message))
                st.stop()
        except Exception as e:
            st.session_state.debug_info += f"Error checking count before query: {str(e)}\n"
        
        process_query(user_question, agent_executor, direct_qa, supabase, count)

def process_query(user_input, agent_executor, direct_qa, supabase, count):
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
                st.session_state.messages.append(AIMessage(ai_message))
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.debug_info += f"Error during query processing: {str(e)}\n"
            with st.chat_message("assistant"):
                error_message = "I encountered an error while trying to answer your question. Please try again or check the Debug tab for more information."
                st.markdown(error_message)
                st.session_state.messages.append(AIMessage(error_message))
