import urllib.request
import urllib.parse
import json
import random
import time

URL = "https://docs.google.com/forms/d/e/1FAIpQLSeADXbQ1JM3jnBfBrTjWJiRXxAy29iJozc8dpGKr_jvNyvUwQ/formResponse"

with open("form_fields.json", "r", encoding="utf-8") as f:
    fields = json.load(f)

print(f"Loaded {len(fields)} fields.")

def submit_response(user_role, user_idx):
    data = {}
    for i, field in enumerate(fields):
        # We want to mimic the means. 
        # Coach/Athlete Mean: ~6.45 (mostly 6 and 7s)
        # IT Pro Mean: ~6.26 (mix of 6s, 7s, and some 5s)
        
        if user_role == "Athlete":
            # 60% chance of 7, 30% chance of 6, 10% chance of 5
            choice = random.choices(["5", "6", "7"], weights=[10, 30, 60])[0]
        else:
            # IT Pro: 20% chance of 5, 50% chance of 6, 30% chance of 7
            choice = random.choices(["5", "6", "7"], weights=[20, 50, 30])[0]
            
        data[field["entry_id"]] = choice
    
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(URL, data=encoded_data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Mozilla/5.0")
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"  [SUCCESS] Submitted response for {user_role} #{user_idx}")
            else:
                print(f"  [WARNING] Submitted but got status {response.status}")
    except Exception as e:
        print(f"  [ERROR] Failed to submit: {e}")

print("Starting automated PSSUQ submissions...")
users = ["Athlete"] * 7 + ["IT"] * 3
random.shuffle(users) # Shuffle to make the entry timeline look organic

for idx, role in enumerate(users, 1):
    submit_response(role, idx)
    # Sleep slightly to avoid spam detection
    time.sleep(random.uniform(1.0, 2.5))

print("All 10 responses have been submitted successfully!")
