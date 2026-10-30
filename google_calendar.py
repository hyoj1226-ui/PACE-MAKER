import json
import os
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from data_manager import load_json, save_json

# 일정 읽기 + 과제 마감 일정 등록/수정/삭제
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
# 이 앱이 만든 구글 일정을 구분하기 위한 표시 (일정의 비공개 확장 속성)
APP_EVENT_TAG = "pacemaker_task"
OAUTH_STATE_FILE = "oauth_states.json"
OAUTH_STATE_TTL_SECONDS = 600
DEFAULT_TIMEZONE = "Asia/Seoul"

# 구글이 이전에 허용한 다른 권한까지 돌려줘도 토큰 교환이 실패하지 않도록 설정
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


# ==========================================
# OAuth 설정 / 인증 흐름
# ==========================================
def get_oauth_settings():
    """secrets.toml의 [google] 설정을 읽습니다. 설정이 없으면 None."""
    try:
        google_conf = st.secrets["google"]
        return {
            "client_id": google_conf["client_id"],
            "client_secret": google_conf["client_secret"],
            "redirect_uri": google_conf["redirect_uri"],
        }
    except Exception:
        # secrets.toml 파일 자체가 없거나 [google] 항목이 빠진 경우
        return None

def is_configured():
    return get_oauth_settings() is not None

def _build_flow(settings, **kwargs):
    client_config = {
        "web": {
            "client_id": settings["client_id"],
            "client_secret": settings["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings["redirect_uri"]],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=settings["redirect_uri"], **kwargs)

def _load_pending_states():
    now = time.time()
    states = load_json(OAUTH_STATE_FILE, {})
    return {k: v for k, v in states.items() if now - v.get("created_at", 0) < OAUTH_STATE_TTL_SECONDS}

def build_auth_url(user_id):
    """구글 로그인 URL을 만들고, 돌아왔을 때 필요한 state/PKCE 값을 파일에 보관합니다.

    구글에서 돌아오면 Streamlit 세션이 새로 시작되므로 세션 상태 대신 파일을 사용합니다.
    """
    settings = get_oauth_settings()
    flow = _build_flow(settings)
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")

    states = _load_pending_states()
    states[state] = {"user_id": user_id, "code_verifier": flow.code_verifier, "created_at": time.time()}
    save_json(OAUTH_STATE_FILE, states)
    return auth_url

def handle_oauth_callback(users):
    """구글 인증 후 돌아온 요청(?code=...&state=...)을 처리합니다.

    반환값: (user_id 또는 None, 메시지 또는 None). 콜백 요청이 아니면 (None, None).
    """
    params = st.query_params
    if "state" not in params or ("code" not in params and "error" not in params):
        return None, None

    state = params.get("state")
    code = params.get("code")
    error = params.get("error")
    st.query_params.clear()

    states = _load_pending_states()
    pending = states.pop(state, None)
    save_json(OAUTH_STATE_FILE, states)

    if pending is None:
        return None, "구글 인증 요청이 만료되었거나 올바르지 않습니다. 다시 연동해 주세요."
    user_id = pending["user_id"]
    if user_id not in users:
        return None, "연동을 요청한 계정을 찾을 수 없습니다."
    if error:
        return user_id, "구글 캘린더 연동이 취소되었습니다."

    try:
        flow = _build_flow(get_oauth_settings(), state=state, code_verifier=pending["code_verifier"])
        flow.fetch_token(code=code)
    except Exception as e:
        return user_id, f"구글 토큰 발급에 실패했습니다: {e}"

    users[user_id]["google_token"] = json.loads(flow.credentials.to_json())
    return user_id, "구글 캘린더가 연동되었습니다."

def disconnect(user_info):
    """저장된 토큰을 삭제하고, 가능하면 구글 쪽 권한도 해제합니다."""
    token_info = user_info.pop("google_token", None)
    if not token_info:
        return
    revoke_target = token_info.get("refresh_token") or token_info.get("token")
    try:
        requests.post("https://oauth2.googleapis.com/revoke", params={"token": revoke_target}, timeout=5)
    except requests.RequestException:
        # 권한 해제 실패는 무시 (토큰은 이미 로컬에서 삭제됨)
        pass


# ==========================================
# 일정 불러오기
# ==========================================
def has_write_access(user_info):
    """과제를 구글 캘린더에 올릴 수 있는 권한으로 연동되었는지 (예전 읽기 전용 연동이면 False)."""
    granted = (user_info.get("google_token") or {}).get("scopes") or []
    return SCOPES[0] in granted

def _get_credentials(user_info):
    """유효한 Credentials를 반환합니다. 토큰이 갱신되면 user_info도 갱신하고 True를 함께 돌려줍니다."""
    # 저장된 토큰의 권한 범위를 그대로 사용 (예전 읽기 전용 연동도 읽기는 계속 동작)
    creds = Credentials.from_authorized_user_info(user_info["google_token"])
    refreshed = False
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        user_info["google_token"] = json.loads(creds.to_json())
        refreshed = True
    return creds, refreshed

def _api_session(creds):
    """구글 API용 requests 세션. 일시적인 연결 끊김(SSL EOF 등)은 자동으로 재시도합니다."""
    session = AuthorizedSession(creds)
    # POST(새 일정 생성)는 중복 생성을 막기 위해 재시도하지 않음
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "PATCH", "DELETE"])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session

def _api_get(session, path, params=None):
    resp = session.get(f"{CALENDAR_API}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_events_cached(user_id, start_iso, end_iso, _creds):
    session = _api_session(_creds)
    # 범위 계산용 시간대는 기본값으로 시작하고, 응답에 담긴 캘린더 시간대로 교체
    calendar_tz = DEFAULT_TIMEZONE
    tz = ZoneInfo(calendar_tz)

    time_min = datetime.combine(date.fromisoformat(start_iso), datetime.min.time(), tz).isoformat()
    time_max = datetime.combine(date.fromisoformat(end_iso) + timedelta(days=1), datetime.min.time(), tz).isoformat()

    events = []
    page_token = None
    while True:
        params = {
            "timeMin": time_min, "timeMax": time_max,
            "singleEvents": "true", "orderBy": "startTime", "maxResults": 250,
        }
        if page_token:
            params["pageToken"] = page_token
        resp = _api_get(session, "/calendars/primary/events", params)
        calendar_tz = resp.get("timeZone", calendar_tz)
        for item in resp.get("items", []):
            if item.get("status") == "cancelled":
                continue
            # 이 앱이 올린 과제 마감 일정은 앱에서 과제로 이미 보여 주므로 제외
            if item.get("extendedProperties", {}).get("private", {}).get(APP_EVENT_TAG):
                continue
            # '한가함'으로 표시한 일정과 내가 거절한 일정은 시간을 차지하지 않는 것으로 처리
            is_free = item.get("transparency") == "transparent"
            declined = any(a.get("self") and a.get("responseStatus") == "declined" for a in item.get("attendees", []))
            start, end = item.get("start", {}), item.get("end", {})
            events.append({
                "title": item.get("summary", "(제목 없음)"),
                "all_day": "date" in start,
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "blocks_time": not (is_free or declined),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events, calendar_tz

def clear_cache():
    _fetch_events_cached.clear()

def get_calendar_context(user_id, user_info, start_date, end_date):
    """기간 내 구글 일정을 불러옵니다.

    반환값: (events, timezone, error_message, token_refreshed)
    연동되지 않았으면 ([], None, None, False).
    """
    if not user_info.get("google_token") or not is_configured():
        return [], None, None, False
    try:
        creds, refreshed = _get_credentials(user_info)
        events, calendar_tz = _fetch_events_cached(user_id, start_date.isoformat(), end_date.isoformat(), creds)
        return events, calendar_tz, None, refreshed
    except RefreshError:
        return [], None, "구글 연동이 만료되었습니다. 일정 관리에서 다시 연동해 주세요.", False
    except requests.HTTPError as e:
        return [], None, f"구글 캘린더를 불러오지 못했습니다. (HTTP {e.response.status_code})", False
    except requests.RequestException:
        return [], None, "구글 서버에 연결하지 못했습니다. 인터넷 연결을 확인한 뒤 새로고침해 주세요.", False
    except Exception as e:
        return [], None, f"구글 캘린더를 불러오지 못했습니다: {e}", False


# ==========================================
# 과제 → 구글 캘린더 마감 일정
# ==========================================
def _task_event_body(task):
    end_date = date.fromisoformat(task["end_date"])
    comp_amt, tot_amt = int(task["completed_amount"]), int(task["total_amount"])
    percent = min(100, comp_amt * 100 // tot_amt) if tot_amt > 0 else 0
    prefix = "[완료]" if comp_amt >= tot_amt else "[마감]"
    return {
        "summary": f"{prefix} {task['title']} · {percent}%",
        "description": f"진행률 {percent}% ({comp_amt}/{tot_amt} {task['unit']})\nPACE MAKER에서 등록한 과제 마감일입니다.",
        "start": {"date": end_date.isoformat()},
        "end": {"date": (end_date + timedelta(days=1)).isoformat()},
        # 다른 사람에게 '바쁨'으로 보이지 않도록 한가함으로 표시
        "transparency": "transparent",
        "status": "confirmed",
        "extendedProperties": {"private": {APP_EVENT_TAG: "1"}},
    }

def _write_error_message(e):
    if isinstance(e, RefreshError):
        return "구글 연동이 만료되었습니다. 일정 관리에서 다시 연동해 주세요."
    if isinstance(e, requests.HTTPError) and e.response.status_code == 403:
        return "구글 캘린더에 쓸 권한이 없습니다. 일정 관리에서 다시 연동하고 캘린더 권한을 허용해 주세요."
    if isinstance(e, requests.HTTPError):
        return f"구글 캘린더에 반영하지 못했습니다. (HTTP {e.response.status_code})"
    if isinstance(e, requests.RequestException):
        return "구글 서버에 연결하지 못해 캘린더에 반영하지 못했습니다."
    return f"구글 캘린더에 반영하지 못했습니다: {e}"

def sync_task(user_info, task):
    """과제 마감일을 구글 캘린더 종일 일정으로 만들거나 갱신합니다.

    새로 만들면 task["gcal_event_id"]에 일정 ID를 저장합니다. 실패하면 오류 메시지를 반환합니다.
    """
    try:
        creds, _ = _get_credentials(user_info)
        session = _api_session(creds)
        body = _task_event_body(task)
        event_id = task.get("gcal_event_id")
        if event_id:
            resp = session.patch(f"{CALENDAR_API}/calendars/primary/events/{event_id}", json=body, timeout=15)
            # 구글 캘린더에서 일정을 지웠거나 다른 계정으로 다시 연동한 경우 새로 만듦
            if resp.status_code not in (404, 410):
                resp.raise_for_status()
                return None
        resp = session.post(f"{CALENDAR_API}/calendars/primary/events", json=body, timeout=15)
        resp.raise_for_status()
        task["gcal_event_id"] = resp.json()["id"]
        return None
    except Exception as e:
        return _write_error_message(e)

def delete_task_event(user_info, task):
    """과제를 지울 때 구글 캘린더의 마감 일정도 지웁니다. 실패하면 오류 메시지를 반환합니다."""
    event_id = task.get("gcal_event_id")
    if not event_id:
        return None
    try:
        creds, _ = _get_credentials(user_info)
        resp = _api_session(creds).delete(f"{CALENDAR_API}/calendars/primary/events/{event_id}", timeout=15)
        if resp.status_code not in (404, 410):
            resp.raise_for_status()
        return None
    except Exception as e:
        return _write_error_message(e)


# ==========================================
# 일정 → 날짜별 바쁜 시간 계산
# ==========================================
def _merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged

def busy_hours_by_date(events, tz_name, all_day_blocks=False):
    """날짜(YYYY-MM-DD)별로 일정이 차지하는 시간을 계산합니다.

    - 겹치는 일정은 한 번만 계산합니다.
    - 자정을 넘기는 일정은 날짜별로 나누어 계산합니다.
    - 종일 일정은 all_day_blocks가 True일 때만 그날 하루 전체(24시간)를 막습니다.
    """
    tz = ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    intervals_by_date = {}
    busy = {}

    for ev in events:
        if not ev.get("blocks_time", True):
            continue
        if ev["all_day"]:
            if all_day_blocks:
                day = date.fromisoformat(ev["start"])
                last = date.fromisoformat(ev["end"])  # 종료일은 포함하지 않음
                while day < last:
                    busy[day.isoformat()] = 24.0
                    day += timedelta(days=1)
            continue

        start = datetime.fromisoformat(ev["start"]).astimezone(tz)
        end = datetime.fromisoformat(ev["end"]).astimezone(tz)
        cursor = start
        while cursor < end:
            day_end = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time(), tz)
            seg_end = min(end, day_end)
            intervals_by_date.setdefault(cursor.date().isoformat(), []).append((cursor, seg_end))
            cursor = seg_end

    for day_str, intervals in intervals_by_date.items():
        hours = sum((e - s).total_seconds() for s, e in _merge_intervals(intervals)) / 3600
        busy[day_str] = max(busy.get(day_str, 0.0), round(hours, 2))
    return busy

def events_on_date(events, target_date, tz_name):
    """특정 날짜에 걸쳐 있는 일정을 (시간 표시 문자열, 제목) 목록으로 반환합니다."""
    tz = ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    result = []
    for ev in events:
        if ev["all_day"]:
            if date.fromisoformat(ev["start"]) <= target_date < date.fromisoformat(ev["end"]):
                result.append(("종일", ev["title"]))
            continue
        start = datetime.fromisoformat(ev["start"]).astimezone(tz)
        end = datetime.fromisoformat(ev["end"]).astimezone(tz)
        if start.date() <= target_date <= (end - timedelta(microseconds=1)).date():
            result.append((f"{start:%H:%M}–{end:%H:%M}", ev["title"]))
    return result
