import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase.client import create_client

# Load environment variables
load_dotenv()

def test_document_retrieval():
    """Test if we can search and retrieve HMI document content"""
    print("🔍 Testing document retrieval for HMI content...")
    
    try:
        # Initialize components
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Test queries about your HMI poster
        test_queries = [
            "What is SoleSafe monitoring system?",
            "Who is the student author of this project?",
            "What are the main objectives?",
            "What technologies are used?",
            "What is the problem statement?"
        ]
        
        for query in test_queries:
            print(f"\n📋 Query: {query}")
            
            # Generate embedding for the query
            query_embedding = embeddings.embed_query(query)
            
            # Get all documents and find relevant ones manually
            # (since we don't have the match_documents function)
            response = supabase.table("documents").select("*").eq("metadata->>source", "HMI Poster.pdf").execute()
            
            if response.data:
                print(f"✅ Found {len(response.data)} relevant document chunks")
                
                # Show most relevant content (simple approach)
                best_match = None
                best_score = -1
                
                for doc in response.data:
                    content_lower = doc["content"].lower()
                    query_lower = query.lower()
                    
                    # Simple keyword matching
                    score = 0
                    for word in query_lower.split():
                        if word in content_lower:
                            score += 1
                    
                    if score > best_score:
                        best_score = score
                        best_match = doc
                
                if best_match:
                    preview = best_match["content"][:200] + "..." if len(best_match["content"]) > 200 else best_match["content"]
                    print(f"   Most relevant content: {preview}")
                else:
                    print("   No specific match found")
            else:
                print("❌ No documents found")
        
        print("\n✅ Document retrieval test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in document retrieval test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_document_retrieval()
