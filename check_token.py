import base64
import json

# Decode the JWT token to see what role it has
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im93cnVkeWd5eWJodWNpcWZ6dnlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1MjU4ODMsImV4cCI6MjA2MjEwMTg4M30.VNB7W48AFO1enlXWiY3NmkAIcPmYWDyzP9tlD9iuDyo"

# Split the token and decode the payload
header, payload, signature = token.split('.')

# Add padding if needed
payload += '=' * (4 - len(payload) % 4)

# Decode the payload
decoded_payload = base64.urlsafe_b64decode(payload)
payload_json = json.loads(decoded_payload)

print("Token details:")
print(json.dumps(payload_json, indent=2))

# Check if it's expired (exp is in Unix timestamp)
import time
current_time = time.time()
exp_time = payload_json.get('exp', 0)

print(f"\nCurrent time: {current_time}")
print(f"Token expires: {exp_time}")
print(f"Token is {'EXPIRED' if current_time > exp_time else 'VALID'}")
print(f"Role: {payload_json.get('role', 'unknown')}")
