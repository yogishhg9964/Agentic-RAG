# Agentic RAG with LangChain

This project implements an agentic Retrieval-Augmented Generation (RAG) system using LangChain. It integrates with Supabase for database and vector storage, and provides various utilities for document ingestion, querying, and voice assistance.

## Project Structure

- `agentic_rag.py`: Core agentic RAG implementation.
- `agentic_rag_streamlit.py`: Streamlit interface for the agentic RAG.
- `replica/`: Contains a replica of a web app with backend and frontend.
- `setup_database.py`: Script to setup the database schema and functions.
- `update_supabase_schema.sql` and `update_supabase_functions.sql`: SQL scripts for Supabase schema and functions.
- `ingest_in_db.py`: Script to ingest documents into the database.
- `check_*.py` and `diagnose_*.py`: Various scripts for checking and diagnosing database and documents.
- `test_*.py`: Test scripts for different components.

## Requirements

- Python 3.10 or higher
- Required Python packages listed in `requirements.txt`.

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Setup Supabase database:
   - Run `setup_database.py` to initialize the schema and functions.
   - Alternatively, apply SQL scripts `update_supabase_schema.sql` and `update_supabase_functions.sql` in your Supabase SQL editor.
5. Configure environment variables or configuration files as needed for database connection.

## Usage

- To ingest documents into the database, run:
  ```
  python ingest_in_db.py
  ```
- To run the agentic RAG system:
  ```
  python agentic_rag.py
  ```
- To use the Streamlit interface:
  ```
  streamlit run agentic_rag_streamlit.py
  ```

## Testing

Run test scripts to verify functionality:
```bash
python -m unittest test_agent.py
python -m unittest test_retrieval.py
# and others
```

## Notes

- The `replica` folder contains a web app replica with backend and frontend components.
- Refer to `gemini_setup_instructions.md` for additional setup instructions if applicable.

## License

This project is licensed under the terms specified in the LICENSE file.
