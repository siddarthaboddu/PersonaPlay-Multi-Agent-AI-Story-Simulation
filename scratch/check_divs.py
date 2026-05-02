import sys

with open('frontend/src/components/modals/ConfigModal.jsx', 'r') as f:
    content = f.read()

tags = []
import re
# Simplified tag matcher
for match in re.finditer(r'<(div|/div)', content):
    tag = match.group(0)
    if tag == '<div':
        tags.append('<div')
    else:
        if not tags:
            print(f"Error: </div> at pos {match.start()} has no opening tag")
        else:
            tags.pop()

if tags:
    print(f"Error: {len(tags)} unclosed <div> tags remaining")
    for t in tags:
        print(t)
else:
    print("All <div> tags balanced")
