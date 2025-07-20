#!/bin/bash

# Deploy Gemma3-12b LLM Service using pre-packaged Google images
# Usage: ./deploy-gemma-llm.sh [PROJECT_ID] [REGION]

set -e

# Load environment variables if .env exists
if [ -f ../.env ]; then
    export $(cat ../.env | xargs)
fi

# Configuration
PROJECT_ID=${HACKATHON_PROJECT_ID:-${1:-"your-project-id"}}
REGION=${HACKATHON_PROJECT_REGION:-${2:-"europe-west1"}}
SERVICE_NAME="persona-flow-gemma-llm"
GEMMA_MODEL="gemma3-12b"  # Multi-modal capabilities

echo "Deploying Gemma3-12b LLM Service"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Model: $GEMMA_MODEL"
echo "Service: $SERVICE_NAME"

# Verify gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    echo "Please authenticate with gcloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Set project
echo "Setting project context..."
gcloud config set project $PROJECT_ID

# Enable necessary APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Deploy Gemma using pre-packaged image
echo "🏗️  Deploying Gemma3-12b with GPU..."
gcloud run deploy $SERVICE_NAME \
    --image us-docker.pkg.dev/cloudrun/container/gemma/$GEMMA_MODEL \
    --concurrency 4 \
    --cpu 8 \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --max-instances 1 \
    --memory 32Gi \
    --allow-unauthenticated \
    --no-cpu-throttling \
    --timeout=600 \
    --region $REGION \
    --no-gpu-zonal-redundancy \
    --labels dev-tutorial=hackathon-nyc-cloud-run-gpu-25

# Get Gemma URL
GEMMA_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "Gemma3-12b deployment complete!"
echo "Gemma URL: $GEMMA_URL"
echo "Health check: $GEMMA_URL/"
echo "Save this URL:"
echo "export GEMMA_URL=\"$GEMMA_URL\""
echo ""