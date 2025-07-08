import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

# Get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

print("📊 Checking current documents in database...")

try:
    # Get all documents
    response = supabase.table("documents").select("*").execute()
    total_docs = len(response.data)
    print(f"Total documents in database: {total_docs}")
    
    if total_docs > 0:
        print("\nDocument sources:")
        sources = {}
        for doc in response.data:
            source = doc["metadata"].get("source", "unknown")
            if source in sources:
                sources[source] += 1
            else:
                sources[source] = 1
        
        for source, count in sources.items():
            print(f"  - {source}: {count} chunks")
            
        print("\nSample content from recent documents:")
        for i, doc in enumerate(response.data[-3:]):  # Show last 3 documents
            content_preview = doc["content"][:150] + "..." if len(doc["content"]) > 150 else doc["content"]
            source = doc["metadata"].get("source", "unknown")
            print(f"{i+1}. Source: {source}")
            print(f"   Content: {content_preview}")
            print()
    else:
        print("❌ No documents found in database")
        print("Please upload your HMI document through the 'Upload Documents' tab")

except Exception as e:
    print(f"❌ Error checking database: {e}")
