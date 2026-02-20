import os
import sys

import boto3
import httpx

# Configuration
API_URL = "http://localhost:8085"
BUCKET_NAME = "ai-uc-rag-evaluation-data-ingestion-data"
FILE_PATH = "ai-opportunities-action-plan.jsonl"

# LocalStack S3 Configuration
S3_ENDPOINT = "http://localhost:4566"
AWS_REGION = "eu-central-1"


def main():
    if not os.path.exists(FILE_PATH):
        print(f"Error: File '{FILE_PATH}' not found.")
        sys.exit(1)

    print(f"🚀 Starting ingestion for {FILE_PATH}...")

    # 1. Create Knowledge Group
    print("1. Creating Knowledge Group...")
    group_data = {
        "name": "AI Action Plans",
        "description": "Government AI action plans and opportunities",
        "owner": "admin",
        "sources": [
            "https://www.gov.uk/government/publications/ai-playbook-for-the-uk-government/artificial-intelligence-playbook-for-the-uk-government-html"
        ],  # We'll add the source separately to get the ID
    }

    # Try to create, or find if exists would be better, but for simplicity we create specific one
    # Note: If group exists with same name, app might throw or create duplicate.
    # For idempotency in this script, we'll just create a new one for this run.
    with httpx.Client(timeout=30.0) as client:
        # Create Group
        # We need to pass at least one source to the create endpoint due to schema validation (min_items=1)
        # So we create it with the source immediately.
        group_data["sources"] = [
            {
                "name": "AI Opportunities Action Plan",
                "type": "PRECHUNKED_BLOB",
                "location": "s3://placeholder",  # Location isn't strictly validated for S3 prefix logic yet
            }
        ]

        resp = client.post(f"{API_URL}/knowledge/groups", json=group_data)
        if resp.status_code not in (200, 201):
            print(f"Failed to create group: {resp.text}")
            sys.exit(1)

        group = resp.json()
        group_id = group["groupId"]
        # In the response, sources is a dictionary key=source_id, value=SourceObj
        # We need the source ID to upload the file to the right S3 prefix
        source_id = list(group["sources"].keys())[0]

        print(f"   Created Group ID: {group_id}")
        print(f"   Created Source ID: {source_id}")

        # 2. Upload to S3
        print(f"2. Uploading to S3 bucket '{BUCKET_NAME}'...")
        s3 = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # noqa: S106
        )

        # The ingestion service expects files at {source_id}/{filename}
        s3_key = f"{source_id}/{os.path.basename(FILE_PATH)}"
        s3.upload_file(FILE_PATH, BUCKET_NAME, s3_key)
        print(f"   Uploaded to s3://{BUCKET_NAME}/{s3_key}")

        # 3. Trigger Ingestion
        print("3. Triggering Ingestion...")
        resp = client.post(f"{API_URL}/knowledge/groups/{group_id}/ingest")
        if resp.status_code != 202:
            print(f"Failed to trigger ingestion: {resp.text}")
            sys.exit(1)

        print("✅ Ingestion initiated successfully!")


if __name__ == "__main__":
    main()
