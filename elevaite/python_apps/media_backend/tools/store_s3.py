from fastapi import UploadFile
import os
import hashlib
import boto3
import uuid
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_md5(image_bytes: bytes) -> str:
    """Calculate MD5 hash of image bytes"""
    return hashlib.md5(image_bytes).hexdigest()

def generate_creative_id() -> str:
    """Generate a unique ID for a creative"""
    # Combine UUID with timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = f"creative_{timestamp}_{str(uuid.uuid4())[:8]}"
    return unique_id

def upload_to_s3(image_bytes: bytes, key_prefix: str = "generated") -> dict:
    """Uploads image to S3 with MD5-based file key and returns key + creative_id (no presigned URL)"""
    s3 = boto3.client(
        "s3",
        region_name='us-west-1',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    try:
        # Generate MD5 hash and create file key
        md5_hash = calculate_md5(image_bytes)
        file_key = f"{key_prefix}/{md5_hash}.png"

        # Generate a unique creative ID
        creative_id = generate_creative_id()

        # Upload with MD5-based key
        s3.upload_fileobj(
            BytesIO(image_bytes),
            os.getenv('S3_BUCKET'),
            file_key,
            ExtraArgs={
                'ContentType': 'image/png',
                'ACL': 'private'
            }
        )

        return {
            'key': file_key,
            'creative_id': creative_id,
            'upload_timestamp': datetime.now().isoformat(),
            'bucket': os.getenv('S3_BUCKET')
        }

    except Exception as e:
        logger.error(f"Error Uploading the Generated Image: {e}")
        return {}


def get_image_from_s3(s3_key: str) -> bytes:
    """Retrieve image bytes from S3 using the stored key"""
    s3 = boto3.client(
        "s3",
        region_name='us-west-1',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    try:
        response = s3.get_object(Bucket=os.getenv('S3_BUCKET'), Key=s3_key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error retrieving image from S3: {e}")
        return b''


def generate_secure_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a longer-term presigned URL when needed (optional)"""
    s3 = boto3.client(
        "s3",
        region_name='us-west-1',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': os.getenv('S3_BUCKET'), 'Key': s3_key},
            ExpiresIn=expires_in  # Default 1 hour, can be up to 7 days
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        return ""


def process_s3_keys_to_urls(content: str, expires_in: int = 3600) -> str:
    """
    Process content and replace S3 keys with valid presigned URLs.
    Detects S3 keys in markdown image format and replaces them with URLs.

    Args:
        content: String content that may contain S3 keys in markdown format
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Content with S3 keys replaced by valid presigned URLs
    """
    import re

    if not content:
        return content

    # Pattern to match S3 keys in markdown image format: ![alt](s3_key)
    # S3 keys typically look like: generated/abc123def456.png or uploaded/xyz789.png
    s3_key_pattern = r'!\[([^\]]*)\]\(((generated|uploaded)/[a-zA-Z0-9]+\.png)\)'

    def replace_s3_key(match):
        alt_text = match.group(1)
        s3_key = match.group(2)

        try:
            # Generate presigned URL for the S3 key
            presigned_url = generate_secure_presigned_url(s3_key, expires_in)
            if presigned_url:
                return f'![{alt_text}]({presigned_url})'
            else:
                logger.warning(f"Failed to generate URL for S3 key: {s3_key}")
                return match.group(0)  # Return original if URL generation fails
        except Exception as e:
            logger.error(f"Error processing S3 key {s3_key}: {e}")
            return match.group(0)  # Return original if error occurs

    # Replace all S3 keys with presigned URLs
    processed_content = re.sub(s3_key_pattern, replace_s3_key, content)

    return processed_content


def detect_s3_keys_in_content(content: str) -> list:
    """
    Detect S3 keys in content and return them as a list.

    Args:
        content: String content that may contain S3 keys

    Returns:
        List of S3 keys found in the content
    """
    import re

    if not content:
        return []

    # Pattern to match S3 keys in markdown image format
    s3_key_pattern = r'!\[([^\]]*)\]\(((generated|uploaded)/[a-zA-Z0-9]+\.png)\)'

    matches = re.findall(s3_key_pattern, content)
    # Extract just the S3 keys (second group from each match)
    s3_keys = [match[1] for match in matches]

    return s3_keys