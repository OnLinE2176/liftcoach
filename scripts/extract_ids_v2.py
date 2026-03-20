import urllib.request
import re
import json

url = 'https://docs.google.com/forms/d/e/1FAIpQLSeADXbQ1JM3jnBfBrTjWJiRXxAy29iJozc8dpGKr_jvNyvUwQ/viewform?usp=sharing'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
except Exception as e:
    print(f"Error fetching URL: {e}")
    exit(1)

match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', html)
if match:
    data = json.loads(match.group(1))
    title = data[1][8]
    print(f"Form Title: {title}")
    questions = data[1][1]
    
    for q in questions:
        q_title = q[1]
        
        # Check if the question array contains choices/inputs
        if len(q) > 4 and q[4]:
            entry_id = q[4][0][0]
            options = []
            if len(q[4][0]) > 1 and q[4][0][1]:
                options = [opt[0] for opt in q[4][0][1]]
            
            print(f"Question: {q_title}")
            print(f"  Entry ID: entry.{entry_id}")
            if options:
                print(f"  Options: {options}")
            print("-" * 40)
else:
    print("Could not find FB_PUBLIC_LOAD_DATA_ in the HTML.")
