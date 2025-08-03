// Mapping of example images to their asset files
const EXAMPLE_IMAGES = {
  'period-drama': () => import('../assets/bridg-preview.png'),
  'christmas-special': () => import('../assets/charlie-preview.webp'),
  'dance-party': () => import('../assets/couple-preview.jpg'),
  'brooding-electro': () => import('../assets/dark-preview.jpg'),
  'og-rap': () => import('../assets/comp-preview.jpg')
}

/**
 * Convert a file or blob to base64
 */
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      // Remove the data:image/...;base64, prefix to get just the base64 data
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/**
 * Load an example image and convert it to the format expected by the app
 */
export const loadExampleImage = async (imageKey) => {
  try {
    if (!EXAMPLE_IMAGES[imageKey]) {
      throw new Error(`Unknown image key: ${imageKey}`)
    }

    // Import the image module
    const imageModule = await EXAMPLE_IMAGES[imageKey]()
    const imageUrl = imageModule.default

    // Fetch the image as a blob
    const response = await fetch(imageUrl)
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.statusText}`)
    }
    
    const blob = await response.blob()
    
    // Convert to base64
    const base64Data = await fileToBase64(blob)
    
    // Create a preview URL (same as the imported URL since it's already optimized by Vite)
    const previewUrl = imageUrl
    
    // Create a file-like object for compatibility
    const fileName = imageUrl.split('/').pop() || 'example-image'
    
    return {
      base64Data,
      tempFileId: `example-${imageKey}-${Date.now()}`,
      previewUrl,
      originalFile: {
        name: fileName,
        type: blob.type,
        size: blob.size
      },
      isExample: true // Flag to identify this as an example image
    }
  } catch (error) {
    console.error('Failed to load example image:', error)
    throw error
  }
}

/**
 * Get the image key for a given example query
 */
export const getImageKeyForExample = (exampleIndex) => {
  const imageKeys = [
    'period-drama',      // 0: Period drama
    'og-rap',           // 1: OG Rap  
    'dance-party',      // 2: Dance party
    'brooding-electro', // 3: Brooding electro
    'christmas-special' // 4: Christmas special
  ]
  
  return imageKeys[exampleIndex] || null
}