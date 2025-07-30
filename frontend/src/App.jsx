import { useState, useEffect } from 'react'
import SearchForm from './components/SearchForm'
import ResultsList from './components/ResultsList'
import ChatHistory from './components/ChatHistory'
import LoadingMessage from './components/LoadingMessage'
import FloatingActionButton from './components/FloatingActionButton'
import { useSearch } from './hooks/useSearch'
import { bookmarkService } from './services/bookmarkService'

function App() {
  const [query, setQuery] = useState('')
  const [isViewingSaved, setIsViewingSaved] = useState(false)
  const [bookmarkCount, setBookmarkCount] = useState(0)
  const [bookmarkKey, setBookmarkKey] = useState(0)
  const [hasStartedSession, setHasStartedSession] = useState(false)
  const { startSearch, resetSession, results, meta, isLoading, error, loadingStep, chatHistory, userResponseCount } = useSearch()
  
  const hasResults = results && results.length > 0
  const hasSearched = meta !== null

  // Update bookmark count and key
  const updateBookmarkCount = () => {
    setBookmarkCount(bookmarkService.getBookmarkCount())
    setBookmarkKey(prev => prev + 1) // Increment to trigger re-render
  }

  useEffect(() => {
    updateBookmarkCount()
  }, [])

  // Handle new search - clear bookmarks, reset session, and return to search view
  const handleNewSearch = (queryText) => {
    bookmarkService.clearBookmarksOnNewQuery()
    setBookmarkCount(0)
    setIsViewingSaved(false)
    setHasStartedSession(true) // Mark that user has started a session
    resetSession()
    startSearch(queryText)
  }

  // Handle toggle between search and saved view
  const handleToggleView = () => {
    setIsViewingSaved(!isViewingSaved)
  }
  return (
    <div className="min-h-screen bg-light-cream font-sans">
      {/* Header */}
      <header className="pt-12 pl-12 pb-6">
        <h1 className="text-2xl font-medium text-gray-900 mb-2">
          What type of music are you looking for?
        </h1>
        <p className="text-gray-600">
          I can help you find music based on your mood, vibe, duration, era, genre, and more. Just tell me what you're looking for!
        </p>
      </header>

      {/* Main Content */}
      <main className="pl-12 pr-12">
        <div className="max-w-4xl">
          {/* Show search form if no conversation started or after results are shown */}
          {chatHistory.length === 0 && !isViewingSaved && (
            <SearchForm 
              query={query}
              setQuery={setQuery}
              onSubmit={handleNewSearch}
              isLoading={isLoading}
            />
          )}

          {/* Error Display */}
          {error && (
            <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 mb-3">{error}</p>
              {error.includes("maximum of 10 refinements") && (
                <button
                  onClick={() => {
                    resetSession()
                    setQuery('')
                    setHasStartedSession(false) // Reset session state
                  }}
                  className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium"
                >
                  Start New Session
                </button>
              )}
            </div>
          )}

          {/* Chat History - only show when not viewing saved tracks */}
          {!isViewingSaved && (
            <ChatHistory 
              chatHistory={chatHistory}
              isLoading={isLoading}
              loadingStep={loadingStep}
            />
          )}

          {/* Continue conversation form - shown after any search (results or empty) */}
          {hasSearched && !isViewingSaved && (
            <div className="mb-8">
              <SearchForm 
                query={query}
                setQuery={setQuery}
                onSubmit={(queryText) => {
                  setHasStartedSession(true) // Mark session as started for refinements too
                  startSearch(queryText)
                }}
                isLoading={isLoading}
                placeholder={hasResults 
                  ? "Ask me to refine the results, change the mood, or find something different..."
                  : "Try widening your search or asking for different genres, time periods, or moods..."
                }
                buttonText="Continue"
              />
            </div>
          )}

          {/* Results Display */}
          <ResultsList 
            results={isViewingSaved ? null : results} 
            meta={isViewingSaved ? null : meta}
            isViewingSaved={isViewingSaved}
            onBookmarkChange={updateBookmarkCount}
            onClearAll={() => setIsViewingSaved(false)}
            bookmarkKey={bookmarkKey}
          />
        </div>
      </main>

      {/* Floating Action Button */}
      <FloatingActionButton 
        bookmarkCount={bookmarkCount}
        isViewingSaved={isViewingSaved}
        onToggleView={handleToggleView}
        hasStartedSession={hasStartedSession}
      />
    </div>
  )
}

export default App