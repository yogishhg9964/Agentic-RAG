import os
import sys
sys.path.append('replica')

from dotenv import load_dotenv
from supabase.client import create_client
from replica.utils.agent_utils import initialize_agent_and_qa

# Load environment variables
load_dotenv()

print("🧪 Testing the fixed document retrieval...")

try:
    # Get supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    # Initialize the agent
    print("Initializing agent...")
    agent_executor, direct_qa, debug_log = initialize_agent_and_qa(supabase)
    
    if agent_executor:
        print("✅ Agent initialized successfully!")
        
        # Test queries about the HMI poster
        test_queries = [
            "What is SoleSafe monitoring system?",
            "Who is Yogish HG?",
            "What are the objectives of the HMI project?",
            "What technologies are used in the project?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            try:
                # Include chat_history parameter
                result = agent_executor.invoke({
                    "input": query,
                    "chat_history": []  # Empty chat history for testing
                })
                print(f"✅ Response: {result.get('output', 'No output')[:200]}...")
                break  # Test just one query for now
            except Exception as e:
                print(f"❌ Query failed: {e}")
    else:
        print("❌ Failed to initialize agent")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
