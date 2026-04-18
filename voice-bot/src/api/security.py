"""Security dependencies for the VoiceBot API."""
from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader
from core.config import config

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Validates the API key from headers."""
    if not config.VOICEBOT_API_KEY:
        return None
        
    if api_key == config.VOICEBOT_API_KEY:
        return api_key
        
    raise HTTPException(
        status_code=403, 
        detail="Could not validate credentials - Missing or invalid API Key"
    )

def get_max_upload_size():
    """Returns the maximum allowed upload size in bytes."""
    return config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
