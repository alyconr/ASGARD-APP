import re

file_path = r"G:\APPS SENA\sena-guia-aprendizaje-app\frontend\src\features\programa\components\programa-consolidado-revision.test.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove entryMode="EXCEL" and entryMode="PDF" props
content = re.sub(r'\s+entryMode="EXCEL"', '', content)
content = re.sub(r'\s+entryMode="PDF"', '', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Updated {file_path}")
