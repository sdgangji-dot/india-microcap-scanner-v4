import os
import subprocess

repo_dir = r"C:\Users\sdgangji\OneDrive\Projects\mf_monthly_micro_smallcap_scanner"
os.chdir(repo_dir)

# Clean env without GIT_CONFIG_GLOBAL / GIT_CONFIG_SYSTEM pointing to NUL
env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_CONFIG')}

def run_git(args):
    res = subprocess.run(['git'] + args, env=env, capture_output=True, text=True)
    print(f"CMD: git {' '.join(args)}")
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
    return res.returncode == 0

# 1. Init git if not exists
if not os.path.exists(os.path.join(repo_dir, '.git')):
    run_git(['init'])

# 2. Config user
run_git(['config', 'user.name', 'sdgangji'])
run_git(['config', 'user.email', 'sdgangji@users.noreply.github.com'])

# 3. Set remote origin
res_remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], env=env, capture_output=True, text=True)
if res_remote.returncode != 0:
    run_git(['remote', 'add', 'origin', 'https://github.com/sdgangji/india-microcap-scanner-v4.git'])
else:
    run_git(['remote', 'set-url', 'origin', 'https://github.com/sdgangji/india-microcap-scanner-v4.git'])

# 4. Add all files
run_git(['add', '.'])

# 5. Commit
run_git(['commit', '-m', 'Enable automated daily 5-tier scan and HTML publish'])

# 6. Push
run_git(['branch', '-M', 'main'])
push_res = subprocess.run(['git', 'push', '-u', 'origin', 'main'], env=env, capture_output=True, text=True)
print(f"PUSH STDOUT: {push_res.stdout}")
print(f"PUSH STDERR: {push_res.stderr}")
