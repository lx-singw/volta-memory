import os
from pathlib import Path

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    frontend_out = repo_root / "frontend" / "out"
    if not frontend_out.exists():
        print(f"Error: Build folder not found at {frontend_out}")
        return 1

    print("Post-processing Next.js exported files to make assets relative...")
    for file_name in ["index.html", "memory.html", "404.html"]:
        file_path = frontend_out / file_name
        if not file_path.exists():
            print(f"  Skipping non-existent file {file_name}")
            continue

        print(f"  Processing {file_name}...")
        content = file_path.read_text(encoding="utf-8")

        # 1. Convert absolute "/_next/" paths to relative "_next/"
        content = content.replace('"/_next/', '"_next/')
        content = content.replace('/_next/static/', '_next/static/')

        # 2. Convert absolute "/memory" and "/" navigation links to static relative paths
        content = content.replace('href="/"', 'href="index.html"')
        content = content.replace('href="/memory"', 'href="memory.html"')

        file_path.write_text(content, encoding="utf-8")

    print("Post-processing completed successfully!")
    return 0

if __name__ == '__main__':
    main()
