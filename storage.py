"""
LiftCoach AI — Cloud Storage Module
Abstraction layer for file storage with automatic fallback.
- If R2 credentials are configured → upload to Cloudflare R2, return public URL
- If not configured → save locally (current behavior)
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────
# Try to load from environment (set via .env or Railway config)
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "liftcoach-videos")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(APP_DIR, "output")
PHOTOS_DIR = os.path.join(APP_DIR, "profile_photos")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PHOTOS_DIR, exist_ok=True)


def _r2_enabled() -> bool:
    """Check whether R2 credentials are configured."""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY)


def _get_s3_client():
    """Create a boto3 S3 client configured for Cloudflare R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


# ═══════════════════════════════════════════════════════════
#  VIDEO STORAGE
# ═══════════════════════════════════════════════════════════

def upload_video(local_path: str, filename: str) -> str:
    """Upload an analyzed video. Returns a URL (R2) or local path."""
    if _r2_enabled():
        try:
            s3 = _get_s3_client()
            key = f"videos/{filename}"
            s3.upload_file(local_path, R2_BUCKET_NAME, key, ExtraArgs={"ContentType": "video/mp4"})
            # Clean up local file after successful upload
            try:
                os.remove(local_path)
            except OSError:
                pass
            url = f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else key
            logger.info(f"Uploaded video to R2: {key}")
            return url
        except Exception as e:
            logger.warning(f"R2 upload failed, falling back to local: {e}")
            return local_path
    else:
        return local_path


def get_video_url(filename_or_url: str) -> str | None:
    """Resolve a video filename/URL to something playable.
    - If it's a full URL (R2), return as-is.
    - If it's a local filename, return the local path if it exists.
    """
    if not filename_or_url:
        return None
    if filename_or_url.startswith("http"):
        return filename_or_url

    # Check if R2 is enabled - dynamically reconstruct the URL if it's just a filename
    if _r2_enabled() and R2_PUBLIC_URL:
        # Check if the filename already has the 'videos/' prefix
        prefix = "" if filename_or_url.startswith("videos/") else "videos/"
        return f"{R2_PUBLIC_URL}/{prefix}{filename_or_url}"

    # Local file fallback
    local_path = os.path.join(OUTPUT_DIR, filename_or_url)
    if os.path.exists(local_path):
        return local_path
    # Maybe it's stored with the full local path already
    if os.path.exists(filename_or_url):
        return filename_or_url
    return None


# ═══════════════════════════════════════════════════════════
#  PROFILE PHOTO STORAGE
# ═══════════════════════════════════════════════════════════

def upload_profile_photo(photo_bytes: bytes, user_id: int, original_filename: str) -> str:
    """Upload a profile photo. Returns a URL (R2) or local relative path."""
    ext = os.path.splitext(original_filename)[1] or ".png"
    saved_name = f"user_{user_id}_{int(time.time())}{ext}"

    if _r2_enabled():
        try:
            s3 = _get_s3_client()
            key = f"photos/{saved_name}"
            content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"
            s3.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=key,
                Body=photo_bytes,
                ContentType=content_type,
            )
            url = f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else key
            logger.info(f"Uploaded photo to R2: {key}")
            return url
        except Exception as e:
            logger.warning(f"R2 photo upload failed, falling back to local: {e}")

    # Local fallback
    saved_path = os.path.join(PHOTOS_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(photo_bytes)
    return f"profile_photos/{saved_name}"


def get_photo_url(photo_path: str) -> str | None:
    """Resolve a profile photo path/URL to a displayable path."""
    if not photo_path:
        return None
    if photo_path.startswith("http"):
        return photo_path
    full_path = os.path.join(APP_DIR, photo_path)
    if os.path.exists(full_path):
        return full_path
    return None


# ═══════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════

def delete_file(key_or_path: str):
    """Delete a file from R2 or local storage."""
    if _r2_enabled() and not os.path.exists(key_or_path):
        try:
            s3 = _get_s3_client()
            s3.delete_object(Bucket=R2_BUCKET_NAME, Key=key_or_path)
            logger.info(f"Deleted from R2: {key_or_path}")
        except Exception as e:
            logger.warning(f"R2 delete failed: {e}")
    elif os.path.exists(key_or_path):
        try:
            os.remove(key_or_path)
        except OSError:
            pass


def storage_status() -> dict:
    """Return current storage configuration status."""
    return {
        "r2_enabled": _r2_enabled(),
        "r2_bucket": R2_BUCKET_NAME if _r2_enabled() else "N/A",
        "r2_public_url": R2_PUBLIC_URL if _r2_enabled() else "N/A",
        "local_output_dir": OUTPUT_DIR,
        "local_photos_dir": PHOTOS_DIR,
    }
