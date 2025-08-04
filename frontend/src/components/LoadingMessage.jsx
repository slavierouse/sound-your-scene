import AnimatedDots from './AnimatedDots'

function LoadingMessage({ message, animated = false }) {
  if (!animated) {
    return <span>{message}</span>
  }

  // Add animated dots to loading messages with timing note
  if (message.endsWith('further') || message.endsWith('results') || message.endsWith('request')) {
    return (
      <span>
        {message} (up to 1-2 minutes)<AnimatedDots />
      </span>
    )
  }
  
  return <span>{message}</span>
}

export default LoadingMessage