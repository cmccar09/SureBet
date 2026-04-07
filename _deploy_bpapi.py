"""Deploy _bpapi_patched.py as lambda_function.py to BettingPicksAPI in eu-west-1"""
import boto3
import zipfile
import io
import os
import shutil

FUNCTION_NAME = 'BettingPicksAPI'
REGION        = 'eu-west-1'
SRC_FILE      = '_bpapi_patched.py'

# Read patched source
with open(SRC_FILE, 'r', encoding='utf-8') as f:
    source = f.read()

# Create in-memory zip with the file named lambda_function.py
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
    info = zipfile.ZipInfo('lambda_function.py')
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, source.encode('utf-8'))
buf.seek(0)
zip_bytes = buf.read()
print(f"Zip size: {len(zip_bytes):,} bytes")

# Deploy
client = boto3.client('lambda', region_name=REGION)
resp = client.update_function_code(
    FunctionName=FUNCTION_NAME,
    ZipFile=zip_bytes,
    Publish=True,
)
print(f"Status  : {resp['ResponseMetadata']['HTTPStatusCode']}")
print(f"Version : {resp.get('Version')}")
print(f"Modified: {resp.get('LastModified')}")
print(f"SHA256  : {resp.get('CodeSha256')}")
print("Deploy: OK")
