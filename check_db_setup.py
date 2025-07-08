import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

# Get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

try:
    # Create supabase client
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Supabase client created successfully!")
    
    # Check if documents table exists at all
    print("\n🔍 Checking if documents table exists...")
    try:
        response = supabase.table("documents").select("*").limit(1).execute()
        print(f"✅ Documents table exists. Data sample: {response.data}")
    except Exception as e:
        print(f"❌ Error accessing documents table: {e}")
        
    # Check if vector extension is enabled
    print("\n🔍 Checking vector extension...")
    try:
        # Try to check extensions
        response = supabase.rpc('sql', {'query': "SELECT * FROM pg_extension WHERE extname = 'vector'"}).execute()
        if response.data:
            print("✅ Vector extension is installed")
        else:
            print("❌ Vector extension is NOT installed")
    except Exception as e:
        print(f"❌ Error checking vector extension: {e}")
        
    # Check if match_documents function exists
    print("\n🔍 Checking match_documents function...")
    try:
        response = supabase.rpc('match_documents', {
            'query_embedding': [0.1] * 768,
            'filter': {}
        }).execute()
        print("✅ match_documents function exists and works")
    except Exception as e:
        print(f"❌ match_documents function error: {e}")

except Exception as e:
    print(f"❌ Failed to create Supabase client: {e}")
    import traceback
    traceback.print_exc()
