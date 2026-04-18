"""Vision API endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from core.vision_client import get_vision_client
from api.security import verify_api_key, get_max_upload_size
from fastapi import Depends

router = APIRouter()

class VisionResponse(BaseModel):
    analysis: str
    model: str

@router.post("/analyze", response_model=VisionResponse)
async def analyze_image(
    prompt: str = Form("Describe this image."),
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """Analyze an uploaded image using the vision model."""
    max_size = get_max_upload_size()
    if file.size and file.size > max_size:
        raise HTTPException(status_code=413, detail="Image too large")
        
    try:
        contents = await file.read()
        client = get_vision_client()
        analysis = await client.analyze_image(contents, prompt)
        
        return VisionResponse(
            analysis=analysis,
            model=client.model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
