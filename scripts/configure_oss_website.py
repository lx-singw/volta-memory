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
    
    print(f"Connecting to OSS bucket '{bucket_name}' to enable static website hosting...")
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    
    try:
        # Enable website hosting configuration
        # Index document: index.html
        # Error document: index.html (Next.js client-side routing fallback)
        website_cfg = oss2.models.BucketWebsite(index_file='index.html', error_file='index.html')
        bucket.put_bucket_website(website_cfg)
        print("Successfully enabled static website hosting configuration on the OSS bucket!")
    except Exception as e:
        print(f"Error enabling static website configuration: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
