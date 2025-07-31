import os
import base64
import uuid
import tempfile
from typing import Optional, Tuple
from PIL import Image
from fastapi import UploadFile, HTTPException
import io

class ImageService:
    # Security constraints
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_DIMENSION = 1920
    ALLOWED_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    async def validate_and_process_image(self, file: UploadFile) -> Tuple[str, str]:
        """
        Validate uploaded image and return base64 encoded data and temp file ID.
        
        Returns:
            Tuple[str, str]: (base64_data, temp_file_id)
        
        Raises:
            HTTPException: If validation fails
        """
        
        # Check file size
        if file.size and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Check content type
        if file.content_type not in self.ALLOWED_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type. Allowed types: {', '.join(self.ALLOWED_TYPES)}"
            )
        
        # Check file extension
        filename_lower = file.filename.lower() if file.filename else ""
        if not any(filename_lower.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=415,
                detail=f"Invalid file extension. Allowed extensions: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        try:
            content = await file.read()
            
            # Double-check file size after reading
            if len(content) > self.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
        except Exception as e:
            raise HTTPException(status_code=400, detail="Failed to read uploaded file")
        
        # Validate image content using PIL
        try:
            image = Image.open(io.BytesIO(content))
            
            # Verify it's actually an image by trying to load it
            image.verify()
            
            # Re-open for dimension checking (verify() closes the image)
            image = Image.open(io.BytesIO(content))
            width, height = image.size
            
            # Check dimensions
            if width > self.MAX_DIMENSION or height > self.MAX_DIMENSION:
                raise HTTPException(
                    status_code=413,
                    detail=f"Image dimensions too large. Maximum size is {self.MAX_DIMENSION}x{self.MAX_DIMENSION} pixels"
                )
            
            # Check for minimum dimensions (prevent 1x1 pixel attacks)
            if width < 10 or height < 10:
                raise HTTPException(
                    status_code=400,
                    detail="Image too small. Minimum size is 10x10 pixels"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file or corrupted data"
            )
        
        # Convert to RGB if necessary (for JPEG compatibility)
        try:
            if image.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB for consistent processing
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = rgb_image
            
            # Resize if needed to reduce memory usage
            if width > 1024 or height > 1024:
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Failed to process image"
            )
        
        # Generate temporary file ID for reference
        temp_file_id = str(uuid.uuid4())
        
        return base64_data, temp_file_id
    
    def cleanup_temp_files(self):
        """Clean up temporary directory"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Best effort cleanup

# Global instance
image_service = ImageService()