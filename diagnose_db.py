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
    
    # Check if vector extension is installed manually
    print("\n🔍 Checking vector extension...")
    try:
        response = supabase.rpc('sql', {'query': "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') as has_vector"}).execute()
        print(f"Vector extension response: {response.data}")
    except Exception as e:
        print(f"❌ Error checking vector extension: {e}")
    
    # Check documents table structure
    print("\n🔍 Checking documents table structure...")
    try:
        response = supabase.rpc('sql', {'query': """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'documents' 
            ORDER BY ordinal_position
        """}).execute()
        if response.data:
            print("Documents table columns:")
            for col in response.data:
                print(f"  - {col['column_name']}: {col['data_type']}")
        else:
            print("❌ Documents table not found or no columns returned")
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
    
    # Check if match_documents function exists
    print("\n🔍 Checking match_documents function...")
    try:
        response = supabase.rpc('sql', {'query': """
            SELECT routine_name, routine_type 
            FROM information_schema.routines 
            WHERE routine_name = 'match_documents'
        """}).execute()
        if response.data:
            print(f"✅ match_documents function exists: {response.data}")
        else:
            print("❌ match_documents function not found")
    except Exception as e:
        print(f"❌ Error checking function: {e}")
    
    # Check document count
    print("\n🔍 Checking document count...")
    try:
        response = supabase.table("documents").select("count", count="exact").execute()
        count = response.count if hasattr(response, 'count') else 0
        print(f"Document count: {count}")
    except Exception as e:
        print(f"❌ Error checking document count: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")

except Exception as e:
    print(f"❌ Failed to create Supabase client: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
