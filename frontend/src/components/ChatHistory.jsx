import { useState } from 'react'
import ChatMessage from './ChatMessage'
import LoadingMessage from './LoadingMessage'

function ChatHistory({ chatHistory, isLoading, loadingStep, conversationHistory }) {
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
        {visibleMessages.map((message, index) => {
          // For bot messages, find the corresponding conversation steps
          let chainOfThoughtSteps = []
          if (!message.isUser && conversationHistory && conversationHistory.steps) {
            // Calculate which chat turn this bot message represents
            const messageIndex = showAll ? index : index + (chatHistory.length - visibleMessages.length)
            const chatTurnIndex = Math.floor(messageIndex / 2) // 0-based index of which user query this responds to
            
            // Get the user message that corresponds to this chat turn
            // When showAll is false, we need to map from visible message index to actual chat history index
            const actualMessageIndex = showAll ? index : index + (chatHistory.length - visibleMessages.length)
            const actualChatTurnIndex = Math.floor(actualMessageIndex / 2)
            const actualUserMessageIndex = actualChatTurnIndex * 2 // User messages are at even indices
            if (actualUserMessageIndex >= 0 && actualUserMessageIndex < chatHistory.length) {
              const correspondingUserMessage = chatHistory[actualUserMessageIndex]
              
              if (correspondingUserMessage && correspondingUserMessage.isUser) {
                const userQuery = correspondingUserMessage.content.trim()
                
                // Find all steps that belong to this chat turn
                const allSteps = conversationHistory.steps
                const stepsForThisTurn = []
                
                // Find the step that matches this user query
                let foundMatchingStep = false
                for (let i = 0; i < allSteps.length; i++) {
                  const step = allSteps[i]
                  
                  // Check if this step's user_input matches our user query
                  if (step.user_input && step.user_input.trim() === userQuery) {
                    stepsForThisTurn.push(step)
                    foundMatchingStep = true
                    
                    // Add any subsequent auto_refine steps
                    for (let j = i + 1; j < allSteps.length; j++) {
                      const nextStep = allSteps[j]
                      if (nextStep.step_type === 'auto_refine') {
                        stepsForThisTurn.push(nextStep)
                      } else {
                        // Stop when we hit a non-auto_refine step (next user turn)
                        break
                      }
                    }
                    break
                  }
                }
                
                chainOfThoughtSteps = stepsForThisTurn
              }
            }
          }
          
          return (
            <ChatMessage
              key={showAll ? index : index + (chatHistory.length - visibleMessages.length)}
              message={message.content}
              isUser={message.isUser}
              chainOfThoughtSteps={chainOfThoughtSteps}
              isLoading={isLoading}
              imageData={message.imageData}
            />
          )
        })}
        
        {/* Loading message as bot response */}
        {isLoading && loadingStep && (
          <div className={`flex justify-start mb-3 sm:mb-4`}>
            <div className={`max-w-full sm:max-w-2xl px-3 sm:px-4 py-2 sm:py-3 rounded-lg bg-white border border-gray-200 text-gray-900 sm:mr-12 text-sm sm:text-base`}>
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