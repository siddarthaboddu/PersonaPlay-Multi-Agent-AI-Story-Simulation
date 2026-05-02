import sys
import re

with open('frontend/src/components/modals/ConfigModal.jsx', 'r') as f:
    lines = f.readlines()

tags = []
for i, line in enumerate(lines):
    line_num = i + 1
    for match in re.finditer(r'<(div|/div)', line):
        tag = match.group(0)
        if tag == '<div':
            tags.append(line_num)
        else:
            if not tags:
                print(f"Error: </div> at line {line_num} has no opening tag")
            else:
                tags.pop()

if tags:
    print(f"Error: {len(tags)} unclosed <div> tags remaining:")
    for l in tags:
        print(f"Opened at line {l}")
else:
    print("All <div> tags balanced")
