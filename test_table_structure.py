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
    
    # Let's try different approaches to understand the table structure
    
    print("\n🔍 Attempting to describe table structure...")
    
    # Try to insert without ID to see what the table expects
    print("\n🧪 Testing insert without ID...")
    try:
        response = supabase.table("documents").insert({
            "content": "test content",
            "metadata": {},
        }).execute()
        print(f"✅ Insert without ID successful: {response.data}")
        
        # Get the inserted record to see its structure
        if response.data:
            record = response.data[0]
            print(f"Record structure: {record}")
            
            # Clean up
            if 'id' in record:
                supabase.table("documents").delete().eq("id", record['id']).execute()
                print("✅ Cleanup successful")
        
    except Exception as e:
        print(f"❌ Insert without ID failed: {e}")
        
    # Try to get table metadata through information schema
    print("\n🔍 Trying to access table info through API...")
    try:
        # Try to get an empty result set to see column structure
        response = supabase.table("documents").select("*").eq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Query structure test: {response}")
    except Exception as e:
        print(f"Query test result: {e}")

except Exception as e:
    print(f"❌ Failed to create Supabase client: {e}")
    import traceback
    traceback.print_exc()
