import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    env_path = repo_root / ".env"
    if not env_path.exists():
        print(f"Error: .env not found at {env_path}")
        return 1

    env = dotenv_values(env_path)
    
    # Merge env values into os.environ
    my_env = os.environ.copy()
    for k, v in env.items():
        if v is not None:
            my_env[k] = v
            
    print(f"Loaded DATABASE_URL: {my_env.get('DATABASE_URL')}")
    print(f"Loaded QWEN_API_KEY: {my_env.get('QWEN_API_KEY')[:10] if my_env.get('QWEN_API_KEY') else None}...")
    
    # Run deploy command
    s_path = "/home/lx_singw/.npm-global/bin/s"
    print("Running s deploy...")
    result = subprocess.run([s_path, "deploy", "-y"], env=my_env, cwd=str(repo_root))
    if result.returncode != 0:
        print(f"Error: s deploy failed with code {result.returncode}")
        return result.returncode
    print("Deployment succeeded!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
