import streamlit as st
import json
import math
import re
import calendar
from datetime import datetime, date

# 1. 페이지 기본 설정 (이모티콘 전면 금지)
st.set_page_config(page_title="PACE MAKER", layout="centered")

# 2. 토스 디자인 시스템(TDS) 및 홈/캘린더 커스텀 CSS
tds_style = """
<style>
    /* 전체 배경색 및 폰트 */
    .stApp {
        background-color: #F2F4F6 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Pretendard", sans-serif;
        color: #191F28;
    }
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 720px !important;
    }

    /* 카드 컨테이너 스타일 */
    .tds-card {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        border: 1px solid #E5E8EB;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }

    /* 서브 버튼 (홈으로 이동 / 월 변경) */
    div.sub-btn > button {
        background-color: #E8F3FF !important;
        color: #3182F6 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 8px 14px !important;
        font-size: 14px !important;
    }
    div.sub-btn > button:hover {
        background-color: #DCEBFF !important;
    }

    /* 삭제 버튼 */
    div.delete-btn > button {
        background-color: #FFF1F2 !important;
        color: #F43F5E !important;
        border: 1px solid #FFE4E6 !important;
        border-radius: 10px !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
    }
    div.delete-btn > button:hover {
        background-color: #FFE4E6 !important;
        color: #E11D48 !important;
    }

    /* 
       [홈 화면 3열 가로 버튼 전용 CSS]
       설명 없이 카드 형태로 누를 수 있는 3개의 큰 버튼
    */
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)) {
        gap: 12px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)) button {
        background-color: #FFFFFF !important;
        color: #191F28 !important;
        border: 1px solid #E5E8EB !important;
        border-radius: 18px !important;
        height: 110px !important;
        min-height: 110px !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)) button:hover {
        background-color: #F8FAFC !important;
        border-color: #3182F6 !important;
        color: #3182F6 !important;
    }

    /* 일반 폼 제출 및 서브페이지 버튼 */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #3182F6;
        color: #FFFFFF;
        border-radius: 12px;
        border: none;
        font-weight: 600;
        font-size: 14px;
        padding: 10px 16px;
        width: 100%;
        transition: all 0.2s ease;
    }

    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1B64DA;
    }

    /* 캘린더 7열 그리드 CSS */
    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(7)) {
        gap: 4px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(7)) > div[data-testid="stColumn"] {
        padding: 0px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(7)) button {
        width: 100% !important;
        background-color: #FFFFFF !important;
        color: #191F28 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        min-height: 85px !important;
        height: 85px !important;
        padding: 6px !important;
        text-align: left !important;
        font-size: 12px !important;
        line-height: 1.3 !important;
        white-space: pre-wrap !important;
        word-break: break-all !important;
        box-shadow: none !important;
        display: block !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(7)) button:hover:not(:disabled) {
        background-color: #F8FAFC !important;
        border-color: #3182F6 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(7)) button:disabled {
        background-color: #FAFAFA !important;
        border-color: #F1F5F9 !important;
        cursor: default !important;
        opacity: 0.4 !important;
    }

    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        border: 1px solid #E5E8EB !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
        margin-bottom: 16px !important;
        overflow: hidden;
    }
    
    div[data-testid="stExpander"] > details {
        border: none !important;
    }

    div[data-testid="stMetricValue"] {
        color: #3182F6 !important;
        font-size: 24px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #8B95A1 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    div[data-testid="stProgressBar"] > div > div {
        background-color: #3182F6 !important;
        border-radius: 10px !important;
    }
</style>
"""
st.markdown(tds_style, unsafe_allow_html=True)

FILENAME = "tasks.json"

# 데이터 불러오기
def load_tasks():
    try:
        with open(FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 데이터 저장하기
def save_tasks(tasks):
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# 분량 및 단위 파싱 함수
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

# 세션 상태 초기화
if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

today_obj = date.today()
if "cal_year" not in st.session_state:
    st.session_state.cal_year = today_obj.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = today_obj.month
if "selected_calendar_date" not in st.session_state:
    st.session_state.selected_calendar_date = None

# 페이지 이동 함수
def set_page(page_name):
    st.session_state.current_page = page_name
    st.rerun()


# ==========================================
# 1. 홈 화면 (Home)
# ==========================================
if st.session_state.current_page == "home":
    # 대형 PM 로고 및 대형 PACE MAKER 타이틀
    st.markdown(
        """
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 16px; margin-bottom: 32px;">
            <div style="background-color: #3182F6; color: #FFFFFF; font-weight: 900; font-size: 32px; width: 72px; height: 72px; border-radius: 22px; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 20px rgba(49, 130, 246, 0.35); margin-bottom: 16px; letter-spacing: -1px;">PM</div>
            <h1 style="font-weight: 900; color: #191F28; font-size: 36px; margin: 0 0 8px 0; text-align: center; letter-spacing: -0.5px;">PACE MAKER</h1>
            <p style="color: #8B95A1; font-size: 15px; margin: 0; text-align: center;">목표가 틀어져도 괜찮습니다. 오늘 할 일을 유연하게 맞춰드립니다.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 학습 현황 요약
    tasks = st.session_state.tasks
    total_count = len(tasks)
    active_count = sum(1 for t in tasks if (int(t['total_amount']) - int(t['completed_amount'])) > 0)
    
    st.markdown("<div class='tds-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 17px; font-weight: 700; color: #191F28; margin-bottom: 6px;'>학습 현황 요약</h3>", unsafe_allow_html=True)
    if total_count == 0:
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin: 0;'>등록된 과제가 없습니다. 아래 메뉴에서 새로운 과제를 등록해 보세요.</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color: #4E5968; font-size: 15px; margin: 0;'>현재 <b>{active_count}개</b>의 진행 중인 과제가 있습니다.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 3개 항목 가로 배치 (버튼 자체가 항목 클릭 카드 역할)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("해야 할 일", key="btn_home_todo"):
            set_page("todo")

    with col2:
        if st.button("과제 등록", key="btn_home_add"):
            set_page("add")

    with col3:
        if st.button("캘린더", key="btn_home_cal"):
            st.session_state.selected_calendar_date = None
            set_page("calendar")


# ==========================================
# 2. 해야 할 일 페이지 (To-Do)
# ==========================================
elif st.session_state.current_page == "todo":
    st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
    if st.button("홈으로 돌아가기", key="back_from_todo"):
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-size: 22px; font-weight: 800; color: #191F28; margin-top: 16px; margin-bottom: 16px;'>해야 할 일</h3>", unsafe_allow_html=True)

    if not st.session_state.tasks:
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
        for idx, task in enumerate(st.session_state.tasks):
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
                        daily_target = math.ceil(remaining_amount / remaining_days)
                        st.metric(label="오늘의 추천 목표", value=f"{daily_target} {task['unit']}")
                        st.caption(f"남은 기간 D-{remaining_days}일")

                with col2:
                    if remaining_amount > 0 and end_date >= today and remaining_days > 0:
                        today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0, value=0, step=1, key=f"input_{idx}")
                        if st.button("기록하기", key=f"btn_{idx}"):
                            task['completed_amount'] = comp_amt + today_add
                            save_tasks(st.session_state.tasks)
                            st.success("기록되었습니다.")
                            st.rerun()
                    
                    st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                    if st.button("과제 삭제", key=f"del_{idx}"):
                        st.session_state.tasks.pop(idx)
                        save_tasks(st.session_state.tasks)
                        st.success("과제가 삭제되었습니다.")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# 3. 과제 등록 페이지 (Add Task)
# ==========================================
elif st.session_state.current_page == "add":
    st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
    if st.button("홈으로 돌아가기", key="back_from_add"):
        set_page("home")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='tds-card' style='margin-top: 16px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 16px;'>새로운 과제 추가</h3>", unsafe_allow_html=True)
    
    with st.form("add_task_form_page"):
        title = st.text_input("과제 이름", placeholder="예: 수학 문제집")
        unit_choice = st.radio("기본 분량 단위 선택", ["페이지", "문제 수"], horizontal=True)
        total_input = st.text_input("총 분량", placeholder="예: 100페이지, 300문제 수 또는 숫자 100만 입력")
        end_date = st.date_input("마감일")
        
        submitted = st.form_submit_button("과제 등록하기")
        if submitted:
            parsed_amount, parsed_unit = parse_amount_and_unit(total_input, unit_choice)
            
            if not title.strip():
                st.warning("과제 이름을 입력해 주세요.")
            elif parsed_amount is None or parsed_amount <= 0:
                st.warning("총 분량을 올바른 형식(예: 100, 100페이지, 300문제)으로 입력해 주세요.")
            else:
                new_task = {
                    "title": title.strip(),
                    "unit": parsed_unit,
                    "total_amount": int(parsed_amount),
                    "completed_amount": 0,
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.success(f"'{title}' 과제가 추가되었습니다.")
                set_page("todo")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# 4. 캘린더 페이지 (Calendar)
# ==========================================
elif st.session_state.current_page == "calendar":
    
    # ------------------------------------------
    # 4-A. 격자 칸 클릭 시: 과제 세부사항 큰 화면 (Detail View)
    # ------------------------------------------
    if st.session_state.selected_calendar_date is not None:
        selected_date_str = st.session_state.selected_calendar_date
        
        st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
        if st.button("캘린더로 돌아가기", key="back_to_cal_grid"):
            st.session_state.selected_calendar_date = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 16px;'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='font-size: 22px; font-weight: 800; color: #191F28; margin-bottom: 4px;'>{selected_date_str} 마감 과제 상세</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 24px;'>선택하신 날짜에 마감되는 과제의 상세 현황입니다.</p>", unsafe_allow_html=True)

        day_tasks = [t for t in st.session_state.tasks if t['end_date'] == selected_date_str]
        
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
                            daily_target = math.ceil(remaining_amount / remaining_days)
                            st.metric(label="오늘의 추천 목표", value=f"{daily_target} {task['unit']}")
                            st.caption(f"남은 기간 D-{remaining_days}일")

                    with col2:
                        if remaining_amount > 0 and sel_date_obj >= today and remaining_days > 0:
                            today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0, value=0, step=1, key=f"cal_dt_input_{idx}")
                            if st.button("기록하기", key=f"cal_dt_btn_{idx}"):
                                task['completed_amount'] = comp_amt + today_add
                                save_tasks(st.session_state.tasks)
                                st.success("기록되었습니다.")
                                st.rerun()
                        
                        st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                        if st.button("과제 삭제", key=f"cal_dt_del_{idx}"):
                            st.session_state.tasks = [t for t in st.session_state.tasks if not (t['title'] == task['title'] and t['end_date'] == task['end_date'])]
                            save_tasks(st.session_state.tasks)
                            st.success("과제가 삭제되었습니다.")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 4-B. 월간 격자 캘린더 (Grid View)
    # ------------------------------------------
    else:
        st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
        if st.button("홈으로 돌아가기", key="back_from_cal_main"):
            set_page("home")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 16px;'>", unsafe_allow_html=True)
        
        col_prev, col_title, col_next = st.columns([1, 3, 1])
        with col_prev:
            st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
            if st.button("이전달", key="prev_month"):
                if st.session_state.cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_title:
            st.markdown(
                f"<h3 style='font-size: 18px; font-weight: 700; color: #191F28; text-align: center; margin: 6px 0;'>"
                f"{st.session_state.cal_year}년 {st.session_state.cal_month}월</h3>",
                unsafe_allow_html=True
            )

        with col_next:
            st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
            if st.button("다음달", key="next_month"):
                if st.session_state.cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        task_map = {}
        for task in st.session_state.tasks:
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
