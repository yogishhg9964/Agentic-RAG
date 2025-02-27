<h1>Agentic RAG (Retrieval Augmented Generation) with LangChain and Supabase</h1>

<h2>Watch the full tutorial on my YouTube Channel</h2>
<div>
    &nbsp;<br>
<a href="https://www.youtube.com/watch?v=A3WKdt_MNZQ">
    <img src="thumbnail.png" alt="Thomas Janssen Youtube" width="200"/>
</a>
    &nbsp;<br>
     &nbsp;<br>
</div>

<h2>Prerequisites</h2>
<ul>
  <li>Python 3.11+</li>
</ul>

<h2>Installation</h2>
1. Clone the repository:

```
git clone https://github.com/ThomasJanssen-tech/Agentic-RAG-with-LangChain.git
cd Agentic RAG with LangChain
```

2. Create a virtual environment

```
python -m venv venv
```

3. Activate the virtual environment

```
venv\Scripts\Activate
(or on Mac): source venv/bin/activate
```

4. Install libraries

```
pip install -r requirements.txt
```

5. Create accounts

- Create a free account on Supabase: https://supabase.com/
- Create an API key for OpenAI: https://platform.openai.com/api-keys

6. Execute SQL queries in Supabase

- Execute the following SQL query in Supabase:

```
-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store your documents
create table
  documents (
    id uuid primary key,
    content text, -- corresponds to Document.pageContent
    metadata jsonb, -- corresponds to Document.metadata
    embedding vector (1536) -- 1536 works for OpenAI embeddings, change if needed
  );

-- Create a function to search for documents
create function match_documents (
  query_embedding vector (1536),
  filter jsonb default '{}'
) returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
) language plpgsql as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding;
end;
$$;
```

7. Add API keys to .env file

- Rename .env.example to .env
- Add the API keys for Pinecone and OpenAI to the .env file

<h3>Executing the scripts</h3>

1. Open a terminal in VS Code

2. Execute the following command:

```
python ingest_in_db.py
python agentic_rag.py
streamlit run agentic_rag_streamlit.py
```
