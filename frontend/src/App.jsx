import { useState } from 'react'
import SearchForm from './components/SearchForm'
import ResultsList from './components/ResultsList'
import { useSearch } from './hooks/useSearch'

function App() {
  const [query, setQuery] = useState('')
  const { startSearch, results, meta, isLoading, error, loadingStep } = useSearch()
  return (
    <div className="min-h-screen bg-light-cream font-sans">
      {/* Header */}
      <header className="pt-12 pl-12 pb-6">
        <h1 className="text-2xl font-medium text-gray-900 mb-2">
          What type of music are you looking for?
        </h1>
        <p className="text-gray-600">
          Find music according to the mood and vibe
        </p>
      </header>

      {/* Main Content */}
      <main className="pl-12 pr-12">
        <div className="max-w-3xl">
          <SearchForm 
            query={query}
            setQuery={setQuery}
            onSubmit={startSearch}
            isLoading={isLoading}
          />

          {/* Error Display */}
          {error && (
            <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="mb-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-700">
                {loadingStep ? loadingStep.message : "Finding music that matches your vibe..."}
              </p>
            </div>
          )}

          <ResultsList results={results} meta={meta} />
        </div>
      </main>
    </div>
  )
}

export default App