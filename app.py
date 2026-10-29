import streamlit as st
import calendar
from datetime import datetime, date

# 데이터 및 인증 모듈 불러오기
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


# ==========================================
# 0. 비로그인 상태 (소개 / 로그인 / 회원가입)
# ==========================================
if st.session_state.current_user is None:
    
    # 0-A. 소개 화면
    if st.session_state.auth_page == "intro":
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 28px; margin-bottom: 32px;">
                {render_pm_logo_svg(is_animated=True)}
                <h1 class="hero-title" style="font-weight: 900; color: #191F28; font-size: 42px; margin: 0 0 10px 0; text-align: center;">PACE MAKER</h1>
                <p style="color: #6B7684; font-size: 16px; margin: 0; text-align: center; font-weight: 500;">일정이 틀어져도 괜찮습니다. 당신의 일상에 맞추어 페이스를 조절해 드립니다.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="tds-card" style="padding: 28px; margin-bottom: 24px;">
                <h3 style="font-size: 18px; font-weight: 800; color: #191F28; margin: 0 0 12px 0;">지능형 과제 스케줄러</h3>
                <p style="font-size: 14px; color: #4E5968; margin: 0 0 8px 0; line-height: 1.6;">• <b>개인 맞춤 가중 계산</b>: 요일별 학습 가능 시간에 맞추어 오늘의 일일 추천 목표를 자동으로 계산합니다.</p>
                <p style="font-size: 14px; color: #4E5968; margin: 0 0 8px 0; line-height: 1.6;">• <b>직관적 월간 캘린더</b>: 과제 마감일이 표기된 월간 그리드로 주요 일정을 한눈에 파악합니다.</p>
                <p style="font-size: 14px; color: #4E5968; margin: 0; line-height: 1.6;">• <b>실시간 진도율 기록</b>: 정수 단위 입력과 정교한 % 소수점 표기로 학습 진행률을 모니터링합니다.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_auth1, col_auth2 = st.columns(2)
        with col_auth1:
            if st.button("로그인", key="btn_go_login_view"):
                set_auth_page("login")

        with col_auth2:
            st.markdown("<div class='record-btn'>", unsafe_allow_html=True)
            if st.button("회원가입", key="btn_go_signup_view"):
                set_auth_page("signup")
            st.markdown("</div>", unsafe_allow_html=True)

    # 0-B. 로그인 창
    elif st.session_state.auth_page == "login":
        st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
        if st.button("←", key="back_to_intro_from_login"):
            set_auth_page("intro")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 24px; font-weight: 800; color: #191F28; margin-bottom: 4px;'>로그인</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 20px;'>아이디와 비밀번호를 입력해 주세요.</p>", unsafe_allow_html=True)

        login_id = st.text_input("아이디", key="input_login_id", placeholder="영문 아이디")
        login_pw = st.text_input("비밀번호", type="password", key="input_login_pw")

        if st.button("로그인", key="btn_submit_login"):
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
        st.markdown("</div>", unsafe_allow_html=True)

    # 0-C. 회원가입 창
    elif st.session_state.auth_page == "signup":
        st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
        if st.button("←", key="back_to_intro_from_signup"):
            set_auth_page("intro")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 24px; font-weight: 800; color: #191F28; margin-bottom: 4px;'>회원가입</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 20px;'>새로운 계정 정보 및 주간 학습 가능 시간을 설정해 주세요.</p>", unsafe_allow_html=True)

        new_id = st.text_input("아이디 (영문 대소문자만 가능)", key="input_signup_id", placeholder="예: pacemaker")
        new_pw = st.text_input("비밀번호 (영문 및 숫자 포함 필수)", type="password", key="input_signup_pw")

        st.markdown("<p style='font-weight: 700; font-size: 14px; color: #191F28; margin-top: 20px; margin-bottom: 8px;'>주간 요일별 학습 가능 시간 (시간 단위)</p>", unsafe_allow_html=True)
        cols_sch = st.columns(7)
        new_schedule = {}
        day_names = ["월", "화", "수", "목", "금", "토", "일"]
        for idx, dname in enumerate(day_names):
            default_h = 5 if idx >= 5 else 3
            new_schedule[dname] = cols_sch[idx].number_input(f"{dname}", min_value=0, max_value=24, value=default_h, key=f"signup_sch_{dname}")

        st.markdown("<div class='record-btn' style='margin-top: 20px;'>", unsafe_allow_html=True)
        if st.button("회원가입", key="btn_submit_signup"):
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
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        st.markdown(f"<p style='color: #4E5968; font-size: 14px; font-weight: 600; margin: 8px 0 0 0;'>반갑습니다, <b>{st.session_state.current_user}</b>님</p>", unsafe_allow_html=True)
    with col_u2:
        st.markdown("<div class='logout-btn'>", unsafe_allow_html=True)
        if st.button("로그아웃", key="btn_logout"):
            st.session_state.current_user = None
            st.session_state.auth_page = "intro"
            st.session_state.home_logo_animated = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    should_animate = not st.session_state.home_logo_animated
    if should_animate:
        st.session_state.home_logo_animated = True

    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 12px; margin-bottom: 24px;">
            {render_pm_logo_svg(is_animated=should_animate)}
            <h1 class="hero-title" style="font-weight: 900; color: #191F28; font-size: 34px; margin: 0 0 6px 0; text-align: center;">PACE MAKER</h1>
            <p style="color: #8B95A1; font-size: 14px; margin: 0; text-align: center;">목표가 틀어져도 괜찮습니다. 오늘 할 일을 유연하게 맞춰드립니다.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    total_count = len(user_tasks)
    active_count = sum(1 for t in user_tasks if (int(t['total_amount']) - int(t['completed_amount'])) > 0)
    
    st.markdown("<div class='tds-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 17px; font-weight: 700; color: #191F28; margin-bottom: 6px;'>학습 현황 요약</h3>", unsafe_allow_html=True)
    if total_count == 0:
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin: 0;'>등록된 과제가 없습니다. 아래 메뉴에서 새로운 과제를 등록해 보세요.</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color: #4E5968; font-size: 15px; margin: 0;'>현재 <b>{active_count}개</b>의 진행 중인 과제가 있습니다.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("오늘의 할 일", key="btn_home_todo"):
            set_page("todo")

    with col2:
        if st.button("과제 등록", key="btn_home_add"):
            set_page("add")

    with col3:
        if st.button("월간 캘린더", key="btn_home_cal"):
            st.session_state.selected_calendar_date = None
            set_page("calendar")

    with col4:
        if st.button("일정 관리", key="btn_home_schedule"):
            set_page("schedule")


# ==========================================
# 2. 해야 할 일 페이지 (To-Do)
# ==========================================
elif st.session_state.current_page == "todo":
    st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
    if st.button("←", key="back_from_todo"):
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-size: 22px; font-weight: 800; color: #191F28; margin-top: 12px; margin-bottom: 16px;'>해야 할 일</h3>", unsafe_allow_html=True)

    if not user_tasks:
        st.markdown(
            """
            <div class="tds-card" style="text-align: center; padding: 40px 20px;">
                <p style="font-size: 15px; color: #8B95A1; margin: 0;">등록된 과제가 없습니다.<br>과제 등록 페이지에서 새로운 과제를 추가해 보세요.</p>
            </div>
            """,
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
                st.markdown(
                    f"<p style='color: #8B95A1; font-size: 13px; text-align: right; margin-top: -8px; margin-bottom: 16px;'>"
                    f"진행률 {progress * 100:.1f}% ({comp_amt}/{tot_amt} {task['unit']})</p>",
                    unsafe_allow_html=True
                )
                
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
                        st.markdown("<div class='record-btn'>", unsafe_allow_html=True)
                        if st.button("기록", key=f"btn_{idx}"):
                            task['completed_amount'] = comp_amt + today_add
                            save_json(TASK_FILE, st.session_state.tasks)
                            st.success("기록 되었습니다.")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                    if st.button("삭제", key=f"del_{idx}"):
                        st.session_state.tasks = [t for t in st.session_state.tasks if t != task]
                        save_json(TASK_FILE, st.session_state.tasks)
                        st.success("삭제 되었습니다.")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# 3. 과제 등록 페이지 (Add Task)
# ==========================================
elif st.session_state.current_page == "add":
    st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
    if st.button("←", key="back_from_add"):
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 16px;'>새로운 과제 추가</h3>", unsafe_allow_html=True)
    
    with st.form("add_task_form_page"):
        title = st.text_input("과제 이름", placeholder="예: 수학 문제집")
        unit_choice = st.radio("기본 분량 단위 선택", ["페이지", "문제 수"], horizontal=True)
        total_input = st.text_input("총 분량", placeholder="예: 100페이지, 300문제 수 또는 숫자 100만 입력")
        end_date = st.date_input("마감일")
        
        submitted = st.form_submit_button("과제 등록")
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
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# 4. 일정 관리 페이지 (Schedule Management)
# ==========================================
elif st.session_state.current_page == "schedule":
    st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
    if st.button("←", key="back_from_schedule"):
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 4px;'>주간 학습 일정 변경</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 20px;'>바뀐 일정에 맞춰 요일별 학습 가능 시간(시간 단위)을 수정해 보세요.</p>", unsafe_allow_html=True)

    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    updated_schedule = {}
    
    cols_update = st.columns(7)
    for idx, dname in enumerate(day_names):
        cur_h = user_schedule.get(dname, 3)
        updated_schedule[dname] = cols_update[idx].number_input(f"{dname}", min_value=0, max_value=24, value=cur_h, key=f"update_sch_{dname}")

    st.markdown("<div class='save-btn' style='margin-top: 20px;'>", unsafe_allow_html=True)
    if st.button("일정 저장", key="btn_save_schedule"):
        st.session_state.users[st.session_state.current_user]["schedule"] = updated_schedule
        save_json(USER_FILE, st.session_state.users)
        st.success("주간 학습 일정이 업데이트되었습니다.")
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# 5. 캘린더 페이지 (Calendar)
# ==========================================
elif st.session_state.current_page == "calendar":
    
    # 5-A. 상세 화면
    if st.session_state.selected_calendar_date is not None:
        selected_date_str = st.session_state.selected_calendar_date
        
        st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
        if st.button("←", key="back_to_cal_grid"):
            st.session_state.selected_calendar_date = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='font-size: 22px; font-weight: 800; color: #191F28; margin-bottom: 4px;'>{selected_date_str} 마감 과제 상세</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 24px;'>선택하신 날짜에 마감되는 과제의 상세 현황입니다.</p>", unsafe_allow_html=True)

        day_tasks = [t for t in user_tasks if t['end_date'] == selected_date_str]
        
        if not day_tasks:
            st.markdown(
                """
                <div style="text-align: center; padding: 40px 20px;">
                    <p style="font-size: 15px; color: #8B95A1; margin: 0;">이 날짜에 마감 예정인 과제가 없습니다.</p>
                </div>
                """,
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
                    st.markdown(
                        f"<p style='color: #8B95A1; font-size: 13px; text-align: right; margin-top: -8px; margin-bottom: 16px;'>"
                        f"진행률 {progress * 100:.1f}% ({comp_amt}/{tot_amt} {task['unit']})</p>",
                        unsafe_allow_html=True
                    )
                    
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
                            st.markdown("<div class='record-btn'>", unsafe_allow_html=True)
                            if st.button("기록", key=f"cal_dt_btn_{idx}"):
                                task['completed_amount'] = comp_amt + today_add
                                save_json(TASK_FILE, st.session_state.tasks)
                                st.success("기록 되었습니다.")
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                        if st.button("삭제", key=f"cal_dt_del_{idx}"):
                            st.session_state.tasks = [t for t in st.session_state.tasks if t != task]
                            save_json(TASK_FILE, st.session_state.tasks)
                            st.success("삭제 되었습니다.")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 5-B. 월간 그리드 캘린더
    else:
        st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
        if st.button("←", key="back_from_cal_main"):
            set_page("home")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 12px;'>", unsafe_allow_html=True)
        
        col_prev, col_title, col_next = st.columns([1, 3, 1])
        with col_prev:
            st.markdown("<div class='month-nav-btn'>", unsafe_allow_html=True)
            if st.button("이전달", key="prev_month"):
                if st.session_state.cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_title:
            st.markdown("<div class='month-popover' style='text-align: center;'>", unsafe_allow_html=True)
            with st.popover(f"{st.session_state.cal_year}년 {st.session_state.cal_month}월"):
                st.markdown("<p style='font-size: 14px; font-weight: 700; margin-bottom: 8px; color: #191F28;'>이동할 연/월 선택</p>", unsafe_allow_html=True)
                c_y, c_m = st.columns(2)
                with c_y:
                    sel_y = st.selectbox("연도", range(2023, 2031), index=range(2023, 2031).index(st.session_state.cal_year) if st.session_state.cal_year in range(2023, 2031) else 3, key="pop_sel_y")
                with c_m:
                    sel_m = st.selectbox("월", range(1, 13), index=st.session_state.cal_month - 1, key="pop_sel_m")
                
                if st.button("이동", key="btn_apply_popover_month"):
                    st.session_state.cal_year = sel_y
                    st.session_state.cal_month = sel_m
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_next:
            st.markdown("<div class='month-nav-btn'>", unsafe_allow_html=True)
            if st.button("다음달", key="next_month"):
                if st.session_state.cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        task_map = {}
        for task in user_tasks:
            ed = task['end_date']
            if ed not in task_map:
                task_map[ed] = []
            task_map[ed].append(task)

        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        col_head = st.columns(7)
        for idx, day_name in enumerate(weekdays):
            color = "#F43F5E" if idx == 0 else ("#3182F6" if idx == 6 else "#191F28")
            col_head[idx].markdown(
                f"<p style='text-align: left; font-weight: 600; font-size: 13px; color: {color}; margin-top: 12px; margin-bottom: 8px; padding-left: 4px;'>{day_name}</p>",
                unsafe_allow_html=True
            )

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
                            task_titles.append(f"▪ {t_name}")
                        cell_label += "\n".join(task_titles)
                        if len(day_tasks) > 2:
                            cell_label += f"\n+{len(day_tasks)-2}개"
                    
                    if cols[idx].button(cell_label, key=f"cal_grid_{date_str}"):
                        st.session_state.selected_calendar_date = date_str
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
