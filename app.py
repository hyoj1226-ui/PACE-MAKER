import streamlit as st
import calendar
from datetime import datetime, date

from data_manager import (
    load_json, save_json, parse_amount_and_unit,
    calculate_daily_target, render_pm_logo_svg,
    USER_FILE, TASK_FILE, DEFAULT_SCHEDULE
)
from auth import validate_signup

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

def render_progress_caption(progress, comp_amt, tot_amt, unit):
    st.markdown(
        f"<div class='pm-progress-caption'><span>진행률 <b>{progress * 100:.1f}%</b></span><span>{comp_amt} / {tot_amt} {unit}</span></div>",
        unsafe_allow_html=True
    )


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

    with st.container(key="card_summary"):
        st.markdown("<div class='pm-section-label'>학습 현황 요약</div>", unsafe_allow_html=True)
        if total_count == 0:
            st.markdown("<p class='pm-empty-text' style='text-align: left;'>등록된 과제가 없습니다. 아래 메뉴에서 새로운 과제를 등록해 보세요.</p>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='pm-stats'><div class='pm-stat'><div class='pm-stat-label'>진행 중</div><div class='pm-stat-value'>{active_count}<span>개</span></div></div><div class='pm-stat'><div class='pm-stat-label'>완료</div><div class='pm-stat-value'>{done_count}<span>개</span></div></div><div class='pm-stat'><div class='pm-stat-label'>평균 진행률</div><div class='pm-stat-value'>{avg_progress * 100:.0f}<span>%</span></div></div></div>",
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

    render_page_header("해야 할 일", "오늘의 추천 분량을 확인하고 진행한 만큼 기록하세요.")

    if not user_tasks:
        st.markdown(
            """<div class="pm-empty"><p class="pm-empty-text">등록된 과제가 없습니다.<br>과제 등록 페이지에서 새로운 과제를 추가해 보세요.</p></div>""",
            unsafe_allow_html=True
        )
    else:
        today = date.today()
        for idx, task in enumerate(user_tasks):
            end_date = datetime.strptime(task['end_date'], "%Y-%m-%d").date()
            remaining_days = max(0, (end_date - today).days + 1)

            comp_amt = int(task['completed_amount'])
            tot_amt = int(task['total_amount'])
            remaining_amount = tot_amt - comp_amt
            progress = min(1.0, max(0.0, comp_amt / tot_amt)) if tot_amt > 0 else 0.0

            with st.expander(f"**{task['title']}**", expanded=True):
                st.progress(progress)
                render_progress_caption(progress, comp_amt, tot_amt, task['unit'])

                col1, col2 = st.columns([1, 1])

                with col1:
                    if remaining_amount <= 0:
                        st.success("완료된 과제입니다.")
                    elif end_date < today:
                        st.error("마감 기한이 지났습니다.")
                    elif remaining_days <= 0:
                        st.error("유효 작업 일수가 부족합니다.")
                    else:
                        daily_target = calculate_daily_target(remaining_amount, end_date, user_schedule)
                        st.metric(label="오늘의 맞춤 추천 목표", value=f"{daily_target} {task['unit']}")
                        st.caption(f"남은 기간 D-{remaining_days}일 (주간 일정 자동 반영)")

                with col2:
                    if remaining_amount > 0 and end_date >= today and remaining_days > 0:
                        today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0, value=0, step=1, key=f"input_{idx}")
                        if st.button("기록", key=f"btn_{idx}", type="primary"):
                            task['completed_amount'] = comp_amt + today_add
                            save_json(TASK_FILE, st.session_state.tasks)
                            st.success("기록 되었습니다.")
                            st.rerun()

                    if st.button("삭제", key=f"del_{idx}"):
                        st.session_state.tasks = [t for t in st.session_state.tasks if t != task]
                        save_json(TASK_FILE, st.session_state.tasks)
                        st.success("삭제 되었습니다.")
                        st.rerun()


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
                        "end_date": end_date.strftime("%Y-%m-%d")
                    }
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

        if not day_tasks:
            st.markdown(
                """<div class="pm-empty"><p class="pm-empty-text">이 날짜에 마감 예정인 과제가 없습니다.</p></div>""",
                unsafe_allow_html=True
            )
        else:
            today = date.today()
            sel_date_obj = datetime.strptime(selected_date_str, "%Y-%m-%d").date()

            for idx, task in enumerate(day_tasks):
                remaining_days = max(0, (sel_date_obj - today).days + 1)
                comp_amt = int(task['completed_amount'])
                tot_amt = int(task['total_amount'])
                remaining_amount = tot_amt - comp_amt
                progress = min(1.0, max(0.0, comp_amt / tot_amt)) if tot_amt > 0 else 0.0

                with st.expander(f"**{task['title']}**", expanded=True):
                    st.progress(progress)
                    render_progress_caption(progress, comp_amt, tot_amt, task['unit'])

                    col1, col2 = st.columns([1, 1])

                    with col1:
                        if remaining_amount <= 0:
                            st.success("완료된 과제입니다.")
                        elif sel_date_obj < today:
                            st.error("마감 기한이 지났습니다.")
                        elif remaining_days <= 0:
                            st.error("유효 작업 일수가 부족합니다.")
                        else:
                            daily_target = calculate_daily_target(remaining_amount, sel_date_obj, user_schedule)
                            st.metric(label="오늘의 맞춤 추천 목표", value=f"{daily_target} {task['unit']}")
                            st.caption(f"남은 기간 D-{remaining_days}일")

                    with col2:
                        if remaining_amount > 0 and sel_date_obj >= today and remaining_days > 0:
                            today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0, value=0, step=1, key=f"cal_dt_input_{idx}")
                            if st.button("기록", key=f"cal_dt_btn_{idx}", type="primary"):
                                task['completed_amount'] = comp_amt + today_add
                                save_json(TASK_FILE, st.session_state.tasks)
                                st.success("기록 되었습니다.")
                                st.rerun()

                        if st.button("삭제", key=f"cal_dt_del_{idx}"):
                            st.session_state.tasks = [t for t in st.session_state.tasks if t != task]
                            save_json(TASK_FILE, st.session_state.tasks)
                            st.success("삭제 되었습니다.")
                            st.rerun()

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

                            cell_label = f"{day}\n"
                            if day_tasks:
                                task_titles = []
                                for t in day_tasks[:2]:
                                    t_name = t['title']
                                    if len(t_name) > 6:
                                        t_name = t_name[:5] + ".."
                                    task_titles.append(f"· {t_name}")
                                cell_label += "\n".join(task_titles)
                                if len(day_tasks) > 2:
                                    cell_label += f"\n+{len(day_tasks)-2}개"

                            if cols[idx].button(cell_label, key=f"cal_grid_{date_str}"):
                                st.session_state.selected_calendar_date = date_str
                                st.rerun()
