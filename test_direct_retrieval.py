import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

print("🔧 Testing direct document retrieval...")

try:
    # Get supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    # Test the same logic that's in the retrieve_documents function
    query = "SoleSafe monitoring system"
    print(f"Testing query: '{query}'")
    
    # Get all documents
    response = supabase.table("documents").select("*").execute()
    all_docs = response.data
    
    print(f"Found {len(all_docs)} total documents in database")
    
    if all_docs:
        # Simple keyword matching
        query_words = query.lower().split()
        scored_docs = []
        
        for doc in all_docs:
            content = doc["content"].lower()
            score = 0
            for word in query_words:
                if word in content:
                    score += content.count(word)
            
            if score > 0:
                scored_docs.append((score, doc))
                print(f"Document scored {score}: {doc['content'][:100]}...")
        
        # Sort by score and take top results
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        retrieved_docs = [doc for score, doc in scored_docs[:3]]
        
        if not retrieved_docs:
            print("No keyword matches found, returning all documents")
            retrieved_docs = all_docs[:3]
        
        print(f"\nRetrieved {len(retrieved_docs)} relevant documents:")
        for i, doc in enumerate(retrieved_docs):
            source = doc["metadata"].get("source", "Unknown")
            print(f"{i+1}. Source: {source}")
            print(f"   Content: {doc['content'][:200]}...")
            print()

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
