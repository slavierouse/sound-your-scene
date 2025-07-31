import { useState, useEffect } from 'react'

const examples = [
  {
    emoji: '👑',
    shorthand: 'Period drama',
    query: 'Music for a period drama set in England'
  },
  {
    emoji: '📼',
    shorthand: 'OG Rap',
    query: 'OG rap anthems, early 1990s, explicit lyrics'
  },
  {
    emoji: '🪩',
    shorthand: 'Dance party',
    query: 'Millenial nostalgia dance party hits'
  },
  {
    emoji: '🧛',
    shorthand: 'Brooding electro',
    query: 'Extremely negative, brooding, unhappy electronic music'
  },
  {
    emoji: '🎅',
    shorthand: 'Christmas special',
    query: 'Family friendly music for a christmas special TV episode'
  }
]

function Examples({ query, setQuery }) {
  const [activeTab, setActiveTab] = useState(null)

  // Check if current query matches any example
  useEffect(() => {
    const matchingIndex = examples.findIndex(example => example.query === query)
    setActiveTab(matchingIndex >= 0 ? matchingIndex : null)
  }, [query])

  const handleTabClick = (index) => {
    setActiveTab(index)
    setQuery(examples[index].query)
  }

  return (
    <div className="mb-6">
      {/* Examples section */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mb-12">
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap min-w-[80px]">
          Examples
        </span>
        <div className="flex flex-wrap gap-2">
          {examples.map((example, index) => (
            <button
              key={index}
              onClick={() => handleTabClick(index)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors text-sm ${
                activeTab === index
                  ? 'bg-teal-50 border-teal-300 text-teal-700'
                  : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300'
              }`}
            >
              <span className="text-base">{example.emoji}</span>
              <div className="w-px h-3 bg-gray-300"></div>
              <span className="font-medium">{example.shorthand}</span>
            </button>
          ))}
        </div>
      </div>

      {/* About section */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 mb-12">
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap min-w-[80px]">
          About
        </span>
        <div className="text-sm text-gray-600 leading-relaxed">
          This chatbot uses audio analysis of songs so you can search them by vibe. 
          You can use a mood ("sad"), a purpose ("dancing"), a genre ("hip hop"), an era ("80s"), and even specific ranges for BPM (e.g. 90-120) and duration (e.g. "2-4 minutes"). 
          You can add an image to help the bot understand the scene even better. 
          This should be useful for finding music choices for a movie, TV show, or video game soundtrack.
        </div>
      </div>

      {/* Tech section */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 mb-12">
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap min-w-[80px]">
          Tech
        </span>
        <div className="text-sm text-gray-600 leading-relaxed">
          This demo relies on an 
          <a className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" href="https://www.kaggle.com/datasets/salvatorerastelli/spotify-and-youtube" target="_blank" rel="noopener noreferrer"> open source dataset </a> 
          of about 18,000 songs from Youtube that were matched to their Spotify track ID, enriched with more metadata from Spotify, including audio analysis features. 
          An LLM agent built leveraging the 
          <a className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" href="https://ai.google.dev/" target="_blank" rel="noopener noreferrer"> Gemini API </a>
          ingests the user's query and converts it to a set of filters and weights that are applied to the dataset. The LLM queries the data iteratively to refine the results, both autonomously and with user input. 
          This was initially built as a Python Notebook, and converted to this demo with the support of Claude Code and Cursor.
        </div>
      </div>

      {/* Elsewhere section */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 mb-12">
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap min-w-[80px]">
          Elsewhere
        </span>
        <div className="text-sm text-gray-600 leading-relaxed">
          Surprisingly, Spotify's own search does not honor queries of these sorts. 
          The only publicly available alternative I've found that works with open text search is <a href="https://cyanite.ai/" className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" target="_blank" rel="noopener noreferrer">Cyanite.ai</a>. 
          I searched music related subreddits and 
          <a href="https://www.reddit.com/r/LetsTalkMusic/comments/cak0ib/how_do_yall_find_music_to_fit_into_certain_vibes/" className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" target="_blank" rel="noopener noreferrer"> found </a>
          <a href="https://www.reddit.com/r/LetsTalkMusic/comments/mqdx4i/whats_the_best_way_to_discover_new_music_and_bands/" className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" target="_blank" rel="noopener noreferrer">a </a>
          <a href="https://www.reddit.com/r/LetsTalkMusic/comments/1h005d3/what_music_do_you_turn_to_based_on_your_mood_and/" className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" target="_blank" rel="noopener noreferrer">few </a> 
          <a href="https://www.reddit.com/r/LetsTalkMusic/comments/171obry/finding_music_by_moodtopictheme/" className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" target="_blank" rel="noopener noreferrer">threads </a>
             that detail user painpoints.
        </div>
      </div>

      {/* Feedback section */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4">
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap min-w-[80px]">
          Feedback
        </span>
        <div className="text-sm text-gray-600 leading-relaxed">
          Let me know if you have any feedback or suggestions <a className="text-blue-600 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50" href="https://forms.gle/vtFnqH4F8oLQVrxi7" target="_blank" rel="noopener noreferrer">here.</a>
        </div>
      </div>
    </div>
  )
}

export default Examples 