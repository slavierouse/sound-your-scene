import { useState } from 'react'
import ChatMessage from './ChatMessage'
import LoadingMessage from './LoadingMessage'

function ChatHistory({ chatHistory, isLoading, loadingStep }) {
  const [showAll, setShowAll] = useState(false)
  
  if (!chatHistory || chatHistory.length === 0) return null

  // Show last 2 messages by default, but account for loading state
  // When loading, we want: [last user message, loading message]
  // When not loading, we want: [last user message, last bot response]
  const messagesToShow = isLoading ? 1 : 2 // Show 1 message when loading (+ loading state), 2 when not loading
  const visibleMessages = showAll ? chatHistory : chatHistory.slice(-messagesToShow)
  const hasHiddenMessages = chatHistory.length > messagesToShow

  return (
    <div className="mb-8">
      <div className="space-y-0">
        {/* Show previous messages button */}
        {hasHiddenMessages && !showAll && (
          <div className="mb-4 text-center">
            <button
              onClick={() => setShowAll(true)}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Show previous messages ({chatHistory.length - messagesToShow} hidden)
            </button>
          </div>
        )}

        {/* Collapse button when showing all */}
        {showAll && hasHiddenMessages && (
          <div className="mb-4 text-center">
            <button
              onClick={() => setShowAll(false)}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Hide previous messages
            </button>
          </div>
        )}

        {/* Chat messages */}
        {visibleMessages.map((message, index) => (
          <ChatMessage
            key={showAll ? index : index + (chatHistory.length - visibleMessages.length)}
            message={message.content}
            isUser={message.isUser}
          />
        ))}
        
        {/* Loading message as bot response */}
        {isLoading && loadingStep && (
          <div className={`flex justify-start mb-4`}>
            <div className={`max-w-2xl px-4 py-3 rounded-lg bg-white border border-gray-200 text-gray-900 mr-12`}>
              <p className="whitespace-pre-wrap">
                <LoadingMessage 
                  message={loadingStep.message} 
                  animated={loadingStep.animated} 
                />
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatHistory