function TrackView({ track, index }) {
  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
            <h4 className="font-medium text-gray-900">{track.track}</h4>
          </div>
          <p className="text-gray-600 mb-3">{track.artist}</p>
          {track.spotify_artist_genres && (
            <p className="text-gray-600 mb-3">
              {track.spotify_artist_genres.split(',').map(genre => genre.trim()).join(', ')}
            </p>
          )}
          <div className="flex gap-3">
            {track.url_youtube && (
              <a 
                href={track.url_youtube} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-red-600 hover:text-red-700 text-sm font-medium"
              >
                YouTube
              </a>
            )}
            {track.spotify_url && (
              <a 
                href={track.spotify_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-green-600 hover:text-green-700 text-sm font-medium"
              >
                Spotify
              </a>
            )}
          </div>
          {track.url_youtube && (
            <div className="flex gap-3 mt-4">
              <iframe 
                width="280" height="160" 
                src={`https://www.youtube.com/embed/${track.url_youtube.replace('https://www.youtube.com/watch?v=', '')}`}
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerpolicy="strict-origin-when-cross-origin"
                allowfullscreen
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TrackView