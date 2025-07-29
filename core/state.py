import re

from PIL import Image, ImageEnhance
from utils.screenshot import capture_region, enhanced_screenshot, enhanced_screenshot_for_failure
from core.ocr import extract_text, extract_number, extract_turn_number, extract_mood_text, extract_failure_text
from core.recognizer import match_template

from utils.constants import SUPPORT_CARD_ICON_REGION, MOOD_REGION, TURN_REGION, FAILURE_REGION, YEAR_REGION, MOOD_LIST, CRITERIA_REGION

# Get Stat
def stat_state():
  stat_regions = {
    "spd": (310, 723, 55, 20),
    "sta": (405, 723, 55, 20),
    "pwr": (500, 723, 55, 20),
    "guts": (595, 723, 55, 20),
    "wit": (690, 723, 55, 20)
  }

  result = {}
  for stat, region in stat_regions.items():
    img = enhanced_screenshot(region)
    val = extract_number(img)
    digits = ''.join(filter(str.isdigit, val))
    result[stat] = int(digits) if digits.isdigit() else 0
  return result

# Check support card in each training
def check_support_card(threshold=0.8):
  SUPPORT_ICONS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png"
  }

  count_result = {}

  for key, icon_path in SUPPORT_ICONS.items():
    matches = match_template(icon_path, SUPPORT_CARD_ICON_REGION, threshold)
    count_result[key] = len(matches)

  return count_result

# Get failure chance (idk how to get energy value)
def check_failure():
  # Try up to 5 times to detect failure rate
  max_attempts = 5
  
  for attempt in range(1, max_attempts + 1):
    failure = enhanced_screenshot_for_failure(FAILURE_REGION)
    
    # First try specialized failure text extraction
    failure_text = extract_failure_text(failure)
    if not failure_text:
      # Fallback to general text extraction
      failure_text = extract_text(failure)

    # Check if "Failure" is in the text (with OCR variations)
    has_failure = "Failure" in failure_text or "Failwre" in failure_text or "Fail" in failure_text
    if has_failure:
      break
    
    # If this is not the last attempt, wait a bit before retrying
    if attempt < max_attempts:
      import time
      time.sleep(1)
  
  if not has_failure:
    return -1

  # Find the bounding box of "Failure" text using OCR data
  try:
    import pytesseract
    import numpy as np
    
    # Get OCR data with bounding boxes
    img_np = np.array(failure)
    ocr_data = pytesseract.image_to_data(img_np, output_type=pytesseract.Output.DICT, config='--oem 3 --psm 6')
    
    # Find the bounding box of "Failure"
    failure_bbox = None
    for i, text in enumerate(ocr_data['text']):
      if 'Failure' in text or 'Failwre' in text or 'Fail' in text:
        # Get the bounding box coordinates (relative to the failure region)
        x = ocr_data['left'][i]
        y = ocr_data['top'][i]
        w = ocr_data['width'][i]
        h = ocr_data['height'][i]
        failure_bbox = (x, y, w, h)
        break
    
    if failure_bbox:
      # Calculate the focused region: extend the failure bounding box down by 45 pixels
      x, y, w, h = failure_bbox
      
      # Create focused region: same width as "Failure", extend height down by 45 pixels
      focused_region = (x, y, w, h + 45)
      
      # Capture the focused region from the already captured failure region image
      # Convert (left, top, width, height) to (left, top, right, bottom) for PIL crop
      left, top, width, height = focused_region
      crop_coords = (left, top, left + width, top + height)
      percentage_img = failure.crop(crop_coords)
      
      # Try normal OCR first (up to 3 attempts)
      for ocr_attempt in range(3):
        # Extract text from the focused region
        percentage_text = extract_failure_text(percentage_img)
        if not percentage_text:
          percentage_text = extract_text(percentage_img)
        
        # Extract percentage from the focused text
        percentage_patterns = [
          r"(\d{1,3})\s*%",  # "29%", "29 %"
          r"(\d{1,3})",      # Just the number
        ]
        
        for pattern in percentage_patterns:
          match = re.search(pattern, percentage_text)
          if match:
            rate = int(match.group(1))
            # Validate reasonable range (0-100)
            if 0 <= rate <= 100:
              return rate
        
        # If no percentage found and this is the last OCR attempt, try yellow threshold
        if ocr_attempt == 2:  # After 3 failed attempts
          print("[INFO] Normal OCR failed, trying yellow threshold detection...")
          
          # Get the raw screenshot for yellow threshold processing
          import mss
          with mss.mss() as sct:
            monitor = {
              "left": FAILURE_REGION[0],
              "top": FAILURE_REGION[1],
              "width": FAILURE_REGION[2],
              "height": FAILURE_REGION[3]
            }
            raw_img = sct.grab(monitor)
            raw_np = np.array(raw_img)
            raw_rgb = raw_np[:, :, :3][:, :, ::-1]
            raw_pil = Image.fromarray(raw_rgb)
          
          # Resize and convert to RGB
          raw_pil = raw_pil.resize((raw_pil.width * 2, raw_pil.height * 2), Image.BICUBIC)
          raw_pil = raw_pil.convert("RGB")
          raw_np = np.array(raw_pil)
          
          # Apply yellow threshold (using the working "More permissive" threshold)
          yellow_mask = (
            (raw_np[:, :, 0] > 180) &  # High red
            (raw_np[:, :, 1] > 120) &  # High green
            (raw_np[:, :, 2] < 80)     # Low blue
          )
          
          # Create yellow-specialized image
          yellow_result = np.zeros_like(raw_np)
          yellow_result[yellow_mask] = [255, 255, 255]  # Yellow text -> white
          
          # Convert to PIL and process
          yellow_img = Image.fromarray(yellow_result)
          yellow_img = yellow_img.convert("L")
          yellow_img = ImageEnhance.Contrast(yellow_img).enhance(1.5)
          
          # Crop the same focused region from yellow image
          yellow_cropped = yellow_img.crop(crop_coords)
          
          # Try OCR on yellow-specialized image
          yellow_text = extract_failure_text(yellow_cropped)
          if not yellow_text:
            yellow_text = extract_text(yellow_cropped)
          
          # Extract percentage from yellow text
          for pattern in percentage_patterns:
            match = re.search(pattern, yellow_text)
            if match:
              rate = int(match.group(1))
              if 0 <= rate <= 100:
                print(f"[INFO] Found percentage {rate}% using yellow threshold detection")
                return rate
          
          print("[WARNING] Yellow threshold detection also failed")
        
        # Wait a bit before next attempt
        if ocr_attempt < 2:
          import time
          time.sleep(0.5)
    
    # Fallback: if we can't find the exact bounding box, use the heuristic approach
    x, y, width, height = FAILURE_REGION
    focused_height = int(height * 0.6)
    focused_y = y + int(height * 0.4)
    focused_region = (x, focused_y, width, focused_height)
    
    percentage_img = enhanced_screenshot(focused_region)
    percentage_text = extract_failure_text(percentage_img)
    if not percentage_text:
      percentage_text = extract_text(percentage_img)
    
    percentage_patterns = [
      r"(\d{1,3})\s*%",  # "29%", "29 %"
      r"(\d{1,3})",      # Just the number
    ]
    
    for pattern in percentage_patterns:
      match = re.search(pattern, percentage_text)
      if match:
        rate = int(match.group(1))
        if 0 <= rate <= 100:
          return rate
  
  except Exception as e:
    # If OCR data extraction fails, fall back to heuristic approach
    x, y, width, height = FAILURE_REGION
    focused_height = int(height * 0.6)
    focused_y = y + int(height * 0.4)
    focused_region = (x, focused_y, width, focused_height)
    
    percentage_img = enhanced_screenshot(focused_region)
    percentage_text = extract_failure_text(percentage_img)
    if not percentage_text:
      percentage_text = extract_text(percentage_img)
    
    percentage_patterns = [
      r"(\d{1,3})\s*%",  # "29%", "29 %"
      r"(\d{1,3})",      # Just the number
    ]
    
    for pattern in percentage_patterns:
      match = re.search(pattern, percentage_text)
      if match:
        rate = int(match.group(1))
        if 0 <= rate <= 100:
          return rate

  return -1

# Check mood
def check_mood():
  mood = enhanced_screenshot(MOOD_REGION)
  
  # First try specialized mood text extraction
  mood_text = extract_mood_text(mood).upper()
  if mood_text:
    for known_mood in MOOD_LIST:
      if known_mood in mood_text:
        return known_mood
  
  # Fallback to general text extraction
  mood_text = extract_text(mood).upper()
  for known_mood in MOOD_LIST:
    if known_mood in mood_text:
      return known_mood

  print(f"[WARNING] Mood not recognized: {mood_text}")
  return "UNKNOWN"

# Check turn
def check_turn():
    turn = enhanced_screenshot(TURN_REGION)
    
    # First check for "Race Day" before trying number extraction
    turn_text = extract_text(turn)
    if "Race Day" in turn_text or "RaceDay" in turn_text:
        return "Race Day"
    
    # Then try specialized turn number extraction
    turn_number = extract_turn_number(turn)
    if turn_number and turn_number.isdigit():
        return int(turn_number)
    
    # Fallback to text extraction with character replacement
    # sometimes tesseract misreads characters instead of numbers
    # Handle common digit misreads
    cleaned_text = (
        turn_text
        .replace("T", "1")
        .replace("I", "1")
        .replace("l", "1")  # lowercase L often misread as 1
        .replace("O", "0")
        .replace("o", "0")  # lowercase O
        .replace("S", "5")
        .replace("s", "5")  # lowercase S
        .replace("Z", "2")  # Z often misread as 2
        .replace("z", "2")  # lowercase Z
        .replace("G", "6")  # G sometimes misread as 6
        .replace("g", "6")  # lowercase G
        .replace("B", "8")  # B sometimes misread as 8
        .replace("b", "8")  # lowercase B
    )

    digits_only = re.sub(r"[^\d]", "", cleaned_text)

    if digits_only:
      return int(digits_only)
    
    return -1

# Check year
def check_current_year():
  year = enhanced_screenshot(YEAR_REGION)
  text = extract_text(year)
  
  if not text:
    return ""
  
  # Clean up the text and add proper spacing
  # Remove extra whitespace and normalize
  text = text.strip()
  
  # Remove any extra text after the year (like "ko o")
  # Look for common year patterns and cut off after them
  import re
  
  # Split by whitespace and take only the first few words that look like year text
  words = text.split()
  clean_words = []
  
  # Common OCR artifacts to filter out
  ocr_artifacts = ["Py", "Ko", "O", "A", "I", "U", "E"]
  
  for word in words:
    # Check if word looks like a year word (starts with uppercase, contains letters)
    # Skip single lowercase letters and common OCR artifacts
    if word and word.isalpha():
      if word[0].isupper() and len(word) > 1 and word not in ocr_artifacts:  # Only keep proper words starting with uppercase
        clean_words.append(word)
      elif len(word) == 1 and word.islower():  # Skip single lowercase letters
        continue
      else:
        # Stop when we hit non-year text
        break
  
  text = ' '.join(clean_words)
  
  # Add spaces before uppercase letters (except first letter)
  if text:
    result = text[0]  # Keep first letter as is
    for char in text[1:]:
      if char.isupper():
        result += ' ' + char
      else:
        result += char
    return result
  
  return text

# Check criteria
def check_criteria():
  img = enhanced_screenshot(CRITERIA_REGION)
  
  # Try different PSM modes for better text detection
  import pytesseract
  
  # Try PSM 7 first (better for single line text)
  text = pytesseract.image_to_string(img, config='--oem 3 --psm 7')
  if text.strip():
    return text.strip()
  
  # Fallback to PSM 6
  text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
  if text.strip():
    return text.strip()
  
  # Final fallback to extract_text
  text = extract_text(img)
  return text.strip() if text else ""

# Check skill points
def check_skill_points():
  from utils.constants import SKILL_PTS_REGION
  img = enhanced_screenshot(SKILL_PTS_REGION)
  number = extract_number(img)
  digits = ''.join(filter(str.isdigit, number))
  return int(digits) if digits.isdigit() else 0

# Check skill points and handle cap
def check_skill_points_cap():
  import json
  from pymsgbox import confirm
  
  # Load config
  with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
  
  skill_point_cap = config.get("skill_point_cap", 100)
  current_skill_points = check_skill_points()
  
  print(f"[INFO] Current skill points: {current_skill_points}, Cap: {skill_point_cap}")
  
  if current_skill_points > skill_point_cap:
    print(f"[WARNING] Skill points ({current_skill_points}) exceed cap ({skill_point_cap})")
    
    # Show confirmation dialog 
    result = confirm(
      text=f"Skill points ({current_skill_points}) exceed the cap ({skill_point_cap}).\n\nYou can:\n• Use your skill points manually, then click OK\n• Click OK without spending (automation continues)\n\nNote: This check only happens on race days.",
      title="Skill Points Cap Reached",
      buttons=['OK']
    )
    
    print("[INFO] Automation continuing (player may or may not have spent skill points)")
    return True
  
  return True