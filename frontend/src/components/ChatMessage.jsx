function ChatMessage({ message, isUser }) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-2xl px-4 py-3 rounded-lg ${
        isUser 
          ? 'bg-teal-600 text-white ml-12' 
          : 'bg-white border border-gray-200 text-gray-900 mr-12'
      }`}>
        <p className="whitespace-pre-wrap">{message}</p>
      </div>
    </div>
  )
}

export default ChatMessage