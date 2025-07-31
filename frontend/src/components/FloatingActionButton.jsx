import { BookmarkIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'

function FloatingActionButton({ 
  bookmarkCount, 
  isViewingSaved, 
  onToggleView,
  hasStartedSession 
}) {
  // Always show "Back to search" when viewing saved tracks
  if (isViewingSaved) {
    return (
      <button
        onClick={onToggleView}
        className="fixed bottom-4 left-4 sm:bottom-6 sm:left-6 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-gray-800 text-white hover:bg-gray-900 rounded-lg shadow-lg text-sm sm:text-base font-medium transition-colors"
      >
        <ArrowLeftIcon className="w-4 h-4 sm:w-5 sm:h-5" />
        <span className="hidden sm:inline">Back to search</span>
        <span className="sm:hidden">Back</span>
      </button>
    )
  }

  // Don't show button if no bookmarks and user has started a session
  if (bookmarkCount === 0 && hasStartedSession) {
    return null
  }

  // Show "see your last X saved tracks" when on blank page with saved tracks (no session started)
  if (bookmarkCount > 0 && !hasStartedSession) {
    return (
      <button
        onClick={onToggleView}
        className="fixed bottom-4 left-4 sm:bottom-6 sm:left-6 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-teal-600 text-white rounded-lg shadow-lg hover:bg-teal-700 transition-colors text-sm sm:text-base font-medium"
      >
        <BookmarkIcon className="w-4 h-4 sm:w-5 sm:h-5" />
        <span className="hidden sm:inline">See your last {bookmarkCount} saved tracks</span>
        <span className="sm:hidden">Saved ({bookmarkCount})</span>
      </button>
    )
  }

  // Show "View saved tracks" button when user has started session and has bookmarks
  if (hasStartedSession && bookmarkCount > 0) {
    return (
      <button
        onClick={onToggleView}
        className="fixed bottom-4 left-4 sm:bottom-6 sm:left-6 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-teal-600 text-white hover:bg-teal-700 rounded-lg shadow-lg text-sm sm:text-base font-medium transition-colors"
      >
        <BookmarkIcon className="w-4 h-4 sm:w-5 sm:h-5" />
        <span className="hidden sm:inline">View {bookmarkCount} saved tracks</span>
        <span className="sm:hidden">Saved ({bookmarkCount})</span>
      </button>
    )
  }

  return null
}

export default FloatingActionButton