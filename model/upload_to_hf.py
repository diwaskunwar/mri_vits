import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv('.env')

# HF Credentials
hf_token = os.getenv('HF_TOKEN')
hf_username = os.getenv('HF_USERNAME')

# Configuration
model_path = './brain_tumor_vit_v0.1.0'
metrics_files = [
    './evaluation_summary.json',
    './confidence_stats.json'
]
repo_name = 'brain-tumor-vit-candor'
repo_id = f"{hf_username}/{repo_name}"

def upload_to_huggingface():
    if not hf_token or not hf_username:
        logger.error("HF_TOKEN or HF_USERNAME not found in .env")
        return

    api = HfApi(token=hf_token)

    try:
        # Create or retrieve repository
        logger.info(f"Creating repository {repo_id} if it doesn't exist...")
        api.create_repo(repo_id=repo_id, exist_ok=True, repo_type="model")

        # Upload model directory
        logger.info(f"Uploading model contents from {model_path} to {repo_id}...")
        api.upload_folder(
            folder_path=model_path,
            repo_id=repo_id,
            repo_type="model",
            commit_message="Initial model upload",
            ignore_patterns=["checkpoint-*", "checkpoint-*/*"]
        )
        logger.info("Model upload complete!")

        # Upload metrics files
        for metric_file in metrics_files:
            if os.path.exists(metric_file):
                logger.info(f"Uploading metric file {metric_file} to {repo_id}...")
                api.upload_file(
                    path_or_fileobj=metric_file,
                    path_in_repo=os.path.basename(metric_file),
                    repo_id=repo_id,
                    repo_type="model",
                    commit_message=f"Upload metrics {os.path.basename(metric_file)}"
                )
            else:
                logger.warning(f"Metric file {metric_file} not found.")

        logger.info("All uploads to Hugging Face completed successfully!")
        logger.info(f"You can view your model here: https://huggingface.co/{repo_id}")

    except Exception as e:
        logger.error(f"Error uploading to Hugging Face: {e}")

if __name__ == '__main__':
    upload_to_huggingface()
