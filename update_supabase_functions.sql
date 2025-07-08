-- Create a function to check if vector extension is installed
CREATE OR REPLACE FUNCTION check_vector_ext()
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    );
END;
$$ LANGUAGE plpgsql; 