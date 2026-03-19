import subprocess

def get_git_file_at_commit(commit, path):
    result = subprocess.run(['git', 'show', f'{commit}:{path}'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    return result.stdout

def find_function_in_git():
    # Get all commits that modified auth.py
    result = subprocess.run(['git', 'log', '--format=%H', 'apps/api/auth.py'], capture_output=True, text=True)
    commits = result.stdout.splitlines()
    
    for commit in commits:
        content = get_git_file_at_commit(commit, 'apps/api/auth.py')
        if 'get_token_from_header_or_query' in content:
            print(f"Found in commit: {commit}")
            lines = content.splitlines()
            start = -1
            for i, line in enumerate(lines):
                if 'def get_token_from_header_or_query' in line:
                    start = i
                    break
            if start != -1:
                # Print next 30 lines
                for i in range(start, min(start + 30, len(lines))):
                    print(lines[i])
                return

if __name__ == "__main__":
    find_function_in_git()
