import TrackView from './TrackView'

function ResultsList({ results, meta }) {
  if (!results && !meta) return null

  return (
    <>
      {/* Meta Information */}
      {meta && meta.result_count && (
        <div className="mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Found {meta.result_count} results
          </h3>
          {meta.llm_message && (
            <p className="text-gray-700 mb-4">{meta.llm_message}</p>
          )}
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div className="mb-8">
          <div className="space-y-4">
            {results.map((track, index) => (
              <TrackView key={track.spotify_track_id || index} track={track} index={index} />
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export default ResultsList