#!/bin/bash

echo "🎵 Creating SoundByMood deployment bundle..."

# Build the frontend with production environment
echo "📦 Building frontend..."
cd frontend

# Set production environment variables
export VITE_APP_DOMAIN=https://soundyourscene.hirenotes.com
export VITE_API_BASE_URL=https://soundyourscene.hirenotes.com

npm install
npm run build
cd ..

# Copy frontend build to API static directory
echo "📁 Copying frontend build to API..."
mkdir -p api/static
cp -r frontend/dist/* api/static/

# Create deployment bundle
echo "📦 Creating deployment bundle..."
rm -rf deployment-bundle
mkdir deployment-bundle

# Copy API files (excluding __pycache__)
cp -r api deployment-bundle/
find deployment-bundle/api -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
cp requirements.txt deployment-bundle/
cp Procfile deployment-bundle/
# Note: alembic files removed - running migrations manually
echo "ℹ️  Skipping alembic files - running migrations manually"
mkdir -p deployment-bundle/data
cp data/main_df.csv deployment-bundle/data/
# Note: .ebextensions removed - running alembic manually
echo "ℹ️  Skipping .ebextensions - running alembic manually"


# Create zip file
echo "🗜️ Creating zip file..."
cd deployment-bundle
zip -r ../soundbymood-deployment.zip .
cd ..

# aws s3 cp "soundbymood-deployment.zip" "s3://soundyourscene-versions/soundbymood-deployment-v3.zip"

# aws elasticbeanstalk create-application-version \
#   --application-name  Sound-your-scene \
#   --version-label     20250804-03 \
#   --source-bundle     S3Bucket=soundyourscene-versions,S3Key=soundbymood-deployment-v2.zip


# aws elasticbeanstalk update-environment \
#   --environment-name  Sound-your-scene-env-2 \
#   --version-label     20250804-03

echo "✅ Deployment bundle created: soundbymood-deployment.zip"
echo "📤 Upload this file to AWS Elastic Beanstalk" 