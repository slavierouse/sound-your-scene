import { ArrowUpTrayIcon, ArrowLeftIcon, EnvelopeIcon, LinkIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import { APP_CONFIG } from '../config/constants'
import { apiService } from '../services/apiService'

function FloatingActionButtonExport({ bookmarkCount, activePlaylistId }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isEmailMode, setIsEmailMode] = useState(false)
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [isLinkCopied, setIsLinkCopied] = useState(false)
  const [error, setError] = useState('')

  // Success state
  if (isSuccess) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center px-3 sm:px-4 py-2 sm:py-3 bg-green-600 text-white rounded-lg shadow-lg text-sm sm:text-base font-medium">
        Success
      </div>
    )
  }

  // Link copied success state
  if (isLinkCopied) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center px-3 sm:px-4 py-2 sm:py-3 bg-green-600 text-white rounded-lg shadow-lg text-sm sm:text-base font-medium">
        Link copied to clipboard
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center px-3 sm:px-4 py-2 sm:py-3 bg-red-600 text-white rounded-lg shadow-lg text-sm sm:text-base font-medium max-w-xs">
        <span className="truncate">{error}</span>
        <button
          onClick={() => setError('')}
          className="ml-2 text-white hover:text-red-200"
        >
          ×
        </button>
      </div>
    )
  }

  // Only show when there are saved tracks
  if (bookmarkCount === 0) {
    return null
  }

  // Email input mode
  if (isEmailMode) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center bg-teal-600 text-white rounded-lg shadow-lg text-sm sm:text-base font-medium">
        {/* Back button */}
        <button
          onClick={() => {
            setIsEmailMode(false)
            setIsExpanded(false)
            setEmail('')
            setError('')
          }}
          className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 hover:bg-teal-700 transition-colors rounded-l-lg"
        >
          <ArrowLeftIcon className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>

        {/* Separator */}
        <span className="text-teal-400">|</span>

        {/* Email input */}
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="enter your email"
          className="px-3 py-2 text-sm sm:text-base bg-white text-gray-900 rounded border-0 focus:ring-2 focus:ring-teal-500 focus:outline-none min-w-[120px] sm:min-w-[160px]"
        />

        {/* Send button */}
        <button
          onClick={async () => {
            if (!activePlaylistId) {
              setError('No playlist available to email')
              return
            }

            setIsSubmitting(true)
            setError('')
            
            try {
              await apiService.emailPlaylist(activePlaylistId, email)
              setIsSubmitting(false)
              setIsSuccess(true)
              // Show success for 3 seconds, then revert to default
              setTimeout(() => {
                setIsSuccess(false)
                setIsEmailMode(false)
                setIsExpanded(false)
                setEmail('')
              }, 3000)
            } catch (error) {
              setIsSubmitting(false)
              setError(error.message || 'Failed to send email')
            }
          }}
          disabled={!email.trim() || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/) || isSubmitting}
          className="px-3 sm:px-4 py-2 sm:py-3 hover:bg-teal-700 transition-colors rounded-r-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Sending...' : 'Send'}
        </button>
      </div>
    )
  }

  // Expanded state with three panels
  if (isExpanded) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center bg-teal-600 text-white rounded-lg shadow-lg text-sm sm:text-base font-medium">
        {/* Back button */}
        <button
          onClick={() => {
            setIsExpanded(false)
            setError('')
          }}
          className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 hover:bg-teal-700 transition-colors rounded-l-lg"
        >
          <ArrowLeftIcon className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>

        {/* Separator */}
        <span className="text-teal-400">|</span>

        {/* Email button */}
        <button
          onClick={() => setIsEmailMode(true)}
          className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 hover:bg-teal-700 transition-colors"
        >
          <EnvelopeIcon className="w-4 h-4 sm:w-5 sm:h-5" />
          <span className="hidden sm:inline">Email</span>
        </button>

        {/* Separator */}
        <span className="text-teal-400">|</span>

        {/* Copy link button */}
        <button
          onClick={async () => {
            const playlistUrl = activePlaylistId 
              ? `${APP_CONFIG.DOMAIN}/playlist/${activePlaylistId}`
              : "No playlist available"
            
            try {
              await navigator.clipboard.writeText(playlistUrl)
              setIsLinkCopied(true)
              // Show success for 3 seconds, then revert to default
              setTimeout(() => {
                setIsLinkCopied(false)
                setIsExpanded(false)
              }, 3000)
            } catch (err) {
              console.error('Failed to copy link:', err)
              // Fallback for older browsers
              const textArea = document.createElement('textarea')
              textArea.value = playlistUrl
              document.body.appendChild(textArea)
              textArea.select()
              document.execCommand('copy')
              document.body.removeChild(textArea)
              setIsLinkCopied(true)
              setTimeout(() => {
                setIsLinkCopied(false)
                setIsExpanded(false)
              }, 3000)
            }
          }}
          className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 hover:bg-teal-700 transition-colors rounded-r-lg"
        >
          <LinkIcon className="w-4 h-4 sm:w-5 sm:h-5" />
          <span className="hidden sm:inline">Copy link</span>
        </button>
      </div>
    )
  }

  // Default collapsed state
  return (
    <button
      onClick={() => setIsExpanded(true)}
      className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 bg-teal-600 text-white hover:bg-teal-700 rounded-lg shadow-lg text-sm sm:text-base font-medium transition-colors"
    >
      <ArrowUpTrayIcon className="w-4 h-4 sm:w-5 sm:h-5" />
      <span className="hidden sm:inline">Export {bookmarkCount} saved tracks</span>
      <span className="sm:hidden">Export ({bookmarkCount})</span>
    </button>
  )
}

export default FloatingActionButtonExport 