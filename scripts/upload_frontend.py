import os
import sys
import oss2
from pathlib import Path
from dotenv import dotenv_values

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    env_path = repo_root / ".env"
    if not env_path.exists():
        print(f"Error: .env not found at {env_path}")
        return 1

    env = dotenv_values(env_path)
    
    access_key_id = env.get("ALIBABA_ACCESS_KEY_ID")
    access_key_secret = env.get("ALIBABA_ACCESS_KEY_SECRET")
    bucket_name = env.get("ALIBABA_OSS_BUCKET", "volta-memory-frontend-static")
    region = env.get("ALIBABA_REGION", "ap-southeast-1")
    
    if not access_key_id or not access_key_secret:
        print("Error: Alibaba AccessKey credentials not found in .env")
        return 1
        
    endpoint = f"https://oss-{region}.aliyuncs.com"
    
    print(f"Connecting to OSS bucket '{bucket_name}' at endpoint '{endpoint}'...")
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    
    frontend_out = repo_root / "frontend" / "out"
    if not frontend_out.exists():
        print(f"Error: Frontend build directory not found at {frontend_out}. Did you run npm run build?")
        return 1
        
    print("Uploading static files to OSS...")
    for root, dirs, files in os.walk(frontend_out):
        for file in files:
            local_file = Path(root) / file
            relative_path = local_file.relative_to(frontend_out)
            object_key = str(relative_path).replace("\\", "/")
            
            # Map common media types
            content_type = "application/octet-stream"
            ext = local_file.suffix.lower()
            if ext == ".html":
                content_type = "text/html; charset=utf-8"
            elif ext == ".css":
                content_type = "text/css; charset=utf-8"
            elif ext == ".js":
                content_type = "application/javascript; charset=utf-8"
            elif ext == ".svg":
                content_type = "image/svg+xml"
            elif ext == ".png":
                content_type = "image/png"
            elif ext == ".jpg" or ext == ".jpeg":
                content_type = "image/jpeg"
            elif ext == ".json":
                content_type = "application/json"
            
            headers = {"Content-Type": content_type}
            print(f"  Uploading {object_key}...")
            try:
                bucket.put_object_from_file(object_key, str(local_file), headers=headers)
            except Exception as e:
                print(f"  [ERROR] Failed to upload {object_key}: {e}")
                return 1
            
    print("Upload completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
