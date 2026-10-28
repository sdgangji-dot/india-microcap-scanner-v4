import os
import sys
import subprocess

repo_dir = r"C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner"
os.chdir(repo_dir)

env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_CONFIG')}

def run_cmd(cmd_list):
    res = subprocess.run(cmd_list, env=env, capture_output=True, text=True)
    print(f"CMD: {' '.join(cmd_list)}")
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
    return res.returncode == 0

# 1. Checkout ours for conflicted files
run_cmd(['git', 'checkout', '--ours', 'setup_and_publish_live_site.py'])
run_cmd(['git', 'checkout', '--ours', 'index.html'])
run_cmd(['git', 'checkout', '--ours', 'deploy_to_google.bat'])
run_cmd(['git', 'checkout', '--ours', 'archive/runs_manifest.json'])
run_cmd(['git', 'checkout', '--ours', 'archive/scan_2026-10-25.html'])

run_cmd(['git', 'add', '.'])

# 2. Run site publisher
print("Running setup_and_publish_live_site.py...")
pub_res = subprocess.run([sys.executable, 'setup_and_publish_live_site.py'], env=env, capture_output=True, text=True)
print("Publisher STDOUT:", pub_res.stdout)
print("Publisher STDERR:", pub_res.stderr)

# 3. Add and commit
run_cmd(['git', 'add', '.'])
run_cmd(['git', 'commit', '-m', 'Resolve merge conflicts and update live site dashboard'])

# 4. Get token and push
token_res = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
token = token_res.stdout.strip()
if token:
    remote_url = f"https://{token}@github.com/sdgangji-dot/india-microcap-scanner-v4.git"
    run_cmd(['git', 'remote', 'set-url', 'origin', remote_url])

run_cmd(['git', 'push', '-u', 'origin', 'main', '--force'])
