import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import UploadFile, HTTPException
import os

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dvt-cloud"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "764846719658924"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "OmdiuCF8")
)

async def upload_screenshot(file: UploadFile, user_id: int = None):
    """
    Upload screenshot to Cloudinary
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")
        
        # Validate file size (max 5MB)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="File too large. Max 5MB allowed.")
        
        # Create folder path
        folder = "dvt-screenshots"
        if user_id:
            folder = f"{folder}/user-{user_id}"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            resource_type="image",
            transformation=[
                {"width": 800, "height": 600, "crop": "limit"},
                {"quality": "auto:good"}
            ]
        )
        
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"],
            "size": result["bytes"],
            "uploaded_at": result["created_at"]
        }
        
    except cloudinary.exceptions.Error as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

def delete_screenshot(public_id: str):
    """
    Delete screenshot from Cloudinary
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result
    except Exception as e:
        print(f"Failed to delete image: {e}")
        return None

def get_screenshot_info(public_id: str):
    """
    Get screenshot information
    """
    try:
        result = cloudinary.api.resource(public_id)
        return result
    except Exception as e:
        print(f"Failed to get image info: {e}")
        return None

def generate_thumbnail_url(url: str, width: int = 300, height: int = 200):
    """
    Generate thumbnail URL from Cloudinary URL
    """
    # Cloudinary URL transformation
    if "res.cloudinary.com" in url:
        # Extract parts and add transformation
        parts = url.split("/upload/")
        if len(parts) == 2:
            transformed_url = f"{parts[0]}/upload/w_{width},h_{height},c_fill/{parts[1]}"
            return transformed_url
    
    return url
