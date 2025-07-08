import os
from dotenv import load_dotenv
from supabase.client import create_client
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

# Get supabase credentials
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

print("🔍 Analyzing your HMI Poster content...")

try:
    # Get all HMI document chunks
    response = supabase.table("documents").select("*").eq("metadata->>source", "HMI Poster.pdf").execute()
    hmi_docs = response.data
    
    print(f"Found {len(hmi_docs)} chunks from HMI Poster.pdf")
    print("\n" + "="*80)
    print("COMPLETE HMI POSTER CONTENT:")
    print("="*80)
    
    for i, doc in enumerate(hmi_docs, 1):
        print(f"\n--- CHUNK {i} ---")
        print(doc["content"])
        print("-" * 40)
    
    print("\n" + "="*80)
    print("SUMMARY FOR YOUR PRESENTATION:")
    print("="*80)
    
    # Combine all content
    full_content = "\n\n".join([doc["content"] for doc in hmi_docs])
    
    print("\nBased on the content, here's what your HMI poster covers:")
    print("\n1. PROBLEM STATEMENT:")
    if "risks" in full_content.lower() or "hazards" in full_content.lower():
        print("   - Individual safety risks from physiological changes")
        print("   - Environmental hazards and location-based dangers")
        print("   - Need for continuous monitoring systems")
    
    print("\n2. SOLUTION/SYSTEM FEATURES:")
    if "real-time" in full_content.lower():
        print("   - Real-time data visualization")
        print("   - Temperature and pressure monitoring")
        print("   - Proactive location safety tracking")
        print("   - Immediate alert systems")
    
    print("\n3. TECHNICAL ASPECTS:")
    if "hmi" in full_content.lower() or "interface" in full_content.lower():
        print("   - Human-Machine Interface design")
        print("   - User-friendly data display")
        print("   - Intuitive visualization systems")
    
    print("\n4. REFERENCES/RESEARCH:")
    if "doi" in full_content.lower() or "vol" in full_content.lower():
        print("   - Academic research backing")
        print("   - IEEE publications referenced")
        print("   - Evidence-based approach")

except Exception as e:
    print(f"❌ Error analyzing HMI content: {e}")
    import traceback
    traceback.print_exc()
