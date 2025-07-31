import { useState } from 'react'

function ChainOfThought({ steps, isLoading }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Always show button (don't hide based on steps availability)
  // Only hide while actively loading
  if (isLoading) {
    return null
  }

  // Show steps in reverse chronological order (most recent first)
  const sortedSteps = steps && steps.length > 0 ? 
    [...steps].sort((a, b) => b.step_number - a.step_number) : []

  return (
    <div className="mt-3">
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        {isExpanded ? 'Hide chain of thought' : 'Show chain of thought'}
      </button>

      {/* Chain of Thought Content */}
      {isExpanded && (
        <div className="mt-3 space-y-3">
          {sortedSteps.length > 0 ? (
            sortedSteps.map((step, index) => {
              const isLatestStep = index === 0 // First in sorted array (most recent)
              
              return (
                <div key={step.step_number} className="border-l-2 border-gray-200 pl-3">
                  <div className="text-sm text-gray-700 font-medium mb-1">
                    {step.step_type === 'initial' ? 'Initial Search' : 
                     step.step_type === 'auto_refine' ? `Auto Refinement ${step.step_number}` :
                     step.step_type === 'user_refine' ? `User Refinement ${step.step_number}` :
                     `Step ${step.step_number}`}
                  </div>
                  
                  {/* For latest step, don't show user message (it's in chat bubble above) */}
                  {/* For previous steps, show user message since it's not visible in current chat */}
                  {!isLatestStep && (
                    <div className="text-sm text-gray-600 mb-2">
                      I found {step.result_count} results. {step.user_message}
                    </div>
                  )}
                  
                  {/* Always show rationale if available */}
                  {(step.reflection || step.rationale) && (
                    <div className="text-xs text-gray-500">
                      {step.reflection || step.rationale}
                    </div>
                  )}
                </div>
              )
            })
          ) : (
            <div className="text-xs text-gray-500 italic">
              Chain of thought not available for this message.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ChainOfThought