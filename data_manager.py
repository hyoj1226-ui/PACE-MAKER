import json
import math
import re
from datetime import date

USER_FILE = "users.json"
TASK_FILE = "tasks.json"
DEFAULT_SCHEDULE = {"월": 3, "화": 3, "수": 3, "목": 3, "금": 3, "토": 5, "일": 5}

def load_json(filename, default_val):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_val

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_amount_and_unit(text_input, default_unit):
    text_input = text_input.strip()
    if not text_input:
        return None, None
    
    match = re.search(r'([\d.]+)', text_input)
    if not match:
        return None, None
    
    amount = int(float(match.group(1)))
    
    if "페이지" in text_input:
        unit = "페이지"
    elif "문제" in text_input:
        unit = "문제 수"
    else:
        unit = default_unit
        
    return amount, unit

def calculate_daily_target(remaining_amount, end_date_obj, user_schedule):
    today = date.today()
    remaining_days = (end_date_obj - today).days + 1
    if remaining_days <= 0 or remaining_amount <= 0:
        return 0
    
    weekday_keys = ["월", "화", "수", "목", "금", "토", "일"]
    total_avail_hours = 0
    day_hours_list = []
    
    for i in range(remaining_days):
        target_day = date.fromordinal(today.toordinal() + i)
        w_idx = target_day.weekday()
        w_key = weekday_keys[w_idx]
        hours = user_schedule.get(w_key, 3)
        day_hours_list.append(hours)
        total_avail_hours += hours
        
    today_hours = day_hours_list[0]
    if total_avail_hours == 0:
        return math.ceil(remaining_amount / remaining_days)
    
    return math.ceil(remaining_amount * (today_hours / total_avail_hours))

def render_pm_logo_svg(is_animated=True):
    path_class = "pm-svg-path-animated" if is_animated else "pm-svg-path-static"
    box_class = "pm-logo-box-animated" if is_animated else "pm-logo-box-static"
    
    return f'<div class="{box_class}"><svg width="68" height="68" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path class="{path_class}" d="M 22,22 L 22,78 M 22,22 L 38,22 C 50,22 50,50 38,50 L 22,50" stroke="white" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/><path class="{path_class}" d="M 52,78 L 52,22 L 68,54 L 84,22 L 84,78" stroke="white" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
