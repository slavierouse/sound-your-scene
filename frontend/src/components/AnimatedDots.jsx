import { useState, useEffect } from 'react'

function AnimatedDots() {
  const [dots, setDots] = useState('.')
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '.') return '..'
        if (prev === '..') return '...'
        return '.'
      })
    }, 500) // Change every 500ms
    
    return () => clearInterval(interval)
  }, [])
  
  return <span>{dots}</span>
}

export default AnimatedDots