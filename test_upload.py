import os
from dotenv import load_dotenv
from replica.utils.document_utils import store_documents_in_supabase
from langchain.schema import Document

# Load environment variables
load_dotenv()

# Create a test document
test_docs = [
    Document(
        page_content="This is a test document about artificial intelligence.",
        metadata={"source": "test.txt", "file_type": "txt", "chunk_index": 0}
    ),
    Document(
        page_content="Machine learning is a subset of artificial intelligence.",
        metadata={"source": "test.txt", "file_type": "txt", "chunk_index": 1}
    )
]

print("🧪 Testing document storage...")

try:
    vector_store = store_documents_in_supabase(test_docs, mode="append")
    print("✅ Document storage test successful!")
    
    # Test retrieval
    print("\n🔍 Testing document retrieval...")
    
    from supabase.client import create_client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    # Check document count
    response = supabase.table("documents").select("count", count="exact").execute()
    count = response.count if hasattr(response, 'count') else 0
    print(f"✅ Total documents in database: {count}")
    
    # Get a sample document
    response = supabase.table("documents").select("*").limit(1).execute()
    if response.data:
        print(f"✅ Sample document: {response.data[0]}")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
