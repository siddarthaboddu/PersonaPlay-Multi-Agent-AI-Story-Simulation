import re

with open('frontend/src/components/modals/ConfigModal.jsx', 'r') as f:
    content = f.read()

for match in re.finditer(r'</?div', content):
    print(f"Found {match.group(0)} at pos {match.start()}")
