import os
import time
import socket
from dotenv import load_dotenv
from supabase.client import create_client
import requests

# Load environment variables
load_dotenv()

def test_network_connectivity():
    """Test basic network connectivity"""
    print("🌐 Testing network connectivity...")
    
    # Test DNS resolution
    try:
        socket.gethostbyname("google.com")
        print("✅ DNS resolution working")
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    
    # Test HTTP connectivity
    try:
        response = requests.get("https://httpbin.org/get", timeout=5)
        if response.status_code == 200:
            print("✅ HTTP connectivity working")
        else:
            print(f"⚠️ HTTP connectivity issue: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP connectivity failed: {e}")
        return False
    
    return True

def test_supabase_connectivity():
    """Test Supabase specific connectivity"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    print(f"\n🔍 Testing Supabase connectivity to: {supabase_url}")
    
    # Test if we can resolve Supabase hostname
    try:
        hostname = supabase_url.replace("https://", "").replace("http://", "")
        ip = socket.gethostbyname(hostname)
        print(f"✅ Supabase hostname resolved to: {ip}")
    except socket.gaierror as e:
        print(f"❌ Failed to resolve Supabase hostname: {e}")
        return False
    
    # Test HTTP connection to Supabase
    try:
        response = requests.get(f"{supabase_url}/rest/v1/", timeout=10, headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        })
        print(f"✅ Supabase HTTP connection: {response.status_code}")
    except Exception as e:
        print(f"❌ Supabase HTTP connection failed: {e}")
        return False
    
    return True

def test_supabase_operations():
    """Test actual Supabase operations"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    print(f"\n📊 Testing Supabase operations...")
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created")
        
        # Test document count multiple times to check for intermittent issues
        for i in range(3):
            try:
                print(f"  Attempt {i+1}/3...")
                response = supabase.table("documents").select("count", count="exact").execute()
                count = response.count if hasattr(response, 'count') else 0
                print(f"  ✅ Document count: {count}")
                time.sleep(1)  # Small delay between attempts
            except Exception as e:
                print(f"  ❌ Document count failed: {e}")
                print(f"  Error type: {type(e).__name__}")
                
        return True
        
    except Exception as e:
        print(f"❌ Supabase client creation failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("🔧 Connection Diagnostics\n")
    
    # Run all tests
    network_ok = test_network_connectivity()
    if network_ok:
        supabase_ok = test_supabase_connectivity()
        if supabase_ok:
            test_supabase_operations()
    
    print("\n💡 If you're still seeing intermittent errors, try:")
    print("1. Check your internet connection stability")
    print("2. Disable VPN if you're using one")
    print("3. Check if your firewall is blocking connections")
    print("4. Try using the service_role key instead of anon key")
