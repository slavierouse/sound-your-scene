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
        className="fixed bottom-6 left-6 flex items-center gap-3 px-4 py-3 bg-gray-800 text-white hover:bg-gray-900 rounded-lg shadow-lg font-medium transition-colors"
      >
        <ArrowLeftIcon className="w-5 h-5" />
        <span>Back to search</span>
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
        className="fixed bottom-6 left-6 flex items-center gap-3 px-4 py-3 bg-teal-600 text-white rounded-lg shadow-lg hover:bg-teal-700 transition-colors font-medium"
      >
        <BookmarkIcon className="w-5 h-5" />
        <span>See your last {bookmarkCount} saved tracks</span>
      </button>
    )
  }

  // Show "View saved tracks" button when user has started session and has bookmarks
  if (hasStartedSession && bookmarkCount > 0) {
    return (
      <button
        onClick={onToggleView}
        className="fixed bottom-6 left-6 flex items-center gap-3 px-4 py-3 bg-teal-600 text-white hover:bg-teal-700 rounded-lg shadow-lg font-medium transition-colors"
      >
        <BookmarkIcon className="w-5 h-5" />
        <span>View {bookmarkCount} saved tracks</span>
      </button>
    )
  }

  return null
}

export default FloatingActionButton