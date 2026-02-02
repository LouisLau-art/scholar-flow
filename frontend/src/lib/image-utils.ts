/**
 * Compresses and resizes an image file.
 * 
 * @param file - The input image file
 * @param maxWidth - Maximum width (default: 800px)
 * @param maxHeight - Maximum height (default: 800px)
 * @param quality - JPEG/WEBP quality (0 to 1, default: 0.8)
 * @returns Promise<File> - The compressed file
 */
export async function compressImage(
  file: File,
  maxWidth = 800,
  maxHeight = 800,
  quality = 0.8
): Promise<File> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsDataURL(file)
    
    reader.onload = (event) => {
      const img = new Image()
      img.src = event.target?.result as string
      
      img.onload = () => {
        let width = img.width
        let height = img.height
        
        // Calculate new dimensions
        if (width > height) {
          if (width > maxWidth) {
            height = Math.round((height * maxWidth) / width)
            width = maxWidth
          }
        } else {
          if (height > maxHeight) {
            width = Math.round((width * maxHeight) / height)
            height = maxHeight
          }
        }
        
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Failed to get canvas context'))
          return
        }
        
        ctx.drawImage(img, 0, 0, width, height)
        
        // Convert to Blob (prefer WebP if supported, fallback to JPEG)
        // Note: Using 'image/jpeg' for broader compatibility if needed, 
        // but modern browsers support 'image/webp' well.
        // Let's stick to JPEG for maximum safety or WebP for size.
        // Given the requirement "JPG, PNG or WEBP", let's try to output a standardized JPEG or WEBP.
        // Let's use JPEG for now as it's universally robust for Supabase storage preview.
        const mimeType = 'image/jpeg' 
        
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error('Canvas to Blob failed'))
              return
            }
            // Create new File object
            const newFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + ".jpg", {
              type: mimeType,
              lastModified: Date.now(),
            })
            resolve(newFile)
          },
          mimeType,
          quality
        )
      }
      
      img.onerror = (error) => reject(error)
    }
    
    reader.onerror = (error) => reject(error)
  })
}
