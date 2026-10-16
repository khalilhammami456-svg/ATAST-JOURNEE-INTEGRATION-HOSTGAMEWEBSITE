const MAX_FILE_SIZE = 8 * 1024 * 1024;

/**
 * Reads an image file and downsizes it to a small square data URL,
 * so logos and avatars stay light enough for localStorage.
 */
export function readImageAsDataUrl(file, size = 256) {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      reject(new Error("Ce fichier n'est pas une image."));
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      reject(new Error("L'image est trop lourde (8 Mo maximum)."));
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Impossible de lire l'image."));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("Format d'image non reconnu."));
      image.onload = () => {
        const canvas = document.createElement('canvas');
        const ratio = Math.min(1, size / Math.max(image.width, image.height));
        canvas.width = Math.round(image.width * ratio);
        canvas.height = Math.round(image.height * ratio);
        canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/png'));
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}
