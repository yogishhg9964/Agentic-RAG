# import basics
import os
from dotenv import load_dotenv

# import supabase
from supabase.client import create_client

# load environment variables
load_dotenv()  

# get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

# print to check if they're loaded
print(f"Supabase URL length: {len(supabase_url) if supabase_url else 0}")
print(f"Supabase Key: {supabase_key[:5]}..." if supabase_key else "Supabase Key: None")

try:
    # create supabase client
    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client created successfully!")
    
    # Test the vector extension
    print("\nChecking vector extension...")
    response = supabase.rpc('check_vector_ext', {}).execute()
    print(f"Vector extension check: {response.data}")
except Exception as e:
    print(f"Error in rpc: {e}")

try:    
    # Check if documents table exists
    print("\nChecking documents table...")
    response = supabase.table('documents').select("id").limit(1).execute()
    print(f"Documents table exists. Example ID: {response.data[0]['id'] if response.data else 'No documents yet'}")
except Exception as e:
    print(f"Error with documents table: {e}")

print("\nTo run the application with Gemini embeddings, make sure:")
print("1. You have executed the SQL in update_supabase_schema.sql")
print("2. Your .env file has SUPABASE_URL, SUPABASE_SERVICE_KEY, and GEMINI_API_KEY set")
print("3. You have documents in the 'documents' folder") 