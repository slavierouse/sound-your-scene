import { useState, useRef } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function ImageUpload({ onImageUploaded, onImageRemoved, disabled }) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const validateFile = (file) => {
    const MAX_SIZE = 2 * 1024 * 1024 // 2MB
    const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Please select a valid image file (JPEG, PNG, or WebP)'
    }
    
    if (file.size > MAX_SIZE) {
      return 'Image must be smaller than 2MB'
    }
    
    return null
  }

  const validateImageDimensions = (file) => {
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        if (img.width > 1920 || img.height > 1920) {
          resolve('Image dimensions must be 1920x1920 pixels or smaller')
        } else if (img.width < 10 || img.height < 10) {
          resolve('Image must be at least 10x10 pixels')
        } else {
          resolve(null)
        }
      }
      img.onerror = () => resolve('Invalid image file')
      img.src = URL.createObjectURL(file)
    })
  }

  const handleFileSelect = async (file) => {
    setError(null)
    
    // Basic validation
    const fileError = validateFile(file)
    if (fileError) {
      setError(fileError)
      return
    }

    // Dimension validation
    const dimensionError = await validateImageDimensions(file)
    if (dimensionError) {
      setError(dimensionError)
      return
    }

    // Upload to server
    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE_URL}/upload-image`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      
      // Create a preview URL for the uploaded image
      const previewUrl = URL.createObjectURL(file)
      
      onImageUploaded({
        base64Data: result.base64_data,
        tempFileId: result.temp_file_id,
        previewUrl: previewUrl,
        originalFile: file
      })

    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || 'Failed to upload image')
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDrop = (event) => {
    event.preventDefault()
    const file = event.dataTransfer.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (event) => {
    event.preventDefault()
  }

  const handleClick = () => {
    if (!disabled && !isUploading) {
      fileInputRef.current?.click()
    }
  }

  const handleRemove = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    setError(null)
    onImageRemoved()
  }

  return (
    <div className="w-full">
      <div
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className={`
          relative cursor-pointer transition-colors py-2
          ${disabled || isUploading ? 'cursor-not-allowed opacity-50' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/webp"
          onChange={handleFileChange}
          className="hidden"
          disabled={disabled || isUploading}
        />
        
        <div className="flex items-center gap-2 text-sm">
          {isUploading ? (
            <span className="text-gray-600">Uploading...</span>
          ) : (
            <>
              <button
                type="button"
                className="text-teal-600 hover:text-teal-700 font-medium"
              >
                + (Optional) Add an image
              </button>
              <span className="text-gray-500">
                JPEG, PNG, WebP • Max 2MB • Max 1920x1920px
              </span>
            </>
          )}
        </div>
      </div>
      
      {error && (
        <div className="mt-2 text-sm text-red-600 flex items-center gap-2">
          <XMarkIcon className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  )
}

export default ImageUpload