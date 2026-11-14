"""
19_upload_cloudflare_r2.py - publish the advice to Cloudflare R2 (replaces the Tiger Cloud load, 07).
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Uploads data/app_rotation_advice.json to an R2 bucket, then downloads it back and checks it is
byte-identical. With the bucket's Public Development URL (r2.dev) enabled, the app reads it at
    https://pub-<id>.r2.dev/app_rotation_advice.json
No password is ever needed by the app. The upload uses an R2 API token (Object Read & Write).

Credentials (never printed, never committed), from environment variables or a file .r2.env in the
project folder (one KEY=value per line; *.env is in .gitignore):
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
    R2_PUBLIC_URL   optional, e.g. https://pub-xxxx.r2.dev  (only used to print the app's link)
    R2_ENDPOINT     optional override (testing); default https://<account>.r2.cloudflarestorage.com
Run:  uv run --with boto3 python scripts/19_upload_cloudflare_r2.py   (run_weekly.sh does this)
"""
import os, sys
import boto3
from botocore.config import Config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [  # (local path, key in bucket, content type)
    ("data/app_rotation_advice.json", "app_rotation_advice.json", "application/json"),
]

cfg = {}
envf = os.path.join(ROOT, ".r2.env")
if os.path.exists(envf):
    for line in open(envf, encoding="utf-8-sig"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
get = lambda k: os.environ.get(k) or cfg.get(k)
need = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
missing = [k for k in need if not get(k)]
if missing:
    sys.exit(f"Missing R2 settings: {', '.join(missing)} (set them as environment variables or in .r2.env)")

endpoint = get("R2_ENDPOINT") or f"https://{get('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"
s3 = boto3.client("s3", endpoint_url=endpoint, region_name="auto",
                  aws_access_key_id=get("R2_ACCESS_KEY_ID"),
                  aws_secret_access_key=get("R2_SECRET_ACCESS_KEY"),
                  config=Config(retries={"max_attempts": 5, "mode": "standard"}))
bucket = get("R2_BUCKET")

ok = True
for local, key, ctype in FILES:
    path = os.path.join(ROOT, local)
    body = open(path, "rb").read()
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=ctype,
                  CacheControl="public, max-age=300")          # app sees a refresh within ~5 min
    back = s3.get_object(Bucket=bucket, Key=key)["Body"].read()   # read it back and compare
    same = back == body
    ok &= same
    print(f"uploaded {local} -> r2://{bucket}/{key} ({len(body):,} bytes) - "
          f"{'verified identical' if same else 'MISMATCH after upload'}")
pub = get("R2_PUBLIC_URL")
if pub:
    print("app link:", pub.rstrip("/") + "/" + FILES[0][1])
if not ok:
    sys.exit("R2 upload check failed.")
print("R2 upload done.")
