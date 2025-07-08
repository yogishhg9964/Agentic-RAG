import os
from flask import Flask, request, jsonify, send_from_directory # Added send_from_directory
from flask_cors import CORS # Added CORS
from dotenv import load_dotenv
from supabase.client import create_client, Client
import tempfile
import traceback
import sys

# Adjust import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
utils_path = os.path.join(parent_dir, 'utils')
if utils_path not in sys.path:
    sys.path.append(utils_path)
if parent_dir not in sys.path: # Ensure parent_dir is also in path for .env loading if needed by utils
    sys.path.append(parent_dir)


from agent_utils import initialize_agent_and_qa
from document_utils import process_files_from_paths, store_documents_in_supabase

# Load environment variables from .env in the parent directory
dotenv_path = os.path.join(parent_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__, static_folder=os.path.join(parent_dir, 'frontend', 'build'))
CORS(app) # Enable CORS for all routes

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client | None = None
if not supabase_url or not supabase_key:
    app.logger.error("Supabase URL or Key not found in .env file. Please check.")
else:
    try:
        supabase = create_client(supabase_url, supabase_key)
        app.logger.info("Supabase client initialized successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Supabase client: {e}\n{traceback.format_exc()}")

# Initialize Agent and QA chain
agent_executor = None
direct_qa = None
# agent_debug_log_global = [] # This might be better handled by actual logging

if supabase:
    try:
        # initialize_agent_and_qa now returns (agent_executor, direct_qa, agent_debug_log)
        # We might not need to store the initial debug log globally here if tools log directly
        agent_executor, direct_qa, _ = initialize_agent_and_qa(supabase)
        if agent_executor and direct_qa:
            app.logger.info("Agent and QA chain initialized successfully.")
        else:
            app.logger.error("Failed to initialize agent or QA chain. Check previous logs from agent_utils.")
    except Exception as e:
        app.logger.error(f"Error during agent and QA initialization: {e}\n{traceback.format_exc()}")
else:
    app.logger.warning("Supabase client not available. Agent and QA chain will not be initialized.")

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat_handler():
    data = request.json
    user_input = data.get('user_input')
    # Expecting chat_history as: [{'role': 'user'/'assistant', 'content': '...'}, ...]
    chat_history_frontend = data.get('chat_history', [])

    if not user_input:
        return jsonify({'error': 'No user_input provided'}), 400
    
    if not agent_executor or not direct_qa:
        app.logger.error("Chat attempt when agent/QA not initialized.")
        return jsonify({'error': 'Agent or QA chain not initialized. Please check backend server logs.'}), 500

    # Convert frontend chat history to Langchain's expected format (list of tuples)
    # HumanMessage and AIMessage objects might be better if your agent expects them directly
    # For create_tool_calling_agent, a list of (type, content) tuples is common for "chat_history"
    chat_history_langchain = []
    for msg in chat_history_frontend:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'user':
            chat_history_langchain.append(("human", content))
        elif role == 'assistant':
            chat_history_langchain.append(("ai", content))
        # else: # ignore other roles or handle as needed

    ai_message = "An unexpected error occurred."
    # debug_log_for_request = [] # For request-specific debug info if needed beyond server logs

    try:
        app.logger.info(f"Invoking agent with input: '{user_input}' and history: {chat_history_langchain}")
        # debug_log_for_request.append(f"Invoking agent with input: {user_input}")
        
        # The agent_utils.retrieve_documents tool now uses print() for logging, which will go to server logs.
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history_langchain
        })
        ai_message = result.get("output", "Error: No output from agent.")
        # debug_log_for_request.append(f"Agent raw output: {ai_message}")
        app.logger.info(f"Agent generated answer: {ai_message}")

    except Exception as agent_error:
        app.logger.error(f"Agent error: {str(agent_error)}. Falling back to direct retrieval.\n{traceback.format_exc()}")
        # debug_log_for_request.append(f"Agent error: {str(agent_error)}. Falling back to direct retrieval.")
        try:
            app.logger.info(f"Invoking direct QA with question: {user_input}")
            # debug_log_for_request.append(f"Invoking direct QA with question: {user_input}")
            result = direct_qa.invoke({"question": user_input}) # Ensure direct_qa expects this format
            ai_message = result.get("result", "Error: No result from direct QA.")
            # debug_log_for_request.append(f"Direct QA raw output: {ai_message}")
            app.logger.info(f"Direct retrieval generated answer: {ai_message}")
        except Exception as qa_error:
            app.logger.error(f"Direct QA error: {str(qa_error)}\n{traceback.format_exc()}")
            # debug_log_for_request.append(f"Direct QA error: {str(qa_error)}")
            ai_message = "I encountered an error with both the agent and direct retrieval. Please try again or check server logs."
    
    return jsonify({'ai_message': ai_message}) # Removed debug_log from response, rely on server logs

@app.route('/api/documents/count', methods=['GET'])
def get_document_count():
    if not supabase:
        return jsonify({"error": "Supabase client not initialized."}), 500
    try:
        # Ensure the table name is correct, e.g., "documents"
        doc_count_response = supabase.table("documents").select("count", count="exact").execute()
        count = doc_count_response.count if hasattr(doc_count_response, 'count') and doc_count_response.count is not None else 0
        
        if count == 0:
            message = "No documents found in the knowledge base."
        else:
            message = f"{count} document chunks in the knowledge base."
        return jsonify({'count': count, 'message': message})
    except Exception as e:
        app.logger.error(f"Error checking document count: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Could not check document count.', 'details': str(e)}), 500

@app.route('/api/documents/upload', methods=['POST'])
def upload_documents_handler():
    global agent_executor, direct_qa # To allow re-initialization
    if not supabase:
        return jsonify({"error": "Supabase client not initialized. Cannot upload documents."}), 500

    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400
    
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        return jsonify({"error": "No selected files"}), 400

    processed_file_paths = []
    # Create a temporary directory that will be automatically cleaned up
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            for file_storage in uploaded_files:
                # Sanitize filename to prevent directory traversal or other issues
                filename = os.path.basename(file_storage.filename) 
                if not filename: continue # Skip if filename is empty after sanitization

                file_path = os.path.join(temp_dir, filename)
                file_storage.save(file_path)
                processed_file_paths.append(file_path)
                app.logger.info(f"File {filename} saved to temporary path: {file_path}")

            if not processed_file_paths:
                return jsonify({"error": "No files were successfully saved for processing."}), 400

            app.logger.info(f"Processing files: {processed_file_paths}")
            document_chunks, file_details = process_files_from_paths(processed_file_paths) # This function is from your utils

            if document_chunks:
                app.logger.info(f"Storing {len(document_chunks)} chunks in Supabase.")
                # The mode can be "append" or "replace"
                store_documents_in_supabase(document_chunks, mode="append") # This function is from your utils
                
                # Re-initialize agent after new documents are added.
                app.logger.info("Re-initializing agent and QA chain after document upload...")
                agent_executor, direct_qa, _ = initialize_agent_and_qa(supabase)
                if agent_executor and direct_qa:
                    app.logger.info("Agent and QA chain re-initialized successfully.")
                else:
                    app.logger.error("Failed to re-initialize agent or QA chain after upload.")

                return jsonify({
                    "message": f"Successfully processed and stored {len(document_chunks)} chunks from {len(file_details)} files.", 
                    "details": file_details
                }), 200
            else:
                app.logger.warning("No document chunks to store after processing uploaded files.")
                return jsonify({"message": "No document chunks were generated from the uploaded files."}), 200

        except Exception as e:
            app.logger.error(f"Error during document upload: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"error": f"An error occurred during document upload: {str(e)}"}), 500
        # temp_dir and its contents are automatically removed here

@app.route('/api/documents/clear', methods=['POST'])
def clear_documents_handler():
    global agent_executor, direct_qa # To allow re-initialization
    if not supabase:
        return jsonify({"error": "Supabase client not initialized. Cannot clear documents."}), 500
    try:
        # Ensure the table name is correct, e.g., "documents"
        # Delete all rows from the "documents" table.
        # Use a nil UUID for the .neq filter, as the 'id' column is likely of UUID type.
        # This effectively matches all rows if no row has this nil UUID as its id.
        nil_uuid = "00000000-0000-0000-0000-000000000000"
        response = supabase.table("documents").delete().neq("id", nil_uuid).execute()
        
        app.logger.info(f"Documents cleared from Supabase. Response: {response.data if hasattr(response, 'data') else 'No data in response'}")
        
        # Re-initialize agent as its knowledge base is now empty/changed
        app.logger.info("Re-initializing agent and QA chain after clearing documents...")
        agent_executor, direct_qa, _ = initialize_agent_and_qa(supabase)
        if agent_executor and direct_qa:
            app.logger.info("Agent and QA chain re-initialized successfully.")
        else:
            app.logger.error("Failed to re-initialize agent or QA chain after clearing documents.")

        return jsonify({"message": "All documents cleared successfully."}), 200
    except Exception as e:
        app.logger.error(f"Error clearing documents: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Failed to clear documents: {str(e)}"}), 500

if __name__ == '__main__':
    # For production, use a Gunicorn or other WSGI server.
    # The host '0.0.0.0' makes it accessible externally, ensure firewall rules are set if needed.
    app.run(debug=True, port=os.environ.get("PORT", 5001), host='0.0.0.0')
