import re

f = open(r'G:\APPS SENA\sena-guia-aprendizaje-app\frontend\src\features\programa\use-programa-wizard.ts', 'r')
content = f.read()
f.close()

# Remove strings and comments
content = re.sub(r'//.*$', '', content, flags=re.M)
content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
content = re.sub(r'"(?:[^"\\]|\\.)*"', '', content)
content = re.sub(r"'(?:[^'\\]|\\.)*'", '', content)
content = re.sub(r'`(?:[^`\\]|\\.)*`', '', content)

opens_paren = content.count('(')
closes_paren = content.count(')')
opens_brace = content.count('{')
closes_brace = content.count('}')

print(f"Paren: ( {opens_paren} ) {closes_paren} diff={opens_paren - closes_paren}")
print(f"Brace: {{ {opens_brace} }} {closes_brace} diff={opens_brace - closes_brace}")

# Find where the first unclosed paren is
stack = []
for i, ch in enumerate(content):
    if ch == '(':
        stack.append(i)
    elif ch == ')':
        if stack:
            stack.pop()
        else:
            line = content[:i].count('\n') + 1
            print(f"Extra ) at line {line}, col {i - content.rfind('\n', 0, i)}")

for pos in stack:
    line = content[:pos].count('\n') + 1
    print(f"Unclosed ( at line {line}, col {pos - content.rfind('\n', 0, pos)}")
