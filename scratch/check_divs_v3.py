import re

with open('frontend/src/components/modals/ConfigModal.jsx', 'r') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    line_num = i + 1
    for match in re.finditer(r'</?div', line):
        tag = match.group(0)
        if tag == '<div':
            stack.append((line_num, line.strip()))
        else:
            if not stack:
                print(f"Error: extra </div> at line {line_num}")
            else:
                stack.pop()

if stack:
    print(f"Unclosed divs:")
    for l, c in stack:
        print(f"Line {l}: {c}")
