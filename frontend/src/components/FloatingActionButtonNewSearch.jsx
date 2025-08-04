import { ArrowPathIcon } from '@heroicons/react/24/outline'

function FloatingActionButtonNewSearch({ hasResults, onNewSearch }) {
  // Only show when there are search results
  if (!hasResults) {
    return null
  }

  return (
    <button
      onClick={onNewSearch}
      className="fixed bottom-4 left-1/2 transform -translate-x-1/2 sm:bottom-6 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-black text-white hover:bg-gray-800 rounded-lg shadow-lg text-sm sm:text-base font-medium transition-colors"
    >
      <ArrowPathIcon className="w-4 h-4 sm:w-5 sm:h-5" />
      <span className="hidden sm:inline">Start a new search</span>
      <span className="sm:hidden">New search</span>
    </button>
  )
}

export default FloatingActionButtonNewSearch 