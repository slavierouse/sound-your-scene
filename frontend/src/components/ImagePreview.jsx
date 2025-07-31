import { XMarkIcon } from '@heroicons/react/24/outline'

function ImagePreview({ imageData, onRemove, disabled = false }) {
  if (!imageData) return null

  const handleRemove = () => {
    if (!disabled && onRemove) {
      // Clean up the preview URL to prevent memory leaks
      if (imageData.previewUrl && imageData.previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(imageData.previewUrl)
      }
      onRemove()
    }
  }

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-start gap-3">
        {/* Image Preview */}
        <div className="relative">
          <img
            src={imageData.previewUrl}
            alt="Scene image"
            className="w-16 h-16 object-cover rounded-lg border border-gray-300"
          />
          {!disabled && (
            <button
              onClick={handleRemove}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
              title="Remove image"
            >
              <XMarkIcon className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Image Info */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 mb-1">
            Your scene image
          </div>
          <div className="text-xs text-gray-500">
            {imageData.originalFile?.name || 'Uploaded image'}
          </div>
          {imageData.originalFile && (
            <div className="text-xs text-gray-400 mt-1">
              {Math.round(imageData.originalFile.size / 1024)} KB
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ImagePreview