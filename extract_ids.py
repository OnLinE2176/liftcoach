import re
import json

with open("form.html", "r", encoding="utf-8") as f:
    html = f.read()

# The form data is stored in FB_PUBLIC_LOAD_DATA_
match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);</script>', html)
if match:
    data = json.loads(match.group(1))
    
    # Form metadata is in data[1][1]
    title = data[1][8]
    print(f"Form Title: {title}")
    
    questions = data[1][1]
    for q in questions:
        q_id = q[0]
        q_title = q[1]
        q_type = q[3]
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
    print("Could not find form data.")
