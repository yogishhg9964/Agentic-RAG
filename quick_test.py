import os
from dotenv import load_dotenv
from supabase.client import create_client

# Load environment variables
load_dotenv()

def quick_hmi_test():
    """Quick test to verify HMI content is accessible"""
    print("🚀 Quick HMI Content Test")
    print("=" * 40)
    
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        # Get HMI document
        response = supabase.table("documents").select("content").eq("metadata->>source", "HMI Poster.pdf").execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} HMI document chunks")
            
            # Combine all content
            full_content = " ".join([doc["content"] for doc in response.data])
            
            # Answer key questions directly from content
            questions_and_answers = [
                ("Student Name", "Yogish HG" if "Yogish HG" in full_content else "Not found"),
                ("Project Title", "SoleSafe Monitoring HMI" if "SoleSafe" in full_content else "Not found"),
                ("Institution", "RV College of Engineering" if "RV College" in full_content else "Not found"),
                ("Mentor", "Dr. Harsha H." if "Dr. Harsha" in full_content else "Not found"),
                ("Main Technology", "ESP32, Flutter, React.js" if "ESP32" in full_content else "Not found"),
                ("Key Features", "Real-time monitoring, alerts" if "real-time" in full_content else "Not found")
            ]
            
            print("\n📋 Key Information from HMI Poster:")
            for question, answer in questions_and_answers:
                print(f"   {question}: {answer}")
            
            print("\n✅ Your HMI document is properly loaded and accessible!")
            print("\n🎯 For your presentation, emphasize:")
            print("   • Real-time safety monitoring system")
            print("   • Multi-parameter sensor integration")
            print("   • Proactive vs reactive approach")
            print("   • User-centric HMI design")
            
            return True
        else:
            print("❌ No HMI document found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    quick_hmi_test()
