import { useState, useEffect } from 'react'
import { apiService } from '../services/apiService'

export function useSearch() {
  const [jobId, setJobId] = useState(null)
  const [results, setResults] = useState(null)
  const [meta, setMeta] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loadingStep, setLoadingStep] = useState(null)

  const startSearch = async (queryText) => {
    setIsLoading(true)
    setError(null)
    setResults(null)
    setMeta(null)
    setLoadingStep({ message: "Gathering initial results...", step: "starting" })

    try {
      const data = await apiService.createSearch(queryText)
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
            const latestStep = history.steps[history.steps.length - 1]
            const stepNumber = latestStep.step_number
            const resultCount = latestStep.result_count
            const userMessage = latestStep.user_message
            
            if (latestStep.step_type === 'initial') {
              setLoadingStep({
                message: `I found ${resultCount} results. ${userMessage}. Refining further...`,
                step: 'initial_complete'
              })
            } else if (latestStep.step_type === 'auto_refine') {
              setLoadingStep({
                message: `Refinement ${stepNumber}: Found ${resultCount} results. ${userMessage}. Refining further...`,
                step: `auto_refine_${stepNumber}`
              })
            }
          } else {
            // No steps yet, still gathering initial results
            setLoadingStep({ message: "Gathering initial results...", step: "starting" })
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

  return {
    startSearch,
    results,
    meta,
    isLoading,
    error,
    loadingStep
  }
}