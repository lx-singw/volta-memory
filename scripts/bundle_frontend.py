import shutil
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    src = repo_root / "frontend" / "out"
    dst = repo_root / "backend" / "app" / "static"

    if not src.exists():
        print(f"Error: Frontend build not found at {src}. Run npm run build first.")
        return 1

    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)
    print("Successfully bundled frontend/out into backend/app/static!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
