import AnimatedDots from './AnimatedDots'

function LoadingMessage({ message, animated = false }) {
  if (!animated) {
    return <span>{message}</span>
  }

  // Add animated dots to loading messages
  if (message.endsWith('further') || message.endsWith('results') || message.endsWith('request')) {
    return (
      <span>
        {message}<AnimatedDots />
      </span>
    )
  }
  
  return <span>{message}</span>
}

export default LoadingMessage