import urllib.request
import re
import json

url = 'https://docs.google.com/forms/d/e/1FAIpQLSeADXbQ1JM3jnBfBrTjWJiRXxAy29iJozc8dpGKr_jvNyvUwQ/viewform?usp=sharing'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    html = response.read().decode('utf-8')

match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', html)
data = json.loads(match.group(1))
questions = data[1][1]

fields = []
for q in questions:
    q_title = q[1]
    if len(q) > 4 and q[4]:
        entry_id = q[4][0][0]
        options = []
        if len(q[4][0]) > 1 and q[4][0][1]:
            options = [opt[0] for opt in q[4][0][1]]
        fields.append({
            "title": q_title,
            "entry_id": f"entry.{entry_id}",
            "options": options
        })

with open('form_fields.json', 'w', encoding='utf-8') as f:
    json.dump(fields, f, indent=2)
