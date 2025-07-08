import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

# Get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

print("🧹 Cleaning up test records...")

try:
    # Delete test records
    response = supabase.table("documents").delete().eq("metadata->source", "test.txt").execute()
    print(f"✅ Cleaned up test records")
    
    # Check final count
    response = supabase.table("documents").select("count", count="exact").execute()
    count = response.count if hasattr(response, 'count') else 0
    print(f"📊 Final document count: {count}")
    
except Exception as e:
    print(f"❌ Cleanup failed: {e}")
