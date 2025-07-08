import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

# Get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

def setup_database():
    try:
        # Create supabase client
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully!")
        
        print("\n🗑️ Dropping existing table and functions...")
        try:
            # Try to drop the existing table
            supabase.rpc('sql', {'query': 'DROP FUNCTION IF EXISTS match_documents CASCADE'}).execute()
            print("✅ Dropped match_documents function")
        except Exception as e:
            print(f"⚠️ Could not drop function (might not exist): {e}")
            
        try:
            supabase.rpc('sql', {'query': 'DROP TABLE IF EXISTS documents CASCADE'}).execute()
            print("✅ Dropped documents table")
        except Exception as e:
            print(f"⚠️ Could not drop table (might not exist): {e}")
        
        print("\n🏗️ Creating new table with correct schema...")
        
        # Create the documents table with UUID primary key
        create_table_sql = """
        CREATE TABLE documents (
          id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
          content text, 
          metadata jsonb, 
          embedding vector(768)
        );
        """
        
        try:
            supabase.rpc('sql', {'query': create_table_sql}).execute()
            print("✅ Created documents table with UUID primary key")
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            return False
        
        print("\n🔧 Creating match_documents function...")
        
        # Create the match_documents function
        create_function_sql = """
        CREATE OR REPLACE FUNCTION match_documents (
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
            documents.id,
            documents.content,
            documents.metadata,
            1 - (documents.embedding <=> query_embedding) AS similarity
          FROM documents
          WHERE documents.metadata @> filter
          ORDER BY documents.embedding <=> query_embedding;
        END;
        $$;
        """
        
        try:
            supabase.rpc('sql', {'query': create_function_sql}).execute()
            print("✅ Created match_documents function")
        except Exception as e:
            print(f"❌ Error creating function: {e}")
            return False
        
        print("\n🧪 Testing the setup...")
        
        # Test inserting a document
        import uuid
        test_id = str(uuid.uuid4())
        try:
            response = supabase.table("documents").insert({
                "id": test_id,
                "content": "test content",
                "metadata": {"test": True},
                "embedding": [0.1] * 768
            }).execute()
            print(f"✅ Test insert successful")
            
            # Test the match function
            response = supabase.rpc('match_documents', {
                'query_embedding': [0.1] * 768,
                'filter': {}
            }).execute()
            print(f"✅ match_documents function works: found {len(response.data)} documents")
            
            # Clean up
            supabase.table("documents").delete().eq("id", test_id).execute()
            print("✅ Test cleanup successful")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Supabase database schema...")
    
    success = setup_database()
    
    if success:
        print("\n✅ Database setup completed successfully!")
        print("You can now upload documents to your knowledge base.")
    else:
        print("\n❌ Database setup failed!")
        print("Please check your Supabase configuration and permissions.")
        print("You may need to run the SQL commands manually in the Supabase dashboard.")
