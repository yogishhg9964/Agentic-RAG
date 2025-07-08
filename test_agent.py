import os
from dotenv import load_dotenv
from replica.utils.agent_utils import initialize_agent_and_qa
from supabase.client import create_client

# Load environment variables
load_dotenv()

def test_agent_with_hmi_questions():
    """Test the agent with specific HMI questions"""
    print("🤖 Testing AI Agent with HMI questions...")
    
    try:
        # Initialize Supabase
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        # Initialize agent
        print("Initializing agent...")
        agent_executor, direct_qa, debug_log = initialize_agent_and_qa(supabase)
        
        if not agent_executor:
            print("❌ Failed to initialize agent")
            return False
        
        print("✅ Agent initialized successfully!")
        
        # Test questions about your HMI poster
        test_questions = [
            "What is the SoleSafe monitoring system about?",
            "Who is Yogish HG and what is his role?",
            "What are the 5 main objectives of the project?",
            "What hardware components are used?",
            "Who is the mentor for this project?"
        ]
        
        for question in test_questions:
            print(f"\n❓ Question: {question}")
            try:
                # Use the agent to answer
                result = agent_executor.invoke({"input": question})
                answer = result.get("output", "No answer provided")
                print(f"🤖 Answer: {answer[:300]}...")
                print("-" * 50)
            except Exception as e:
                print(f"❌ Error answering question: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in agent test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_agent_with_hmi_questions()
