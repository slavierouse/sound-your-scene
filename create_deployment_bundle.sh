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
# Copy EB extensions for database migrations
if [ -d ".ebextensions" ]; then
    mkdir -p deployment-bundle/.ebextensions
    cp -r .ebextensions/* deployment-bundle/.ebextensions/
    echo "📋 Copied .ebextensions configuration"
else
    echo "⚠️  No .ebextensions directory found"
fi


# Create zip file
echo "🗜️ Creating zip file..."
cd deployment-bundle
zip -r ../soundbymood-deployment.zip .
cd ..

aws s3 cp "soundbymood-deployment.zip" "s3://soundyourscene-versions/soundbymood-deployment.zip"

aws elasticbeanstalk create-application-version \
  --application-name  Sound-your-scene \
  --version-label     20250804-01 \
  --source-bundle     S3Bucket=soundyourscene-versions,S3Key=soundbymood-deployment.zip


aws elasticbeanstalk update-environment \
  --environment-name  Sound-your-scene-env \
  --version-label     20250804-01 \
  --option-settings   "Namespace=aws:elasticbeanstalk:application:environment,OptionName=DATABASE_URL,Value=postgresql://api_user:kuzcok-8hykgu-Duwkop@pg-database-1.chhquxplmnn2.us-east-1.rds.amazonaws.com/soundbymood"

echo "✅ Deployment bundle created: soundbymood-deployment.zip"
echo "📤 Upload this file to AWS Elastic Beanstalk" 