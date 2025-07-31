import { useState, useEffect } from 'react'
import { apiService } from '../services/apiService'

export function useSearch() {
  const [jobId, setJobId] = useState(null)
  const [results, setResults] = useState(null)
  const [meta, setMeta] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loadingStep, setLoadingStep] = useState(null)
  const [chatHistory, setChatHistory] = useState([])
  const [conversationHistory, setConversationHistory] = useState(null)
  const [userResponseCount, setUserResponseCount] = useState(0)

  const startSearch = async (queryText) => {
    // Check 10 user responses limit
    if (userResponseCount >= 10) {
      setError("You've reached the maximum of 10 refinements. Please start a new search session.")
      return
    }

    setIsLoading(true)
    setError(null)
    setResults(null)
    setMeta(null)
    setLoadingStep({ message: "Gathering initial results", step: "starting", animated: true })

    // Increment user response count
    setUserResponseCount(prev => prev + 1)

    // Add user message to chat history
    setChatHistory(prev => [...prev, {
      content: queryText,
      isUser: true,
      timestamp: new Date().toISOString()
    }])

    try {
      const data = await apiService.createSearch(queryText, conversationHistory)
      setJobId(data.job_id)
    } catch (err) {
      setError(err.message)
      setIsLoading(false)
    }
  }

  // Polling effect
  useEffect(() => {
    if (!jobId) return

    const pollResults = async () => {
      try {
        const data = await apiService.getJobStatus(jobId)
        
        if (data.status === 'done') {
          setResults(data.results?.tracks || [])
          setMeta({
            llm_message: data.results?.llm_message,
            llm_reflection: data.results?.llm_reflection,
            result_count: data.results?.result_count,
          })
          
          // Add bot response to chat history
          const botMessage = data.results?.llm_message || 
            (data.results?.result_count === 0 ? "No results found. Please try widening your search." : null)
          
          if (botMessage) {
            setChatHistory(prev => [...prev, {
              content: botMessage,
              isUser: false,
              timestamp: new Date().toISOString()
            }])
          }
          
          // Update conversation history for future requests
          if (data.conversation_history) {
            setConversationHistory(data.conversation_history)
          }
          
          setIsLoading(false)
          setLoadingStep(null)
          setJobId(null)
        } else if (data.status === 'error') {
          setError(data.error_message || 'Search failed')
          setIsLoading(false)
          setLoadingStep(null)
          setJobId(null)
        } else if (data.status === 'running' || data.status === 'queued') {
          // Update loading step based on conversation history
          const history = data.conversation_history
          if (history && history.steps && history.steps.length > 0) {
            // Find the most recent step that's actively being processed
            // Look for steps added after the job started processing
            const latestStep = history.steps[history.steps.length - 1]
            const stepNumber = latestStep.step_number
            const resultCount = latestStep.result_count
            const userMessage = latestStep.user_message
            
            // Check if this step is recent (within the current job processing)
            // If the step timestamp is very recent, it's likely part of current processing
            const stepTime = new Date(latestStep.timestamp)
            const jobStartTime = new Date(data.started_at)
            const isRecentStep = stepTime >= jobStartTime
            
            if (isRecentStep) {
              if (latestStep.step_type === 'initial') {
                setLoadingStep({
                  message: `Refinement 1: I found ${resultCount} results. ${userMessage} Refining further`,
                  step: 'initial_complete',
                  animated: true
                })
              } else if (latestStep.step_type === 'auto_refine' || latestStep.step_type === 'user_refine') {
                // Count actual refinement steps (not including initial)
                const refinementNumber = stepNumber;
                setLoadingStep({
                  message: `Refinement ${refinementNumber}: Found ${resultCount} results. ${userMessage} Refining further`,
                  step: `refine_${stepNumber}`,
                  animated: true
                })
              }
            } else {
              // Old step, show generic loading
              setLoadingStep({ message: "Processing your request", step: "processing", animated: true })
            }
          } else {
            // No steps yet, still gathering initial results
            setLoadingStep({ message: "Gathering initial results", step: "starting", animated: true })
          }
        }
      } catch (err) {
        setError(err.message)
        setIsLoading(false)
        setLoadingStep(null)
        setJobId(null)
      }
    }

    const interval = setInterval(pollResults, 2000) // Poll every 2 seconds
    
    return () => clearInterval(interval)
  }, [jobId])

  const resetSession = () => {
    setResults(null)
    setMeta(null)
    setError(null)
    setLoadingStep(null)
    setChatHistory([])
    setConversationHistory(null)
    setUserResponseCount(0)
  }

  return {
    startSearch,
    resetSession,
    results,
    meta,
    isLoading,
    error,
    loadingStep,
    chatHistory,
    userResponseCount
  }
}