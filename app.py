import streamlit as st
import altair as alt
import calendar
import html
import time
from datetime import datetime, date, timedelta

import pandas as pd

from data_manager import (
    load_json, save_json, parse_amount_and_unit,
    available_hours_on, render_pm_logo_svg,
    allocate_today, add_log, pace_status, progress_series, study_streak, task_minutes_per_unit,
    USER_FILE, TASK_FILE, DEFAULT_SCHEDULE, DEFAULT_MINUTES_PER_UNIT
)
from auth import validate_signup
import google_calendar as gcal

# 1. 페이지 기본 설정
st.set_page_config(page_title="PACE MAKER", layout="centered")

# 2. 외부 style.css 불러오기
with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 세션 상태 초기화
if "users" not in st.session_state:
    st.session_state.users = load_json(USER_FILE, {})

if "tasks" not in st.session_state:
    st.session_state.tasks = load_json(TASK_FILE, [])

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "intro"

if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

if "home_logo_animated" not in st.session_state:
    st.session_state.home_logo_animated = False

today_obj = date.today()
if "cal_year" not in st.session_state:
    st.session_state.cal_year = today_obj.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = today_obj.month
if "selected_calendar_date" not in st.session_state:
    st.session_state.selected_calendar_date = None

def set_page(page_name):
    st.session_state.current_page = page_name
    st.rerun()

def set_auth_page(auth_name):
    st.session_state.auth_page = auth_name
    st.rerun()

def render_hero(subtitle, is_animated, compact=False):
    logo_html = render_pm_logo_svg(is_animated=is_animated)
    hero_class = "pm-hero pm-hero--compact" if compact else "pm-hero"
    st.markdown(
        f'<div class="{hero_class}">{logo_html}<div class="pm-eyebrow">Study Pace Planner</div><div class="hero-title">PACE MAKER</div><div class="pm-hero-rule"></div><p class="pm-hero-sub">{subtitle}</p></div>',
        unsafe_allow_html=True
    )

def render_page_header(title, subtitle=None):
    sub_html = f"<p class='pm-page-sub'>{subtitle}</p>" if subtitle else ""
    st.markdown(f"<div class='pm-page-title'>{title}</div>{sub_html}", unsafe_allow_html=True)

def render_progress_caption(progress, comp_amt, tot_amt, unit, pace=None):
    pace_html = ""
    if pace and pace["state"] in ("ahead", "behind", "on_track"):
        pace_html = f"<span class='pm-pace-badge pm-pace-badge--{pace['state']}'>{pace['label']}</span>"
    st.markdown(
        f"<div class='pm-progress-caption'><span>진행률 <b>{progress * 100:.1f}%</b>{pace_html}</span><span>{comp_amt} / {tot_amt} {unit}</span></div>",
        unsafe_allow_html=True
    )

def fmt_hours(hours):
    return f"{round(hours, 1):g}"

def fmt_minutes(hours):
    total = round(hours * 60)
    h, m = divmod(total, 60)
    if h and m:
        return f"{h}시간 {m}분"
    return f"{h}시간" if h else f"{m}분"

def render_progress_chart(task, schedule, unit):
    """실제 누적 분량(잉크 실선)과 계획(골드 점선)을 비교하는 선 그래프."""
    df = pd.DataFrame(progress_series(task, schedule, date.today()))
    df["날짜"] = pd.to_datetime(df["날짜"])
    series_scale = alt.Scale(domain=["실제", "계획"], range=["#14161A", "#B08D57"])
    base = alt.Chart(df).encode(
        x=alt.X("날짜:T", title=None, axis=alt.Axis(format="%m/%d", labelAngle=0, grid=False, tickCount=6)),
        y=alt.Y("누적 분량:Q", title=unit, axis=alt.Axis(gridColor="#EFEBE3", domain=False, tickCount=4)),
        color=alt.Color("구분:N", scale=series_scale, legend=alt.Legend(orient="top", title=None)),
        strokeDash=alt.StrokeDash("구분:N", scale=alt.Scale(domain=["실제", "계획"], range=[[1, 0], [5, 4]]), legend=None),
        tooltip=[alt.Tooltip("날짜:T", format="%m월 %d일"), "구분:N", alt.Tooltip("누적 분량:Q", format=",.0f")],
    )
    lines = base.mark_line(strokeWidth=2, interpolate="monotone")
    points = base.transform_filter(alt.datum["구분"] == "실제").mark_point(size=64, filled=True, opacity=1)
    chart = (
        (lines + points).properties(height=220, width="container")
        .configure(font="Pretendard, sans-serif")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor="#8A8D93", titleColor="#8A8D93", labelFontSize=11, titleFontSize=11)
        .configure_legend(labelColor="#3D4047", labelFontSize=12)
    )
    st.altair_chart(chart, theme=None)

def render_event_list(day_events):
    items = "".join(
        f"<li><span class='pm-event-time'>{html.escape(when)}</span><span class='pm-event-title'>{html.escape(title)}</span></li>"
        for when, title in day_events
    )
    return f"<ul class='pm-event-list'>{items}</ul>"


# 구글 캘린더 인증 후 돌아온 경우 (?code=...&state=...)
oauth_user, oauth_msg = gcal.handle_oauth_callback(st.session_state.users)
if oauth_msg:
    if oauth_user:
        save_json(USER_FILE, st.session_state.users)
        gcal.clear_cache()
        st.session_state.current_user = oauth_user
        st.session_state.current_page = "schedule"
    st.toast(oauth_msg)

# st.rerun() 직전에 남긴 알림은 다음 화면에서 보여 줌
for flash_msg in st.session_state.pop("flash_messages", []):
    st.toast(flash_msg)

def flash(message):
    st.session_state.setdefault("flash_messages", []).append(message)


# ==========================================
# 0. 비로그인 상태 (소개 / 로그인 / 회원가입)
# ==========================================
if st.session_state.current_user is None:

    # 0-A. 소개 화면
    if st.session_state.auth_page == "intro":
        render_hero("일정이 틀어져도 괜찮습니다.<br>당신의 일상에 맞추어 페이스를 조절해 드립니다.", is_animated=True)

        st.markdown(
            """<div class="pm-feature-card"><div class="pm-section-label">지능형 과제 스케줄러</div><div class="pm-feature"><span class="pm-feature-num">01</span><div><b>개인 맞춤 가중 계산</b><p>요일별 학습 가능 시간에 맞추어 오늘의 일일 추천 목표를 자동으로 계산합니다.</p></div></div><div class="pm-feature"><span class="pm-feature-num">02</span><div><b>직관적 월간 캘린더</b><p>과제 마감일이 표기된 월간 그리드로 주요 일정을 한눈에 파악합니다.</p></div></div><div class="pm-feature"><span class="pm-feature-num">03</span><div><b>실시간 진도율 기록</b><p>정수 단위 입력과 정교한 % 소수점 표기로 학습 진행률을 모니터링합니다.</p></div></div></div>""",
            unsafe_allow_html=True
        )

        col_auth1, col_auth2 = st.columns(2)
        with col_auth1:
            if st.button("로그인", key="btn_go_login_view"):
                set_auth_page("login")

        with col_auth2:
            if st.button("회원가입", key="btn_go_signup_view", type="primary"):
                set_auth_page("signup")

    # 0-B. 로그인 창
    elif st.session_state.auth_page == "login":
        if st.button("뒤로", key="back_to_intro_from_login", icon=":material/arrow_back:"):
            set_auth_page("intro")

        with st.container(key="card_login"):
            render_page_header("로그인", "아이디와 비밀번호를 입력해 주세요.")

            login_id = st.text_input("아이디", key="input_login_id", placeholder="영문 아이디")
            login_pw = st.text_input("비밀번호", type="password", key="input_login_pw")

            if st.button("로그인", key="btn_submit_login", type="primary"):
                if not login_id.strip() or not login_pw.strip():
                    st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
                elif login_id not in st.session_state.users:
                    st.error("존재하지 않는 아이디입니다.")
                elif st.session_state.users[login_id]["password"] != login_pw:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    st.session_state.current_user = login_id
                    st.session_state.current_page = "home"
                    st.success("로그인 되었습니다.")
                    st.rerun()

    # 0-C. 회원가입 창
    elif st.session_state.auth_page == "signup":
        if st.button("뒤로", key="back_to_intro_from_signup", icon=":material/arrow_back:"):
            set_auth_page("intro")

        with st.container(key="card_signup"):
            render_page_header("회원가입", "새로운 계정 정보 및 주간 학습 가능 시간을 설정해 주세요.")

            new_id = st.text_input("아이디 (영문 대소문자만 가능)", key="input_signup_id", placeholder="예: pacemaker")
            new_pw = st.text_input("비밀번호 (영문 및 숫자 포함 필수)", type="password", key="input_signup_pw")

            st.markdown("<div class='pm-section-label' style='margin-top: 12px;'>주간 요일별 학습 가능 시간 (시간 단위)</div>", unsafe_allow_html=True)
            new_schedule = {}
            day_names = ["월", "화", "수", "목", "금", "토", "일"]
            with st.container(key="sched_grid_signup"):
                cols_sch = st.columns(7)
                for idx, dname in enumerate(day_names):
                    default_h = 5 if idx >= 5 else 3
                    new_schedule[dname] = cols_sch[idx].number_input(f"{dname}", min_value=0, max_value=24, value=default_h, key=f"signup_sch_{dname}")

            if st.button("회원가입", key="btn_submit_signup", type="primary"):
                is_ok, msg = validate_signup(new_id, new_pw)
                if not is_ok:
                    st.error(msg)
                elif new_id in st.session_state.users:
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    st.session_state.users[new_id] = {
                        "password": new_pw,
                        "schedule": new_schedule
                    }
                    save_json(USER_FILE, st.session_state.users)
                    st.success("회원가입 완료! 로그인 화면으로 이동합니다.")
                    set_auth_page("login")

    st.stop()


# ==========================================
# 로그인 완료 상태 공통 데이터
# ==========================================
user_info = st.session_state.users.get(st.session_state.current_user, {"schedule": DEFAULT_SCHEDULE})
user_schedule = user_info.get("schedule", DEFAULT_SCHEDULE)
user_tasks = [t for t in st.session_state.tasks if t.get("user_id") == st.session_state.current_user]
calendar_connected = bool(user_info.get("google_token")) and gcal.is_configured()
calendar_writable = calendar_connected and gcal.has_write_access(user_info)

def push_task_to_calendar(task):
    """과제 마감일을 구글 캘린더에 반영합니다 (쓰기 권한이 있을 때만). 실패해도 앱 동작은 계속됩니다."""
    if not calendar_writable:
        return
    err = gcal.sync_task(user_info, task)
    save_json(USER_FILE, st.session_state.users)  # 토큰이 갱신됐을 수 있음
    if err:
        flash(err)

def remove_task_from_calendar(task):
    if not calendar_writable:
        return
    err = gcal.delete_task_event(user_info, task)
    save_json(USER_FILE, st.session_state.users)
    if err:
        flash(err)

def load_calendar(start_date, end_date):
    """구글 캘린더 일정과 날짜별 바쁜 시간을 불러옵니다. 연동 전이면 빈 값."""
    events, tz_name, err, refreshed = gcal.get_calendar_context(st.session_state.current_user, user_info, start_date, end_date)
    if refreshed:
        save_json(USER_FILE, st.session_state.users)
    if err:
        st.warning(err)
    all_day_blocks = user_info.get("calendar_settings", {}).get("all_day_blocks", False)
    return events, tz_name, gcal.busy_hours_by_date(events, tz_name, all_day_blocks)

def task_horizon(tasks, start_date):
    """일정을 불러올 기간의 끝: 가장 늦은 마감일 (최대 1년)."""
    end_dates = [datetime.strptime(t['end_date'], "%Y-%m-%d").date() for t in tasks]
    return min(max([start_date] + end_dates), start_date + timedelta(days=365))

def load_busy_for_tasks():
    """할 일 배분에 쓸 날짜별 바쁜 시간과 오늘 일정 (연동 전이면 빈 값)."""
    if not calendar_connected:
        return [], None, {}
    return load_calendar(today_obj, task_horizon(user_tasks, today_obj))

def render_today_plan(plan, events, tz_name, busy):
    """오늘 공부 가능 시간과 과제별 배분, 부족 경고, 오늘 구글 일정을 한 카드로 보여 줍니다."""
    today = date.today()
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]
    base_hours = user_schedule.get(weekday_kr, 3)
    busy_today = busy.get(today.isoformat(), 0)
    avail = plan["avail_hours"]

    if avail == 0:
        note = "오늘은 공부 가능 시간이 없어 분량을 남은 날로 넘겼어요."
    elif busy_today > 0:
        note = f"주간 설정 {fmt_hours(base_hours)}시간에서 캘린더 일정 {fmt_hours(busy_today)}시간을 뺐어요."
    else:
        note = f"주간 설정 {fmt_hours(base_hours)}시간 기준이에요."

    rows = ""
    for alloc in sorted(plan["allocations"], key=lambda a: a["days_left"]):
        task = alloc["task"]
        if alloc["amount"] == 0:
            continue
        rows += (
            f"<div class='pm-plan-row'><span class='pm-plan-title'>{html.escape(task['title'])}</span>"
            f"<span class='pm-plan-amount'>{alloc['amount']} {html.escape(task['unit'])}</span>"
            f"<span class='pm-plan-time'>{fmt_minutes(alloc['hours'])}</span>"
            f"<span class='pm-plan-due'>D-{alloc['days_left']}</span></div>"
        )
    if not rows:
        rows = "<p class='pm-today-meta'>오늘 배정된 분량이 없습니다.</p>"
    planned_hours = sum(a["hours"] for a in plan["allocations"])
    spare_hours = avail - planned_hours
    if planned_hours > 0 and spare_hours >= 5 / 60:
        note += f" 남는 {fmt_minutes(spare_hours)}은 여유 시간이에요."

    warnings_html = "".join(
        f"<div class='pm-plan-warning'>⚠ <b>{html.escape(title)}</b> 마감까지 약 {fmt_hours(shortage)}시간이 부족해요. 분량·마감일이나 학습 가능 시간을 조정해 보세요.</div>"
        for title, shortage in plan["warnings"]
    )

    events_html = ""
    if calendar_connected:
        today_events = gcal.events_on_date(events, today, tz_name)
        events_html = "<div class='pm-section-label' style='margin-top: 20px;'>오늘의 구글 캘린더 일정</div>" + (
            render_event_list(today_events) if today_events else "<p class='pm-today-meta'>오늘 등록된 일정이 없습니다.</p>"
        )
    badge = "<span class='pm-badge'>Google Calendar</span>" if calendar_connected else ""

    st.markdown(
        f"<div class='pm-today-card'><div class='pm-today-head'><div><div class='pm-section-label'>오늘의 계획</div>"
        f"<div class='pm-today-hours pm-today-hours--sans'>{fmt_minutes(planned_hours) if planned_hours else '0시간'}<span>/ 가능 {fmt_hours(avail)}시간</span></div></div>{badge}</div>"
        f"<p class='pm-today-meta'>{note}</p><div class='pm-plan-list'>{rows}</div>{warnings_html}{events_html}</div>",
        unsafe_allow_html=True
    )

def render_task_card(idx, task, alloc, avail_hours, key_prefix=""):
    """과제 카드: 진행률·페이스, 오늘 배정 분량, 기록/삭제, 진행 그래프."""
    today = date.today()
    end_date = datetime.strptime(task['end_date'], "%Y-%m-%d").date()
    comp_amt = int(task['completed_amount'])
    tot_amt = int(task['total_amount'])
    remaining_amount = tot_amt - comp_amt
    progress = min(1.0, max(0.0, comp_amt / tot_amt)) if tot_amt > 0 else 0.0
    is_active = remaining_amount > 0 and end_date >= today

    with st.expander(f"**{task['title']}**", expanded=True):
        st.progress(progress)
        render_progress_caption(progress, comp_amt, tot_amt, task['unit'], pace_status(task, user_schedule, today))

        col1, col2 = st.columns([1, 1])

        with col1:
            if remaining_amount <= 0:
                st.success("완료된 과제입니다.")
            elif end_date < today:
                st.error("마감 기한이 지났습니다.")
            else:
                amount = alloc["amount"] if alloc else 0
                st.metric(label="오늘 배정 분량", value=f"{amount} {task['unit']}")
                days_left = (end_date - today).days
                if amount > 0:
                    st.caption(f"약 {fmt_minutes(alloc['hours'])} · 마감 D-{days_left}")
                elif avail_hours == 0:
                    st.caption(f"오늘은 공부 가능 시간이 없어요 · 마감 D-{days_left}")
                else:
                    st.caption(f"오늘은 마감이 더 급한 과제에 시간을 먼저 배정했어요 · 마감 D-{days_left}")

        with col2:
            if is_active:
                today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0, value=0, step=1, key=f"{key_prefix}input_{idx}")
                if st.button("기록", key=f"{key_prefix}btn_{idx}", type="primary"):
                    add_log(task, today_add, today)
                    push_task_to_calendar(task)
                    save_json(TASK_FILE, st.session_state.tasks)
                    flash(f"{task['title']}: 오늘 {today_add} {task['unit']} 기록했어요.")
                    st.rerun()

            if st.button("삭제", key=f"{key_prefix}del_{idx}"):
                remove_task_from_calendar(task)
                st.session_state.tasks = [t for t in st.session_state.tasks if t is not task]
                save_json(TASK_FILE, st.session_state.tasks)
                flash(f"{task['title']} 과제를 삭제했어요.")
                st.rerun()

        with st.popover("진행 그래프 · 설정", icon=":material/show_chart:"):
            render_progress_chart(task, user_schedule, task['unit'])
            new_minutes = st.number_input(
                f"1{'페이지' if task['unit'] == '페이지' else '문제'}당 예상 시간(분)",
                min_value=0.5, max_value=240.0, step=0.5, format="%.1f",
                value=float(task_minutes_per_unit(task)), key=f"{key_prefix}mpu_{idx}",
                help="오늘 분량을 시간으로 나눌 때 씁니다. 실제로 걸리는 시간에 맞춰 바꿔 보세요."
            )
            if new_minutes != float(task_minutes_per_unit(task)):
                task["minutes_per_unit"] = new_minutes
                save_json(TASK_FILE, st.session_state.tasks)
                st.rerun()


# ==========================================
# 1. 메인 홈 화면 (Home)
# ==========================================
if st.session_state.current_page == "home":
    col_u1, col_u2 = st.columns([3, 1], vertical_alignment="center")
    with col_u1:
        weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][today_obj.weekday()]
        st.markdown(
            f"<div class='pm-greeting'><span class='pm-greeting-date'>{today_obj.year}. {today_obj.month:02d}. {today_obj.day:02d} ({weekday_kr})</span>반갑습니다, <b>{st.session_state.current_user}</b>님</div>",
            unsafe_allow_html=True
        )
    with col_u2:
        if st.button("로그아웃", key="btn_logout", icon=":material/logout:"):
            st.session_state.current_user = None
            st.session_state.auth_page = "intro"
            st.session_state.home_logo_animated = False
            st.rerun()

    should_animate = not st.session_state.home_logo_animated
    if should_animate:
        st.session_state.home_logo_animated = True

    render_hero("목표가 틀어져도 괜찮습니다. 오늘 할 일을 유연하게 맞춰드립니다.", is_animated=should_animate, compact=True)

    total_count = len(user_tasks)
    active_count = sum(1 for t in user_tasks if (int(t['total_amount']) - int(t['completed_amount'])) > 0)
    done_count = total_count - active_count
    avg_progress = (
        sum(min(1.0, int(t['completed_amount']) / int(t['total_amount'])) for t in user_tasks if int(t['total_amount']) > 0) / total_count
        if total_count > 0 else 0.0
    )
    streak = study_streak(user_tasks, today_obj)
    behind_titles = [t['title'] for t in user_tasks if pace_status(t, user_schedule, today_obj)["state"] == "behind"]

    with st.container(key="card_summary"):
        st.markdown("<div class='pm-section-label'>학습 현황 요약</div>", unsafe_allow_html=True)
        if total_count == 0:
            st.markdown("<p class='pm-empty-text' style='text-align: left;'>등록된 과제가 없습니다. 아래 메뉴에서 새로운 과제를 등록해 보세요.</p>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='pm-stats pm-stats--4'><div class='pm-stat'><div class='pm-stat-label'>진행 중</div><div class='pm-stat-value'>{active_count}<span>개</span></div></div><div class='pm-stat'><div class='pm-stat-label'>완료</div><div class='pm-stat-value'>{done_count}<span>개</span></div></div><div class='pm-stat'><div class='pm-stat-label'>평균 진행률</div><div class='pm-stat-value'>{avg_progress * 100:.0f}<span>%</span></div></div><div class='pm-stat'><div class='pm-stat-label'>연속 학습</div><div class='pm-stat-value'>{streak}<span>일</span></div></div></div>",
                unsafe_allow_html=True
            )
            if behind_titles:
                names = ", ".join(html.escape(t) for t in behind_titles[:2]) + (f" 외 {len(behind_titles) - 2}개" if len(behind_titles) > 2 else "")
                st.markdown(
                    f"<div class='pm-pace-note'><span class='pm-pace-badge pm-pace-badge--behind'>페이스 주의</span><span><b>{names}</b> 과제가 계획보다 뒤처져 있어요.</span></div>",
                    unsafe_allow_html=True
                )
        if calendar_connected:
            events, tz_name, busy = load_calendar(today_obj, today_obj)
            today_event_count = len(gcal.events_on_date(events, today_obj, tz_name))
            avail_today = available_hours_on(today_obj, user_schedule, busy)
            st.markdown(
                f"<div class='pm-calendar-strip'><span class='pm-badge'>Google Calendar</span><span>오늘 일정 <b>{today_event_count}개</b> · 공부 가능 <b>{fmt_hours(avail_today)}시간</b></span></div>",
                unsafe_allow_html=True
            )

    with st.container(key="home_menu"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("오늘의 할 일", key="btn_home_todo", icon=":material/task_alt:"):
                set_page("todo")

        with col2:
            if st.button("과제 등록", key="btn_home_add", icon=":material/add_circle:"):
                set_page("add")

        with col3:
            if st.button("월간 캘린더", key="btn_home_cal", icon=":material/calendar_month:"):
                st.session_state.selected_calendar_date = None
                set_page("calendar")

        with col4:
            if st.button("일정 관리", key="btn_home_schedule", icon=":material/schedule:"):
                set_page("schedule")


# ==========================================
# 2. 해야 할 일 페이지 (To-Do)
# ==========================================
elif st.session_state.current_page == "todo":
    if st.button("뒤로", key="back_from_todo", icon=":material/arrow_back:"):
        set_page("home")

    render_page_header("해야 할 일", "오늘 가능한 시간을 과제별로 나눴어요. 진행한 만큼 기록하세요.")

    events, tz_name, busy = load_busy_for_tasks()
    plan_today = allocate_today(user_tasks, user_schedule, busy, today_obj)

    if not user_tasks:
        st.markdown(
            """<div class="pm-empty"><p class="pm-empty-text">등록된 과제가 없습니다.<br>과제 등록 페이지에서 새로운 과제를 추가해 보세요.</p></div>""",
            unsafe_allow_html=True
        )
    else:
        render_today_plan(plan_today, events, tz_name, busy)
        if not calendar_connected and gcal.is_configured():
            st.markdown(
                "<div class='pm-hint'>구글 캘린더를 연동하면 약속·수업 같은 일정을 빼고 오늘 분량을 다시 계산해 드려요. <b>일정 관리</b>에서 연동할 수 있습니다.</div>",
                unsafe_allow_html=True
            )
        alloc_by_task = {id(a["task"]): a for a in plan_today["allocations"]}
        for idx, task in enumerate(user_tasks):
            render_task_card(idx, task, alloc_by_task.get(id(task)), plan_today["avail_hours"])


# ==========================================
# 3. 과제 등록 페이지 (Add Task)
# ==========================================
elif st.session_state.current_page == "add":
    if st.button("뒤로", key="back_from_add", icon=":material/arrow_back:"):
        set_page("home")

    with st.container(key="card_add"):
        render_page_header("새로운 과제 추가", "분량과 마감일만 입력하면 하루 목표를 자동으로 나눠 드립니다.")

        with st.form("add_task_form_page", border=False):
            title = st.text_input("과제 이름", placeholder="예: 수학 문제집")
            unit_choice = st.radio("기본 분량 단위 선택", ["페이지", "문제 수"], horizontal=True)
            total_input = st.text_input("총 분량", placeholder="예: 100페이지, 300문제 수 또는 숫자 100만 입력")
            end_date = st.date_input("마감일")
            minutes_input = st.number_input(
                "1페이지/1문제당 예상 시간(분)", min_value=0.5, max_value=240.0, step=0.5, value=None,
                placeholder=f"비워 두면 페이지 {DEFAULT_MINUTES_PER_UNIT['페이지']}분 · 문제 {DEFAULT_MINUTES_PER_UNIT['문제 수']}분",
                help="여러 과제에 오늘 공부 시간을 나눌 때 씁니다. 나중에 과제의 '진행 그래프 · 설정'에서 바꿀 수 있어요."
            )

            submitted = st.form_submit_button("과제 등록", type="primary")
            if submitted:
                parsed_amount, parsed_unit = parse_amount_and_unit(total_input, unit_choice)

                if not title.strip():
                    st.warning("과제 이름을 입력해 주세요.")
                elif parsed_amount is None or parsed_amount <= 0:
                    st.warning("총 분량을 올바른 형식(예: 100, 100페이지, 300문제)으로 입력해 주세요.")
                else:
                    new_task = {
                        "user_id": st.session_state.current_user,
                        "title": title.strip(),
                        "unit": parsed_unit,
                        "total_amount": int(parsed_amount),
                        "completed_amount": 0,
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "created_date": today_obj.isoformat(),
                        "log": []
                    }
                    if minutes_input:
                        new_task["minutes_per_unit"] = minutes_input
                    push_task_to_calendar(new_task)
                    st.session_state.tasks.append(new_task)
                    save_json(TASK_FILE, st.session_state.tasks)
                    st.success(f"'{title}' 과제가 추가되었습니다.")
                    set_page("todo")


# ==========================================
# 4. 일정 관리 페이지 (Schedule Management)
# ==========================================
elif st.session_state.current_page == "schedule":
    if st.button("뒤로", key="back_from_schedule", icon=":material/arrow_back:"):
        set_page("home")

    with st.container(key="card_schedule"):
        render_page_header("주간 학습 일정 변경", "바뀐 일정에 맞춰 요일별 학습 가능 시간(시간 단위)을 수정해 보세요.")

        day_names = ["월", "화", "수", "목", "금", "토", "일"]
        updated_schedule = {}

        with st.container(key="sched_grid_edit"):
            cols_update = st.columns(7)
            for idx, dname in enumerate(day_names):
                cur_h = user_schedule.get(dname, 3)
                updated_schedule[dname] = cols_update[idx].number_input(f"{dname}", min_value=0, max_value=24, value=cur_h, key=f"update_sch_{dname}")

        if st.button("일정 저장", key="btn_save_schedule", type="primary"):
            st.session_state.users[st.session_state.current_user]["schedule"] = updated_schedule
            save_json(USER_FILE, st.session_state.users)
            st.success("주간 학습 일정이 업데이트되었습니다.")
            set_page("home")

    def render_connect_link(label):
        # 같은 세션에서 다시 그릴 때마다 새 인증 요청을 만들지 않도록 URL을 잠시 재사용
        auth_cache = st.session_state.get("gcal_auth")
        if not auth_cache or time.time() - auth_cache["created_at"] > gcal.OAUTH_STATE_TTL_SECONDS - 60:
            auth_cache = {"url": gcal.build_auth_url(st.session_state.current_user), "created_at": time.time()}
            st.session_state.gcal_auth = auth_cache
        st.markdown(
            f"<a class='pm-link-button' href='{html.escape(auth_cache['url'], quote=True)}' target='_self'>{label}</a>",
            unsafe_allow_html=True
        )

    with st.container(key="card_gcal"):
        render_page_header("구글 캘린더 연동", "구글 일정은 앱에서 보이고 공부 시간 계산에 반영되며, 앱에서 등록한 과제 마감일은 구글 캘린더에 표시됩니다.")

        if not gcal.is_configured():
            st.markdown(
                "<div class='pm-hint'>아직 구글 API가 설정되지 않았습니다. <code>.streamlit/secrets.toml</code>에 OAuth 클라이언트 정보를 넣어 주세요. 자세한 방법은 README를 참고하세요.</div>",
                unsafe_allow_html=True
            )
        elif not user_info.get("google_token"):
            render_connect_link("Google 계정으로 연동하기")
            st.caption("캘린더 일정 보기·수정 권한을 요청합니다. 앱은 일정을 읽고, 이 앱에서 등록한 과제 마감 일정만 만들거나 수정합니다.")
        else:
            st.markdown("<div class='pm-connected'><span class='pm-dot'></span>연동됨 · 기본 캘린더의 일정을 반영하고 있어요</div>", unsafe_allow_html=True)

            if not calendar_writable:
                st.markdown(
                    "<div class='pm-hint'>지금은 일정 <b>읽기</b> 권한으로만 연동되어 있어요. 과제 마감일을 구글 캘린더에 올리려면 아래 버튼으로 다시 연동하고 캘린더 권한을 허용해 주세요.</div>",
                    unsafe_allow_html=True
                )
                render_connect_link("권한 업데이트하고 다시 연동하기")
            else:
                unsynced = [t for t in user_tasks if not t.get("gcal_event_id")]
                sync_label = f"과제 마감일 구글 캘린더에 올리기 ({len(unsynced)}개 남음)" if unsynced else "과제 마감일 다시 동기화"
                if user_tasks and st.button(sync_label, key="btn_gcal_sync_all", icon=":material/sync:"):
                    errors = []
                    for task in user_tasks:
                        err = gcal.sync_task(user_info, task)
                        if err:
                            errors.append(err)
                    save_json(TASK_FILE, st.session_state.tasks)
                    save_json(USER_FILE, st.session_state.users)
                    flash(errors[0] if errors else f"과제 {len(user_tasks)}개를 구글 캘린더에 반영했습니다.")
                    st.rerun()
                st.caption("새로 등록하거나 진행률을 기록한 과제는 자동으로 구글 캘린더에 반영됩니다.")

            calendar_settings = user_info.setdefault("calendar_settings", {})
            all_day_blocks = st.toggle(
                "종일 일정이 있는 날은 공부하지 않기",
                value=calendar_settings.get("all_day_blocks", False),
                key="toggle_all_day_blocks",
                help="여행·시험처럼 하루 종일 일정이 잡힌 날의 공부 가능 시간을 0으로 처리합니다. 끄면 시간이 정해진 일정만 반영합니다."
            )
            if all_day_blocks != calendar_settings.get("all_day_blocks", False):
                calendar_settings["all_day_blocks"] = all_day_blocks
                save_json(USER_FILE, st.session_state.users)

            if st.button("연동 해제", key="btn_gcal_disconnect"):
                gcal.disconnect(user_info)
                save_json(USER_FILE, st.session_state.users)
                gcal.clear_cache()
                st.session_state.pop("gcal_auth", None)
                st.rerun()


# ==========================================
# 5. 캘린더 페이지 (Calendar)
# ==========================================
elif st.session_state.current_page == "calendar":

    # 5-A. 상세 화면
    if st.session_state.selected_calendar_date is not None:
        selected_date_str = st.session_state.selected_calendar_date

        if st.button("뒤로", key="back_to_cal_grid", icon=":material/arrow_back:"):
            st.session_state.selected_calendar_date = None
            st.rerun()

        render_page_header(f"{selected_date_str} 마감 과제", "선택하신 날짜에 마감되는 과제의 상세 현황입니다.")

        day_tasks = [t for t in user_tasks if t['end_date'] == selected_date_str]
        sel_date_obj = datetime.strptime(selected_date_str, "%Y-%m-%d").date()

        # 오늘 배분(할 일 화면과 같은 계산)과 선택한 날짜의 구글 일정을 한 번에 불러옴
        events, tz_name, busy = [], None, {}
        if calendar_connected:
            events, tz_name, busy = load_calendar(min(today_obj, sel_date_obj), max(task_horizon(user_tasks, today_obj), sel_date_obj))
            sel_events = gcal.events_on_date(events, sel_date_obj, tz_name)
            if sel_events:
                st.markdown(
                    f"<div class='pm-today-card'><div class='pm-section-label'>이날의 구글 캘린더 일정</div>{render_event_list(sel_events)}</div>",
                    unsafe_allow_html=True
                )
        plan_today = allocate_today(user_tasks, user_schedule, busy, today_obj)
        alloc_by_task = {id(a["task"]): a for a in plan_today["allocations"]}

        if not day_tasks:
            st.markdown(
                """<div class="pm-empty"><p class="pm-empty-text">이 날짜에 마감 예정인 과제가 없습니다.</p></div>""",
                unsafe_allow_html=True
            )
        else:
            for idx, task in enumerate(day_tasks):
                render_task_card(idx, task, alloc_by_task.get(id(task)), plan_today["avail_hours"], key_prefix="cal_dt_")

    # 5-B. 월간 그리드 캘린더
    else:
        if st.button("뒤로", key="back_from_cal_main", icon=":material/arrow_back:"):
            set_page("home")

        with st.container(key="card_calendar"):
            with st.container(key="cal_nav"):
                col_prev, col_title, col_next = st.columns([1, 3, 1], vertical_alignment="center")
                with col_prev:
                    if st.button("이전달", key="prev_month", icon=":material/chevron_left:"):
                        if st.session_state.cal_month == 1:
                            st.session_state.cal_month = 12
                            st.session_state.cal_year -= 1
                        else:
                            st.session_state.cal_month -= 1
                        st.rerun()

                with col_title:
                    with st.container(key="month_popover"):
                        with st.popover(f"{st.session_state.cal_year}년 {st.session_state.cal_month}월"):
                            st.markdown("<div class='pm-section-label'>이동할 연/월 선택</div>", unsafe_allow_html=True)
                            c_y, c_m = st.columns(2)
                            with c_y:
                                sel_y = st.selectbox("연도", range(2023, 2031), index=range(2023, 2031).index(st.session_state.cal_year) if st.session_state.cal_year in range(2023, 2031) else 3, key="pop_sel_y")
                            with c_m:
                                sel_m = st.selectbox("월", range(1, 13), index=st.session_state.cal_month - 1, key="pop_sel_m")

                            if st.button("이동", key="btn_apply_popover_month", type="primary"):
                                st.session_state.cal_year = sel_y
                                st.session_state.cal_month = sel_m
                                st.rerun()

                with col_next:
                    if st.button("다음달", key="next_month", icon=":material/chevron_right:"):
                        if st.session_state.cal_month == 12:
                            st.session_state.cal_month = 1
                            st.session_state.cal_year += 1
                        else:
                            st.session_state.cal_month += 1
                        st.rerun()

            task_map = {}
            for task in user_tasks:
                ed = task['end_date']
                if ed not in task_map:
                    task_map[ed] = []
                task_map[ed].append(task)

            # 이번 달 구글 캘린더 일정 제목
            month_first = date(st.session_state.cal_year, st.session_state.cal_month, 1)
            month_last = date(st.session_state.cal_year, st.session_state.cal_month, calendar.monthrange(st.session_state.cal_year, st.session_state.cal_month)[1])
            event_titles = {}
            if calendar_connected:
                events, tz_name, _ = load_calendar(month_first, month_last)
                for offset in range((month_last - month_first).days + 1):
                    d = month_first + timedelta(days=offset)
                    titles = [title for _, title in gcal.events_on_date(events, d, tz_name)]
                    if titles:
                        event_titles[d.isoformat()] = titles

            # 오늘 날짜 / 마감 과제가 있는 날짜 강조
            highlight_css = f".st-key-cal_grid_{today_obj.strftime('%Y-%m-%d')} button {{ border-color: var(--pm-ink) !important; background: var(--pm-gold-soft) !important; }}"
            for ed in task_map:
                highlight_css += f".st-key-cal_grid_{ed} button {{ box-shadow: inset 3px 0 0 var(--pm-gold) !important; }}"
            st.markdown(f"<style>{highlight_css}</style>", unsafe_allow_html=True)

            with st.container(key="cal_grid"):
                weekdays = ["일", "월", "화", "수", "목", "금", "토"]
                weekday_html = ""
                for idx, day_name in enumerate(weekdays):
                    day_class = "pm-weekday pm-weekday--sun" if idx == 0 else ("pm-weekday pm-weekday--sat" if idx == 6 else "pm-weekday")
                    weekday_html += f"<div class='{day_class}'>{day_name}</div>"
                st.markdown(f"<div class='pm-weekdays'>{weekday_html}</div>", unsafe_allow_html=True)

                c = calendar.Calendar(firstweekday=6)
                month_weeks = c.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)

                for week_idx, week in enumerate(month_weeks):
                    cols = st.columns(7)
                    for idx, day in enumerate(week):
                        if day == 0:
                            cols[idx].button("", key=f"blank_{week_idx}_{idx}", disabled=True)
                        else:
                            date_str = f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}-{day:02d}"
                            day_tasks = task_map.get(date_str, [])

                            # 과제 마감(·)을 먼저, 구글 일정(◦)을 다음에 최대 2줄까지 표시
                            cell_items = [f"· {t['title']}" for t in day_tasks] + [f"◦ {title}" for title in event_titles.get(date_str, [])]
                            cell_lines = []
                            for item in cell_items[:2]:
                                cell_lines.append(item if len(item) <= 8 else item[:7] + "..")
                            if len(cell_items) > 2:
                                cell_lines.append(f"+{len(cell_items) - 2}개")
                            cell_label = f"{day}\n" + "\n".join(cell_lines)

                            if cols[idx].button(cell_label, key=f"cal_grid_{date_str}"):
                                st.session_state.selected_calendar_date = date_str
                                st.rerun()
