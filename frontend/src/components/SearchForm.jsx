import { MagnifyingGlassIcon, MusicalNoteIcon } from '@heroicons/react/24/outline'
import ImageUpload from './ImageUpload'
import ImagePreview from './ImagePreview'

function SearchForm({ query, setQuery, onSubmit, isLoading, placeholder, buttonText, imageData, onImageUploaded, onImageRemoved, isInitialSearch = false }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    onSubmit(query.trim(), imageData)
    setQuery('') // Clear input after submit
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 sm:mb-8">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search Input */}
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder || "Music for a period drama set in England"}
            className="w-full pl-9 sm:pl-10 pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none"
            disabled={isLoading}
          />
        </div>
        
        {/* Submit Button */}
        <button 
          type="submit"
          disabled={isLoading || !query.trim()}
          className="w-full sm:w-auto px-4 sm:px-6 py-2.5 sm:py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-400 text-white text-sm sm:text-base font-medium rounded-lg transition-colors flex items-center justify-center gap-2 min-h-[44px]"
        >
          <MusicalNoteIcon className="h-4 w-4 sm:h-5 sm:w-5" />
          {isLoading ? 'Searching...' : (buttonText || 'Search')}
        </button>
      </div>
      
      {/* Image Upload - Only show for initial search */}
      {isInitialSearch && (
        <div className="mt-4">
          {!imageData ? (
            <ImageUpload 
              onImageUploaded={onImageUploaded}
              onImageRemoved={onImageRemoved}
              disabled={isLoading}
            />
          ) : (
            <ImagePreview 
              imageData={imageData}
              onRemove={onImageRemoved}
              disabled={isLoading}
            />
          )}
        </div>
      )}
    </form>
  )
}

export default SearchForm