
try:
    with open('valid_models.txt', 'r', encoding='utf-16') as f:
        content = f.read()
        for line in content.splitlines():
            if 'gemini' in line.lower():
                print(line)
except Exception as e:
    print(f"Error: {e}")
