import os
from pathlib import Path
import logging
from google.cloud import storage
from google.api_core.exceptions import Conflict
from dotenv import load_dotenv

# Auth: load creds from .env
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

STAGED_DATA_DIR = Path("data/staged")

# Bucket: name must be globally unique across GCP
BUCKET_NAME = "vic-catch-datalake-raw" 
GCP_REGION = "australia-southeast1" # Host in Melb for zero-latency BigQuery joins

def upload_staged_data():
    logging.info("Initializing Google Cloud Storage client...")
    
    try:
        # Client: SDK picks up the GOOGLE_APPLICATION_CREDENTIALS env var automatically
        client = storage.Client()
    except Exception as e:
        logging.error(f"Authentication failed. Check your .env file and JSON key. Error: {e}")
        return

    # Bucket reference
    try:
        # Local ref to the bucket (avoids extra API calls)
        bucket = client.bucket(BUCKET_NAME)
        logging.info(f"Targeting manual bucket: {BUCKET_NAME}")
    except Exception as e:
        logging.error(f"Failed to reference bucket: {e}")
        return

    # Upload loop
    if not STAGED_DATA_DIR.exists():
        logging.error(f"Cannot find local directory: {STAGED_DATA_DIR}")
        return

    parquet_files = list(STAGED_DATA_DIR.glob("*.parquet"))
    if not parquet_files:
        logging.warning("No Parquet files found to upload in data/staged/.")
        return

    logging.info(f"Found {len(parquet_files)} Parquet files. Starting upload...")

    for file_path in parquet_files:
        # I'm storing these under the 'staged/' prefix in the bucket
        blob_name = f"staged/{file_path.name}"
        blob = bucket.blob(blob_name)
        
        logging.info(f"Uploading {file_path.name} -> gs://{BUCKET_NAME}/{blob_name} ...")
        
        blob.upload_from_filename(str(file_path))
        logging.info(f"✓ {file_path.name} uploaded.")

    logging.info("All files successfully migrated to Google Cloud Storage!")

if __name__ == "__main__":
    upload_staged_data()