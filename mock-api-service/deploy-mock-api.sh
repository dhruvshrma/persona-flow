#!/bin/bash

# PersonaFlow Mock API Deployment Script for Google Cloud Run
# Usage: ./deploy-mock-api.sh [PROJECT_ID] [REGION]

set -e

# Load environment variables if .env exists
if [ -f ../.env ]; then
    export $(cat ../.env | xargs)
fi

# Configuration
PROJECT_ID=${HACKATHON_PROJECT_ID:-${1:-"your-project-id"}}
REGION=${HACKATHON_PROJECT_REGION:-${2:-"us-central1"}}
SERVICE_NAME="persona-flow-mock-api"

echo "🚀 Deploying PersonaFlow Mock API to Google Cloud Run"
echo "📍 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "🏷️  Service: $SERVICE_NAME"

# Verify gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
    echo "❌ Please authenticate with gcloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Set project
echo "📋 Setting project context..."
gcloud config set project $PROJECT_ID

# Enable necessary APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Deploy to Cloud Run - gcloud will find Dockerfile in the source directory
echo "🏗️  Building and deploying Mock API service..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --memory 16Gi \
    --cpu 8 \
    --max-instances 10 \
    --platform managed

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Mock API deployment complete!"
echo "🔗 Service URL: $SERVICE_URL"
echo "🩺 Health check: $SERVICE_URL/health"
echo "📚 API docs: $SERVICE_URL/docs"
echo ""
echo "🧪 Quick test:"
echo "curl $SERVICE_URL/health"
echo ""
echo "📋 Save this URL for orchestrator configuration:"
echo "export MOCK_API_URL=\"$SERVICE_URL\""