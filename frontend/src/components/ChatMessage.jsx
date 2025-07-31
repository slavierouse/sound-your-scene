import ChainOfThought from './ChainOfThought'

function ChatMessage({ message, isUser, chainOfThoughtSteps, isLoading, imageData }) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 sm:mb-4`}>
      <div className={`max-w-full sm:max-w-2xl px-3 sm:px-4 py-2 sm:py-3 rounded-lg text-sm sm:text-base ${
        isUser 
          ? 'bg-teal-600 text-white sm:ml-12' 
          : 'bg-white border border-gray-200 text-gray-900 sm:mr-12'
      }`}>
        {/* Show image for user messages if available */}
        {isUser && imageData && (
          <div className="mb-3">
            <img
              src={imageData.previewUrl}
              alt="Scene image"
              className="w-32 h-32 object-cover rounded-lg border border-gray-300 opacity-90"
            />
          </div>
        )}
        <p className="whitespace-pre-wrap">{message}</p>
        {/* Show chain of thought only for bot messages when not loading */}
        {!isUser && (
          <ChainOfThought 
            steps={chainOfThoughtSteps} 
            isLoading={isLoading}
          />
        )}
      </div>
    </div>
  )
}

export default ChatMessage