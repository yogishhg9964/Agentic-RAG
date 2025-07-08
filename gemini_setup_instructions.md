# Setting Up Agentic RAG with Gemini

## Database Setup

1. Go to your Supabase project dashboard.
2. Navigate to the SQL Editor.
3. Copy the contents of the `update_supabase_schema.sql` file (or open the file and run its contents).
4. Execute the SQL. This will:
   - Drop the existing `match_documents` function
   - Drop the existing `documents` table (WARNING: this will delete any existing documents)
   - Create a new `documents` table with 768 dimensions (for Gemini embeddings)
   - Create a new `match_documents` function that works with 768 dimensions

## Environment Setup

1. Create a `.env` file in the root of your project with the following content:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
GEMINI_API_KEY=your_gemini_api_key
```

2. Replace the placeholder values with your actual API keys:
   - `your_supabase_url`: The URL of your Supabase project (found in Supabase project settings)
   - `your_supabase_service_key`: The service role API key from Supabase (found in Supabase project settings)
   - `your_gemini_api_key`: Your Google Gemini API key (get one at https://aistudio.google.com/app/apikey)

## Ingesting Documents

After setting up your database and environment, run:
```
python ingest_in_db.py
```

This will:
1. Load any PDF documents from the `documents` folder
2. Split them into chunks
3. Generate Gemini embeddings for each chunk
4. Store the chunks and embeddings in Supabase

## Running the Application

After ingesting documents, you can run either:
```
python agentic_rag.py
```

Or for the Streamlit interface:
```
streamlit run agentic_rag_streamlit.py
``` 