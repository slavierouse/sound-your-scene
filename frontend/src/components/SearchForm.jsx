import { MagnifyingGlassIcon, MusicalNoteIcon } from '@heroicons/react/24/outline'

function SearchForm({ query, setQuery, onSubmit, isLoading }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    onSubmit(query.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="mb-8">
      <div className="flex gap-3">
        {/* Search Input */}
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Music for a period drama set in Elizabethan England"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none"
            disabled={isLoading}
          />
        </div>
        
        {/* Submit Button */}
        <button 
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-6 py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <MusicalNoteIcon className="h-5 w-5" />
          {isLoading ? 'Searching...' : 'Vibe'}
        </button>
      </div>
    </form>
  )
}

export default SearchForm