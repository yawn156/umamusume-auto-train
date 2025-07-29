from PIL import Image, ImageEnhance
import mss
import numpy as np

def enhanced_screenshot(region=(0, 0, 1920, 1080)) -> Image.Image:
  with mss.mss() as sct:
    monitor = {
      "left": region[0],
      "top": region[1],
      "width": region[2],
      "height": region[3]
    }
    img = sct.grab(monitor)
    img_np = np.array(img)
    img_rgb = img_np[:, :, :3][:, :, ::-1]
    pil_img = Image.fromarray(img_rgb)

  pil_img = pil_img.resize((pil_img.width * 2, pil_img.height * 2), Image.BICUBIC)
  pil_img = pil_img.convert("L")
  pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)

  return pil_img

def capture_region(region=(0, 0, 1920, 1080)) -> Image.Image:
  with mss.mss() as sct:
    monitor = {
      "left": region[0],
      "top": region[1],
      "width": region[2],
      "height": region[3]
    }
    img = sct.grab(monitor)
    img_np = np.array(img)
    img_rgb = img_np[:, :, :3][:, :, ::-1]
    return Image.fromarray(img_rgb)

def enhanced_screenshot_for_failure(region=(0, 0, 1920, 1080)) -> Image.Image:
  """Enhanced screenshot specifically optimized for white and yellow text on orange background"""
  with mss.mss() as sct:
    monitor = {
      "left": region[0],
      "top": region[1],
      "width": region[2],
      "height": region[3]
    }
    img = sct.grab(monitor)
    img_np = np.array(img)
    img_rgb = img_np[:, :, :3][:, :, ::-1]
    pil_img = Image.fromarray(img_rgb)

  # Resize for better OCR
  pil_img = pil_img.resize((pil_img.width * 2, pil_img.height * 2), Image.BICUBIC)
  
  # Convert to RGB to work with color channels
  pil_img = pil_img.convert("RGB")
  
  # Convert to numpy for color processing
  img_np = np.array(pil_img)
  
  # Define orange color range (RGB) - for background
  # Orange background typically has high red, medium green, low blue
  orange_mask = (
    (img_np[:, :, 0] > 150) &  # High red
    (img_np[:, :, 1] > 80) &   # Medium green  
    (img_np[:, :, 2] < 100)    # Low blue
  )
  
  # Define white text range (RGB) - for "Failure" text
  white_mask = (
    (img_np[:, :, 0] > 200) &  # High red
    (img_np[:, :, 1] > 200) &  # High green
    (img_np[:, :, 2] > 200)    # High blue
  )
  
  # Define yellow text range (RGB) - for failure rate percentages
  # Yellow: (255, 210, 17) - high red, high green, low blue
  # Using more permissive thresholds to catch yellow text
  yellow_mask = (
    (img_np[:, :, 0] > 190) &  # High red
    (img_np[:, :, 1] > 140) &  # High green
    (img_np[:, :, 2] < 90)     # Low blue
  )
  
  # Create a new image: black background, white and yellow text
  result = np.zeros_like(img_np)
  
  # Set white text (for "Failure")
  result[white_mask] = [255, 255, 255]
  
  # Set yellow text (for percentages) - convert to white for OCR
  result[yellow_mask] = [255, 255, 255]
  
  # Set orange background to black
  result[orange_mask] = [0, 0, 0]
  
  # Convert back to PIL
  pil_img = Image.fromarray(result)
  
  # Convert to grayscale for OCR
  pil_img = pil_img.convert("L")
  
  # Enhance contrast for better OCR
  pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)
  
  return pil_img