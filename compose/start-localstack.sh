#!/bin/bash
export AWS_REGION=eu-west-2
export AWS_DEFAULT_REGION=eu-west-2
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# S3 buckets
aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-uc-rag-evaluation-data-ingestion-data

# SQS queues
# aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name ai-uc-rag-evaluation-data-ingest-job
