import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values


def host_matches_cookie_domain(host: str, cookie_domain: str) -> bool:
    """Accept the exact cookie domain or a real DNS subdomain only."""
    return host == cookie_domain or host.endswith("." + cookie_domain)


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
            
    required = [
        "DATABASE_URL",
        "QWEN_API_KEY",
        "AUTH_SESSION_SECRET",
        "ADMIN_API_KEY",
        "CORS_ALLOWED_ORIGINS",
        "VOLTA_PUBLIC_APP_ORIGIN",
        "VOLTA_PUBLIC_API_BASE_URL",
        "VOLTA_PUBLIC_HEALTH_URL",
        "AUTH_COOKIE_DOMAIN",
        "FC_RUNTIME_ROLE_ARN",
        "FC_DISABLE_PUBLIC_INTERNET",
    ]
    missing = [name for name in required if not my_env.get(name)]
    if missing:
        print("Refusing production deploy; missing required release configuration: " + ", ".join(missing))
        return 1
    if my_env["CORS_ALLOWED_ORIGINS"].strip() == "*":
        print("Refusing production deploy; CORS_ALLOWED_ORIGINS must not be '*'.")
        return 1
    cors_origins = [origin.strip().rstrip("/") for origin in my_env["CORS_ALLOWED_ORIGINS"].split(",") if origin.strip()]
    invalid_origins = []
    for origin in cors_origins:
        parsed = urlparse(origin)
        if parsed.scheme != "https" or not parsed.netloc or (parsed.hostname or "").lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            invalid_origins.append(origin)
    if invalid_origins:
        print("Refusing production deploy; CORS origins must be non-local HTTPS origins: " + ", ".join(invalid_origins))
        return 1
    public_app_origin = my_env["VOLTA_PUBLIC_APP_ORIGIN"].strip().rstrip("/")
    if public_app_origin not in cors_origins:
        print("Refusing production deploy; CORS_ALLOWED_ORIGINS must include VOLTA_PUBLIC_APP_ORIGIN.")
        return 1
    public_api_origin = my_env["VOLTA_PUBLIC_API_BASE_URL"].strip().rstrip("/")
    api_host = (urlparse(public_api_origin).hostname or "").lower()
    app_host = (urlparse(public_app_origin).hostname or "").lower()
    cookie_domain = my_env["AUTH_COOKIE_DOMAIN"].strip().lower().lstrip(".")
    if not cookie_domain or not host_matches_cookie_domain(app_host, cookie_domain) or not host_matches_cookie_domain(api_host, cookie_domain):
        print("Refusing production deploy; AUTH_COOKIE_DOMAIN must be a shared parent domain for app and API hosts.")
        return 1
    if my_env["FC_DISABLE_PUBLIC_INTERNET"].strip().lower() != "true":
        print("Refusing production deploy; set FC_DISABLE_PUBLIC_INTERNET=true after API Gateway is configured.")
        return 1
    if my_env.get("AUTH_EMAIL_PROVIDER", "disabled").lower() not in {"", "disabled"}:
        email_required = ["AUTH_MAGIC_LINK_BASE_URL", "AUTH_EMAIL_WEBHOOK_URL", "AUTH_EMAIL_WEBHOOK_TOKEN"]
        missing_email = [name for name in email_required if not my_env.get(name)]
        if missing_email:
            print("Refusing production deploy; configured email provider is missing: " + ", ".join(missing_email))
            return 1
    print("Loaded production release configuration (secret values redacted).")
    
    # Run deploy command
    s_path = my_env.get("SERVERLESS_DEVS_BIN") or shutil.which("s") or "/home/lx_singw/.npm-global/bin/s"
    if not Path(s_path).exists() and not shutil.which(s_path):
        print("Error: Serverless Devs executable was not found. Set SERVERLESS_DEVS_BIN or add 's' to PATH.")
        return 1
    print("Running s deploy...")
    result = subprocess.run([s_path, "deploy", "-y"], env=my_env, cwd=str(repo_root))
    if result.returncode != 0:
        print(f"Error: s deploy failed with code {result.returncode}")
        return result.returncode
    print("Deployment succeeded!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
