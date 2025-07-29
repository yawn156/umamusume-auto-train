import pytesseract
from PIL import Image
import numpy as np
import os

# Configure Tesseract to use the custom trained data
tessdata_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tessdata')
os.environ['TESSDATA_PREFIX'] = tessdata_dir

# Try to find tesseract executable automatically
try:
    # On Windows, try common installation paths
    if os.name == 'nt':
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', ''))
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
except Exception:
    pass  # Fall back to system PATH

def extract_text(pil_img: Image.Image) -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Use Tesseract with custom configuration for better accuracy
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). '
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        return text.strip()
    except Exception as e:
        print(f"[WARNING] OCR extraction failed: {e}")
        return ""

def extract_number(pil_img: Image.Image) -> str:
    """Extract numbers from image using Tesseract OCR"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Use Tesseract with configuration optimized for numbers
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789 '
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        return text.strip()
    except Exception as e:
        print(f"[WARNING] Number extraction failed: {e}")
        return ""

def extract_turn_number(pil_img: Image.Image) -> str:
    """Extract turn numbers with specialized configuration for better digit recognition"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better digit recognition
        configs = [
            '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',  # Single word
            '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',  # Single line
            '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',  # Uniform block
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text and text.isdigit():
                return text
        
        # If no config worked, return the first non-empty result
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        print(f"[WARNING] Turn number extraction failed: {e}")
        return ""

def extract_mood_text(pil_img: Image.Image) -> str:
    """Extract mood text with specialized configuration for better text recognition"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better text recognition
        configs = [
            '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Single word
            '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Single line
            '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Uniform block
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        print(f"[WARNING] Mood text extraction failed: {e}")
        return ""

def extract_failure_text(pil_img: Image.Image) -> str:
    """Extract failure rate text with specialized configuration"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better text recognition
        configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). ',  # Uniform block
            '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). ',  # Single line
            '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). ',  # Single word
            '--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). ',  # Raw line
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        print(f"[WARNING] Failure text extraction failed: {e}")
        return ""
