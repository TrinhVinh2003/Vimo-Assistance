#!/bin/bash

echo "📥 [INFO] Downloading data from Google Drive..."

# Create directory for data storage
mkdir -p /app/src/data

# Download zip file from Google Drive (replace ID with yours)
gdown --id 1TZXgLuzL2NCcS3G2D5QaSeKuV9zmlVVi -O /app/src/data/data.zip

# Extract files
unzip -o /app/src/data/data.zip -d /app/src/data/
rm /app/src/data/data.zip

echo "✅ [DONE] Data has been downloaded to /app/src/data directory"
