import pyautogui
import time
import json

pyautogui.useImageNotFoundException(False)

from core.state import check_support_card, check_failure, check_turn, check_mood, check_current_year, check_criteria, check_skill_points_cap
from core.logic import do_something, do_something_fallback, all_training_unsafe, MAX_FAILURE
from utils.constants import MOOD_LIST

def is_racing_available(year):
  """Check if racing is available based on the current year/month"""
  # No races in Pre-Debut
  if "Pre-Debut" in year:
    return False
  year_parts = year.split(" ")
  # No races in July and August (summer break)
  if len(year_parts) > 3 and year_parts[3] in ["Jul", "Aug"]:
    return False
  return True
from core.recognizer import is_infirmary_active, match_template
from utils.scenario import ura

with open("config.json", "r", encoding="utf-8") as file:
  config = json.load(file)

MINIMUM_MOOD = config["minimum_mood"]
PRIORITIZE_G1_RACE = config["prioritize_g1_race"]

def click(img, confidence = 0.8, minSearch = 2, click = 1, text = ""):
  btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch)
  if btn:
    if text:
      print(text)
    pyautogui.moveTo(btn, duration=0.175)
    pyautogui.click(clicks=click)
    return True
  
  return False

def go_to_training():
  return click("assets/buttons/training_btn.png")

def check_training():
  training_types = {
    "spd": "assets/icons/train_spd.png",
    "sta": "assets/icons/train_sta.png",
    "pwr": "assets/icons/train_pwr.png",
    "guts": "assets/icons/train_guts.png",
    "wit": "assets/icons/train_wit.png"
  }
  results = {}

  for key, icon_path in training_types.items():
    pos = pyautogui.locateCenterOnScreen(icon_path, confidence=0.8)
    if pos:
      pyautogui.moveTo(pos, duration=0.1)
      pyautogui.mouseDown()
      support_counts = check_support_card()
      total_support = sum(support_counts.values())
      
      # Retry failure detection if confidence is low
      max_retries = 3
      best_confidence = 0.0
      best_failure_result = None
      
      for attempt in range(max_retries):
        failure_result = check_failure()
        
        # Handle new tuple format (rate, confidence) or old format (rate)
        if isinstance(failure_result, tuple):
          failure_chance, confidence = failure_result
        else:
          failure_chance = failure_result
          confidence = 0.0  # Default confidence for old format
        
        # Keep the best result (highest confidence)
        if confidence > best_confidence:
          best_confidence = confidence
          best_failure_result = failure_result
        
        # If we have good confidence, no need to retry
        if confidence >= 0.5:
          break
        
        # Wait a bit before retry
        if attempt < max_retries - 1:
          time.sleep(0.2)
      
      # Use the best result we found
      if isinstance(best_failure_result, tuple):
        failure_chance, confidence = best_failure_result
      else:
        failure_chance = best_failure_result
        confidence = best_confidence
      
      results[key] = {
        "support": support_counts,
        "total_support": total_support,
        "failure": failure_chance,
        "confidence": confidence
      }
      
      retry_info = f" (retried {max_retries} times)" if best_confidence < 0.5 else ""
      print(f"[{key.upper()}] → {support_counts}, Fail: {failure_chance}% - Confident: {confidence:.2f}{retry_info}")
      time.sleep(0.1)
  
  pyautogui.mouseUp()
  click(img="assets/buttons/back_btn.png")
  return results

def do_train(train):
  train_btn = pyautogui.locateCenterOnScreen(f"assets/icons/train_{train}.png", confidence=0.8)
  if train_btn:
    pyautogui.tripleClick(train_btn, interval=0.1, duration=0.2)

def do_rest():
  rest_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_btn.png", confidence=0.8)
  rest_summber_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8)

  if rest_btn:
    pyautogui.moveTo(rest_btn, duration=0.15)
    pyautogui.click(rest_btn)
  elif rest_summber_btn:
    pyautogui.moveTo(rest_summber_btn, duration=0.15)
    pyautogui.click(rest_summber_btn)

def do_recreation():
  recreation_btn = pyautogui.locateCenterOnScreen("assets/buttons/recreation_btn.png", confidence=0.8)
  recreation_summer_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8)

  if recreation_btn:
    pyautogui.moveTo(recreation_btn, duration=0.15)
    pyautogui.click(recreation_btn)
  elif recreation_summer_btn:
    pyautogui.moveTo(recreation_summer_btn, duration=0.15)
    pyautogui.click(recreation_summer_btn)

def do_race(prioritize_g1 = False):
  click(img="assets/buttons/races_btn.png", minSearch=10)
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)

  found = race_select(prioritize_g1=prioritize_g1)
  if not found:
    print("[INFO] No race found.")
    return False

  race_prep()
  time.sleep(1)
  after_race()
  return True

def race_day():
  # Check skill points cap before race day (if enabled)
  import json
  
  # Load config to check if skill point check is enabled
  with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
  
  enable_skill_check = config.get("enable_skill_point_check", True)
  
  if enable_skill_check:
    print("[INFO] Race Day - Checking skill points cap...")
    check_skill_points_cap()
  
  click(img="assets/buttons/race_day_btn.png", minSearch=10)
  
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)
  time.sleep(0.5)

  for i in range(2):
    click(img="assets/buttons/race_btn.png", minSearch=2)
    time.sleep(0.5)

  race_prep()
  time.sleep(1)
  after_race()

def race_select(prioritize_g1 = False):
  pyautogui.moveTo(x=560, y=680)

  time.sleep(0.2)

  if prioritize_g1:
    print("[INFO] Looking for G1 race.")
    for i in range(2):
      race_card = match_template("assets/ui/g1_race.png", threshold=0.9)

      if race_card:
        for x, y, w, h in race_card:
          region = (x, y, 310, 90)
          match_aptitude = pyautogui.locateCenterOnScreen("assets/ui/match_track.png", confidence=0.8, minSearchTime=0.7, region=region)
          if match_aptitude:
            print("[INFO] G1 race found.")
            pyautogui.moveTo(match_aptitude, duration=0.2)
            pyautogui.click()
            for i in range(2):
              race_btn = pyautogui.locateCenterOnScreen("assets/buttons/race_btn.png", confidence=0.8, minSearchTime=2)
              if race_btn:
                pyautogui.moveTo(race_btn, duration=0.2)
                pyautogui.click(race_btn)
                time.sleep(0.5)
            return True
      
      for i in range(4):
        pyautogui.scroll(-300)
    
    return False
  else:
    print("[INFO] Looking for race.")
    for i in range(4):
      match_aptitude = pyautogui.locateCenterOnScreen("assets/ui/match_track.png", confidence=0.8, minSearchTime=0.7)
      if match_aptitude:
        print("[INFO] Race found.")
        pyautogui.moveTo(match_aptitude, duration=0.2)
        pyautogui.click(match_aptitude)

        for i in range(2):
          race_btn = pyautogui.locateCenterOnScreen("assets/buttons/race_btn.png", confidence=0.8, minSearchTime=2)
          if race_btn:
            pyautogui.moveTo(race_btn, duration=0.2)
            pyautogui.click(race_btn)
            time.sleep(0.5)
        return True
      
      for i in range(4):
        pyautogui.scroll(-300)
    
    return False

def race_prep():
  view_result_btn = pyautogui.locateCenterOnScreen("assets/buttons/view_results.png", confidence=0.8, minSearchTime=20)
  if view_result_btn:
    pyautogui.click(view_result_btn)
    time.sleep(0.5)
    for i in range(3):
      pyautogui.tripleClick(interval=0.2)
      time.sleep(0.5)

def after_race():
  # Try to click next_btn.png, if not found, click at (185, 900) and wait for it to appear
  if not click(img="assets/buttons/next_btn.png", minSearch=10):
    print("[INFO] next_btn.png not found, clicking at (185, 900) and waiting...")
    pyautogui.click(185, 900)
    time.sleep(1)  # Wait a bit for the button to appear
    click(img="assets/buttons/next_btn.png", minSearch=10)
  
  time.sleep(0.5) # Raise a bit
  pyautogui.click()
  click(img="assets/buttons/next2_btn.png", minSearch=10)

def career_lobby():
  # Program start
  while True:
    # First check, event
    if click(img="assets/icons/event_choice_1.png", minSearch=0.2, text="[INFO] Event found, automatically select top choice."):
      continue

    # Second check, inspiration
    if click(img="assets/buttons/inspiration_btn.png", minSearch=0.2, text="[INFO] Inspiration found."):
      continue

    if click(img="assets/buttons/next_btn.png", minSearch=0.2):
      continue

    if click(img="assets/buttons/cancel_btn.png", minSearch=0.2):
      continue

    # Check if current menu is in career lobby
    tazuna_hint = pyautogui.locateCenterOnScreen("assets/ui/tazuna_hint.png", confidence=0.8, minSearchTime=0.2)

    if tazuna_hint is None:
      print("[INFO] Should be in career lobby.")
      continue

    time.sleep(0.5)

    # Check if there is debuff status
    debuffed = pyautogui.locateOnScreen("assets/buttons/infirmary_btn2.png", confidence=0.9, minSearchTime=1)
    if debuffed:
      if is_infirmary_active((debuffed.left, debuffed.top, debuffed.width, debuffed.height)):
        pyautogui.click(debuffed)
        print("[INFO] Character has debuff, go to infirmary instead.")
        continue

    mood = check_mood()
    mood_index = MOOD_LIST.index(mood)
    minimum_mood = MOOD_LIST.index(MINIMUM_MOOD)
    turn = check_turn()
    year = check_current_year()
    criteria = check_criteria()
    
    print("\n=======================================================================================\n")
    print(f"Year: {year}")
    print(f"Mood: {mood}")
    print(f"Turn: {turn}")
    print(f"Goal: {criteria}")
    
    # Check if goals criteria are NOT met AND it is not Pre-Debut AND turn is less than 10
    # Prioritize racing when criteria are not met to help achieve goals
    criteria_met = (criteria.split(" ")[0] == "criteria" or "criteria met" in criteria.lower() or "goal achieved" in criteria.lower())
    year_parts = year.split(" ")
    is_pre_debut = "Pre-Debut" in year
    if not criteria_met and not is_pre_debut and turn < 10:
      print(f"Goal Status: Criteria not met - Prioritizing racing to meet goals")
      race_found = do_race()
      if race_found:
        print("Race Result: Found Race")
        continue
      else:
        print("Race Result: No Race Found")
        # If there is no race matching to aptitude, go back and do training instead
        click(img="assets/buttons/back_btn.png", text="[INFO] Race not found. Proceeding to training.")
        time.sleep(0.5)
    else:
      print("Goal Status: Criteria met or conditions not suitable for racing")
    
    print("")

    # URA SCENARIO
    if year == "Finale Season" and turn == "Race Day":
      print("[INFO] URA Finale")
      
      # Check skill points cap before URA race day (if enabled)
      import json
      
      # Load config to check if skill point check is enabled
      with open("config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
      
      enable_skill_check = config.get("enable_skill_point_check", True)
      
      if enable_skill_check:
        print("[INFO] URA Finale Race Day - Checking skill points cap...")
        check_skill_points_cap()
      
      ura()
      for i in range(2):
        if click(img="assets/buttons/race_btn.png", minSearch=2):
          time.sleep(0.5)
      
      race_prep()
      time.sleep(1)
      after_race()
      continue

    # If calendar is race day, do race
    if turn == "Race Day" and year != "Finale Season":
      print("[INFO] Race Day.")
      race_day()
      continue

    # Mood check
    if mood_index < minimum_mood:
      print("[INFO] Mood is low, trying recreation to increase mood")
      do_recreation()
      continue



    year_parts = year.split(" ")
    # If Prioritize G1 Race is true, check G1 race every turn
    if PRIORITIZE_G1_RACE and "Pre-Debut" not in year and is_racing_available(year):
      print("G1 Race Check: Looking for G1 race...")
      g1_race_found = do_race(PRIORITIZE_G1_RACE)
      if g1_race_found:
        print("G1 Race Result: Found G1 Race")
        continue
      else:
        print("G1 Race Result: No G1 Race Found")
        # If there is no G1 race, go back and do training
        click(img="assets/buttons/back_btn.png", text="[INFO] G1 race not found. Proceeding to training.")
        time.sleep(0.5)
    
    # Check training button
    if not go_to_training():
      print("[INFO] Training button is not found.")
      continue

    # Last, do training
    time.sleep(0.5)
    results_training = check_training()
    
    best_training = do_something(results_training)
    if best_training == "PRIORITIZE_RACE":
      # Check if it's Pre-Debut - if so, don't prioritize racing
      year_parts = year.split(" ")
      if "Pre-Debut" in year:
        print("[INFO] Pre-Debut detected. Skipping race prioritization and proceeding to training.")
        # Re-evaluate training without race prioritization
        best_training = do_something_fallback(results_training)
        if best_training:
          go_to_training()
          time.sleep(0.5)
          do_train(best_training)
        else:
          do_rest()
        continue
      
      # Check if it's Finale Season - no races available, fall back to training without min_support
      if year == "Finale Season":
        print("[INFO] Finale Season detected. No races available. Proceeding to training without minimum support requirements.")
        # Re-evaluate training without race prioritization
        best_training = do_something_fallback(results_training)
        if best_training:
          go_to_training()
          time.sleep(0.5)
          do_train(best_training)
        else:
          do_rest()
        continue
      
      print("[INFO] Prioritizing race due to insufficient support cards.")
      
      # Check if all training options are unsafe before attempting race
      if all_training_unsafe(results_training):
        print(f"[INFO] All training options have failure rate > {MAX_FAILURE}%. Skipping race and choosing to rest.")
        do_rest()
        continue
      
      # Check if racing is available (no races in July/August)
      if not is_racing_available(year):
        print("[INFO] July/August detected. No races available during summer break. Choosing to rest.")
        do_rest()
        continue
      
      print("Training Race Check: Looking for race due to insufficient support cards...")
      race_found = do_race()
      if race_found:
        print("Training Race Result: Found Race")
        continue
      else:
        print("Training Race Result: No Race Found")
        # If no race found, go back to training logic
        print("[INFO] No race found. Returning to training logic.")
        click(img="assets/buttons/back_btn.png", text="[INFO] Race not found. Proceeding to training.")
        time.sleep(0.5)
        # Re-evaluate training without race prioritization
        best_training = do_something_fallback(results_training)
        if best_training:
          go_to_training()
          time.sleep(0.5)
          do_train(best_training)
        else:
          do_rest()
    elif best_training:
      go_to_training()
      time.sleep(0.5)
      do_train(best_training)
    else:
      do_rest()
    time.sleep(1)
