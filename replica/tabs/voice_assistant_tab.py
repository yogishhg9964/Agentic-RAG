import streamlit as st
from utils.voice_utils import recognize_speech, speak, process_response_for_speech, process_voice_command
from utils.agent_utils import initialize_agent_and_qa
from utils.document_utils import get_vector_store

def voice_assistant_tab(supabase):
    st.header("Voice Assistant")
    st.markdown("Interact with the assistant using voice to learn about your uploaded documents. Say 'exit' to stop.")
    
    # Initialize vector store and agent
    vector_store = get_vector_store()
    agent_executor, direct_qa, _ = initialize_agent_and_qa(supabase)
    
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
                            
                            with st.chat_message("user"):
                                st.markdown(user_input)
                            
                            with st.chat_message("assistant"):
                                if not display_segments:
                                    st.markdown("Explained via voice. See code or key points below if any.")
                                for seg_type, content in display_segments:
                                    if seg_type == 'code':
                                        st.write("**Code:**")
                                        st.code(content, language="python")
                                
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
        
        for message in st.session_state.voice_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if st.session_state.voice_active:
            st.rerun()