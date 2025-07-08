-- Drop existing function first
DROP FUNCTION IF EXISTS match_documents;

-- Drop existing table (WARNING: This will delete all your existing documents)
DROP TABLE IF EXISTS documents;

-- Recreate table with 768 dimensions for Gemini
CREATE TABLE documents (
  id uuid primary key,
  content text, -- corresponds to Document.pageContent
  metadata jsonb, -- corresponds to Document.metadata
  embedding vector(768) -- 768 dimensions for Google's embedding-001 model
);

-- Recreate the function with 768 dimensions
CREATE FUNCTION match_documents (
  query_embedding vector(768),
  filter jsonb default '{}'
) RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
) LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE metadata @> filter
  ORDER BY documents.embedding <=> query_embedding;
END;
$$; 