import json
import math
import re
from datetime import date, timedelta

USER_FILE = "users.json"
TASK_FILE = "tasks.json"
DEFAULT_SCHEDULE = {"월": 3, "화": 3, "수": 3, "목": 3, "금": 3, "토": 5, "일": 5}
# 1단위(페이지/문제)에 걸리는 기본 예상 시간(분)
DEFAULT_MINUTES_PER_UNIT = {"페이지": 5, "문제 수": 3}

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

def available_hours_on(target_day, user_schedule, busy_hours=None):
    """요일별 학습 가능 시간에서 그날 캘린더 일정이 차지하는 시간을 뺀 값 (최소 0)."""
    weekday_keys = ["월", "화", "수", "목", "금", "토", "일"]
    hours = user_schedule.get(weekday_keys[target_day.weekday()], 3)
    if busy_hours:
        hours -= busy_hours.get(target_day.isoformat(), 0)
    return max(0, hours)

def calculate_daily_target(remaining_amount, end_date_obj, user_schedule, busy_hours=None):
    today = date.today()
    remaining_days = (end_date_obj - today).days + 1
    if remaining_days <= 0 or remaining_amount <= 0:
        return 0

    total_avail_hours = 0
    day_hours_list = []

    for i in range(remaining_days):
        target_day = date.fromordinal(today.toordinal() + i)
        hours = available_hours_on(target_day, user_schedule, busy_hours)
        day_hours_list.append(hours)
        total_avail_hours += hours
        
    today_hours = day_hours_list[0]
    if total_avail_hours == 0:
        return math.ceil(remaining_amount / remaining_days)
    
    return math.ceil(remaining_amount * (today_hours / total_avail_hours))


# ==========================================
# 과제 기본 정보 (예전 형식 과제도 지원)
# ==========================================
def task_minutes_per_unit(task):
    return task.get("minutes_per_unit") or DEFAULT_MINUTES_PER_UNIT.get(task.get("unit"), 5)

def task_end_date(task):
    return date.fromisoformat(task["end_date"])

def task_start_date(task, today=None):
    """등록일. 예전 과제는 첫 기록일, 기록도 없으면 오늘."""
    if task.get("created_date"):
        return date.fromisoformat(task["created_date"])
    log_dates = [date.fromisoformat(entry["date"]) for entry in task.get("log", [])]
    return min(log_dates) if log_dates else (today or date.today())

def task_baseline(task):
    """기록(log)이 생기기 전에 이미 해 둔 분량 (예전 과제의 completed_amount)."""
    logged = sum(entry["amount"] for entry in task.get("log", []))
    return max(0, int(task["completed_amount"]) - logged)

def add_log(task, amount, day):
    """오늘 한 양을 기록합니다. 같은 날 여러 번 기록하면 합칩니다."""
    if amount <= 0:
        return
    task["completed_amount"] = int(task["completed_amount"]) + amount
    log = task.setdefault("log", [])
    for entry in log:
        if entry["date"] == day.isoformat():
            entry["amount"] += amount
            return
    log.append({"date": day.isoformat(), "amount": amount})


# ==========================================
# 과제 간 오늘 시간 배분
# ==========================================
def _hours_until(start_day, end_day, user_schedule, busy_hours=None):
    days = (end_day - start_day).days + 1
    return sum(available_hours_on(start_day + timedelta(days=i), user_schedule, busy_hours) for i in range(max(0, days)))

def allocate_today(tasks, user_schedule, busy_hours=None, today=None):
    """오늘 공부 가능 시간을 진행 중인 과제들에 나눕니다.

    1) 과제마다 오늘 몫 = 남은 시간 × (오늘 가능 시간 / 마감까지 가능 시간 합)
    2) 몫의 합이 오늘 가능 시간을 넘으면 마감이 빠른 과제부터 채웁니다.
    3) 마감까지 필요한 시간이 가능 시간보다 많으면 부족 경고를 만듭니다.
    """
    today = today or date.today()
    avail_today = available_hours_on(today, user_schedule, busy_hours)

    items = []
    for task in tasks:
        remaining = int(task["total_amount"]) - int(task["completed_amount"])
        end_day = task_end_date(task)
        if remaining <= 0 or end_day < today:
            continue
        minutes = task_minutes_per_unit(task)
        need_hours = remaining * minutes / 60
        horizon_hours = _hours_until(today, end_day, user_schedule, busy_hours)
        if horizon_hours > 0:
            share = need_hours * avail_today / horizon_hours
        else:
            share = need_hours / ((end_day - today).days + 1)
        items.append({"task": task, "end": end_day, "remaining": remaining, "minutes_per_unit": minutes,
                      "need_hours": need_hours, "share": share})

    if sum(item["share"] for item in items) <= avail_today + 1e-9:
        for item in items:
            item["hours"] = item["share"]
    else:
        left = avail_today
        for item in sorted(items, key=lambda x: (x["end"], -x["share"])):
            item["hours"] = min(item["share"], left)
            left -= item["hours"]

    allocations = []
    for item in items:
        hours = item["hours"]
        amount = min(item["remaining"], math.ceil(hours * 60 / item["minutes_per_unit"] - 1e-9)) if hours > 0 else 0
        allocations.append({
            "task": item["task"],
            "hours": hours,
            "amount": amount,
            "days_left": (item["end"] - today).days,
        })

    # 마감일 순으로 누적 필요 시간과 누적 가능 시간 비교
    warnings = []
    cumulative_need = 0
    for item in sorted(items, key=lambda x: x["end"]):
        cumulative_need += item["need_hours"]
        shortage = cumulative_need - _hours_until(today, item["end"], user_schedule, busy_hours)
        if shortage > 0.05:
            warnings.append((item["task"]["title"], shortage))

    return {"avail_hours": avail_today, "allocations": allocations, "warnings": warnings}


# ==========================================
# 페이스 / 기록 그래프 / 연속 학습일
# ==========================================
def planned_amount(task, day, user_schedule, today=None):
    """계획대로라면 day가 끝날 때까지 해 두었어야 할 누적 분량 (요일별 가능 시간 비율)."""
    start, end = task_start_date(task, today), task_end_date(task)
    baseline, total = task_baseline(task), int(task["total_amount"])
    if day < start:
        return baseline
    if day >= end:
        return total
    total_hours = _hours_until(start, end, user_schedule)
    if total_hours > 0:
        fraction = _hours_until(start, day, user_schedule) / total_hours
    else:
        fraction = ((day - start).days + 1) / ((end - start).days + 1)
    return baseline + (total - baseline) * fraction

def pace_status(task, user_schedule, today=None):
    """어제까지의 계획과 현재 진행량을 비교해 며칠 앞서는지/뒤처지는지 계산합니다."""
    today = today or date.today()
    completed, total = int(task["completed_amount"]), int(task["total_amount"])
    if total > 0 and completed >= total:
        return {"state": "done", "days": 0, "label": "완료"}
    end = task_end_date(task)
    if end < today:
        return {"state": "overdue", "days": 0, "label": "기한 지남"}

    ref_day = today - timedelta(days=1)
    # 현재 진행량에 계획이 도달하는 날짜 찾기
    reach_day = end
    day = task_start_date(task, today) - timedelta(days=1)
    while day <= end:
        if planned_amount(task, day, user_schedule, today) >= completed - 1e-9:
            reach_day = day
            break
        day += timedelta(days=1)

    diff = (reach_day - ref_day).days
    if diff >= 1:
        return {"state": "ahead", "days": diff, "label": f"{diff}일 앞섬"}
    if diff <= -1:
        return {"state": "behind", "days": -diff, "label": f"{-diff}일 뒤처짐"}
    return {"state": "on_track", "days": 0, "label": "계획대로"}

def progress_series(task, user_schedule, today=None):
    """그래프용 데이터: 날짜별 누적 실제 분량(오늘까지)과 계획 분량(마감일까지)."""
    today = today or date.today()
    start, end = task_start_date(task, today), task_end_date(task)
    daily = {}
    for entry in task.get("log", []):
        daily[entry["date"]] = daily.get(entry["date"], 0) + entry["amount"]

    actual = task_baseline(task)
    # 등록 전날을 출발점으로 두어 두 선이 같은 곳에서 시작하게 함
    before_start = (start - timedelta(days=1)).isoformat()
    rows = [{"날짜": before_start, "구분": "계획", "누적 분량": actual}, {"날짜": before_start, "구분": "실제", "누적 분량": actual}]
    day = start
    while day <= end:
        rows.append({"날짜": day.isoformat(), "구분": "계획", "누적 분량": round(planned_amount(task, day, user_schedule, today), 1)})
        if day <= today:
            actual += daily.get(day.isoformat(), 0)
            rows.append({"날짜": day.isoformat(), "구분": "실제", "누적 분량": actual})
        day += timedelta(days=1)
    return rows

def study_streak(tasks, today=None):
    """어떤 과제든 기록한 날이 오늘(또는 어제)까지 며칠 연속인지."""
    today = today or date.today()
    studied = {entry["date"] for task in tasks for entry in task.get("log", []) if entry["amount"] > 0}
    day = today if today.isoformat() in studied else today - timedelta(days=1)
    streak = 0
    while day.isoformat() in studied:
        streak += 1
        day -= timedelta(days=1)
    return streak

def render_pm_logo_svg(is_animated=True):
    path_class = "pm-svg-path-animated" if is_animated else "pm-svg-path-static"
    box_class = "pm-logo-box-animated" if is_animated else "pm-logo-box-static"
    
    return f'<div class="{box_class}"><svg width="68" height="68" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path class="{path_class}" d="M 22,22 L 22,78 M 22,22 L 38,22 C 50,22 50,50 38,50 L 22,50" stroke="white" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/><path class="{path_class}" d="M 52,78 L 52,22 L 68,54 L 84,22 L 84,78" stroke="white" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
