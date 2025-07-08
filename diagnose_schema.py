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
    
    # Check documents table structure in detail
    print("\n🔍 Checking documents table structure...")
    try:
        # Check column definitions
        response = supabase.rpc('sql', {'query': """
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default,
                character_maximum_length,
                udt_name
            FROM information_schema.columns 
            WHERE table_name = 'documents' 
            ORDER BY ordinal_position
        """}).execute()
        
        if response.data:
            print("Documents table columns:")
            for col in response.data:
                print(f"  - {col['column_name']}: {col['data_type']} ({col['udt_name']}) - nullable: {col['is_nullable']} - default: {col['column_default']}")
        else:
            print("❌ Documents table not found or no columns returned")
            
        # Check table constraints
        print("\n🔍 Checking table constraints...")
        response = supabase.rpc('sql', {'query': """
            SELECT 
                constraint_name,
                constraint_type,
                column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'documents'
        """}).execute()
        
        if response.data:
            print("Table constraints:")
            for constraint in response.data:
                print(f"  - {constraint['constraint_name']}: {constraint['constraint_type']} on {constraint['column_name']}")
        
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        
    # Try to run a simple insert to see what fails
    print("\n🧪 Testing simple insert...")
    try:
        import uuid
        test_id = str(uuid.uuid4())
        response = supabase.table("documents").insert({
            "id": test_id,
            "content": "test content",
            "metadata": {},
            "embedding": [0.1] * 768  # 768 dimensions
        }).execute()
        print(f"✅ Test insert successful with ID: {test_id}")
        
        # Clean up test record
        supabase.table("documents").delete().eq("id", test_id).execute()
        print("✅ Test record cleaned up")
        
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        print(f"Error type: {type(e).__name__}")

except Exception as e:
    print(f"❌ Failed to create Supabase client: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
