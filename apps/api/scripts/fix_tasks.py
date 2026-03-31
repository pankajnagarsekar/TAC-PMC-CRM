import re
file_path = 'apps/api/scripts/seed_production.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

if '"task_status":' not in text:
    lines = text.split('\n')
    out = []
    for line in lines:
        out.append(line)
        if '"percent_complete":' in line:
            match = re.search(r'\"percent_complete\":\s*([0-9]+)', line)
            if match:
                pc = int(match.group(1))
                status = "completed" if pc == 100 else ("in_progress" if pc > 0 else "draft")
                indent = line.split('"percent_complete"')[0]
                out.append(f'{indent}"task_status": "{status}",')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print("task_status injected into seed_production.py")
else:
    print("task_status already present")
