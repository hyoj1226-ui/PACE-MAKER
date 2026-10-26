import streamlit as st
import json
import math
import re
import calendar
from datetime import datetime, date

# 1. 페이지 기본 설정
st.set_page_config(page_title="PACE MAKER", layout="centered")

# 2. 토스 디자인 시스템(TDS) 및 네이버 캘린더 스타일 CSS
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
        max-width: 680px !important;
    }

    /* 카드 컨테이너 스타일 */
    .tds-card {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        border: 1px solid #E5E8EB;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
        margin-bottom: 16px;
    }

    /* 토스 블루 기본 버튼 */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #3182F6 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1B64DA !important;
        color: #FFFFFF !important;
    }

    /* 서브 버튼 (홈으로 이동 / 월 변경용) */
    div.sub-btn > button {
        background-color: #E8F3FF !important;
        color: #3182F6 !important;
        border: none !important;
    }
    div.sub-btn > button:hover {
        background-color: #DCEBFF !important;
    }

    /* 삭제 버튼 */
    div.delete-btn > button {
        background-color: #FFF1F2 !important;
        color: #F43F5E !important;
        border: 1px solid #FFE4E6 !important;
    }
    div.delete-btn > button:hover {
        background-color: #FFE4E6 !important;
        color: #E11D48 !important;
    }

    /* 달력 그리드 칸 커스텀 (이미지 스타일 구현) */
    div.cal-cell > button {
        background-color: #FFFFFF !important;
        color: #191F28 !important;
        border: 1px solid #E5E8EB !important;
        border-radius: 8px !important;
        min-height: 85px !important;
        padding: 6px 4px !important;
        text-align: left !important;
        font-size: 12px !important;
        line-height: 1.4 !important;
        white-space: pre-wrap !important;
        word-break: break-all !important;
        box-shadow: none !important;
    }
    div.cal-cell > button:hover {
        border-color: #3182F6 !important;
        background-color: #F8F9FA !important;
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
    
    amount = float(match.group(1))
    
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

# --- [상단 타이틀 헤더] ---
st.markdown("<h1 style='font-weight: 800; color: #191F28; font-size: 26px; margin-bottom: 4px; text-align: center;'>PACE MAKER</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8B95A1; font-size: 14px; text-align: center; margin-bottom: 24px;'>목표가 틀어져도 괜찮습니다. 오늘 할 일을 유연하게 맞춰드립니다.</p>", unsafe_allow_html=True)


# ==========================================
# 1. 홈 화면 (Home)
# ==========================================
if st.session_state.current_page == "home":
    tasks = st.session_state.tasks
    total_count = len(tasks)
    active_count = sum(1 for t in tasks if (t['total_amount'] - t['completed_amount']) > 0)
    
    st.markdown("<div class='tds-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 8px;'>학습 현황 요약</h3>", unsafe_allow_html=True)
    if total_count == 0:
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin: 0;'>등록된 과제가 없습니다. 아래 메뉴에서 새로운 과제를 등록해 보세요.</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color: #4E5968; font-size: 15px; margin: 0;'>현재 <b>{active_count}개</b>의 진행 중인 과제가 있습니다.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<p style='font-weight: 700; font-size: 16px; color: #191F28; margin-top: 24px; margin-bottom: 12px;'>메뉴 선택</p>", unsafe_allow_html=True)

    # 메뉴 1: 해야 할 일
    st.markdown(
        """
        <div class="tds-card" style="margin-bottom: 12px; padding: 20px;">
            <h4 style="margin:0; font-size: 16px; color: #191F28; font-weight: 700;">해야 할 일</h4>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #8B95A1;">오늘의 자동 추천 목표 확인 및 일일 진행량 기록</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("해야 할 일 페이지로 이동", key="btn_go_todo"):
        set_page("todo")

    # 메뉴 2: 과제 등록
    st.markdown(
        """
        <div class="tds-card" style="margin-top: 12px; margin-bottom: 12px; padding: 20px;">
            <h4 style="margin:0; font-size: 16px; color: #191F28; font-weight: 700;">과제 등록</h4>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #8B95A1;">새로운 과제 이름, 총 분량 및 마감일 설정</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("과제 등록 페이지로 이동", key="btn_go_add"):
        set_page("add")

    # 메뉴 3: 캘린더
    st.markdown(
        """
        <div class="tds-card" style="margin-top: 12px; margin-bottom: 12px; padding: 20px;">
            <h4 style="margin:0; font-size: 16px; color: #191F28; font-weight: 700;">캘린더</h4>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #8B95A1;">전체 과제 마감일 및 D-Day 일정표 확인</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("캘린더 페이지로 이동", key="btn_go_calendar"):
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
    
    st.markdown("<h3 style='font-size: 20px; font-weight: 700; color: #191F28; margin-top: 16px; margin-bottom: 16px;'>해야 할 일</h3>", unsafe_allow_html=True)

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
            remaining_amount = task['total_amount'] - task['completed_amount']
            progress = min(1.0, max(0.0, task['completed_amount'] / task['total_amount']))
            
            with st.expander(f"**{task['title']}**", expanded=True):
                st.progress(progress)
                st.markdown(
                    f"<p style='color: #8B95A1; font-size: 13px; text-align: right; margin-top: -8px; margin-bottom: 16px;'>"
                    f"진행률 {progress * 100:.1f}% ({task['completed_amount']:.0f}/{task['total_amount']:.0f} {task['unit']})</p>",
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
                        today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0.0, key=f"input_{idx}", value=0.0)
                        if st.button("기록하기", key=f"btn_{idx}"):
                            task['completed_amount'] += today_add
                            save_tasks(st.session_state.tasks)
                            st.success("기록되었습니다.")
                    
                    st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                    if st.button("과제 삭제", key=f"del_{idx}"):
                        st.session_state.tasks.pop(idx)
                        save_tasks(st.session_state.tasks)
                        st.success("과제가 삭제되었습니다.")
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
                    "total_amount": parsed_amount,
                    "completed_amount": 0.0,
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
    # 4-A. 날짜 선택 시: 세부사항 큰 화면 (Full Detail View)
    # ------------------------------------------
    if st.session_state.selected_calendar_date is not None:
        selected_date_str = st.session_state.selected_calendar_date
        
        # 뒤로가기 버튼
        st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
        if st.button("캘린더로 돌아가기", key="back_to_cal_grid"):
            st.session_state.selected_calendar_date = None
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 16px;'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='font-size: 22px; font-weight: 800; color: #191F28; margin-bottom: 4px;'>{selected_date_str} 마감 과제 상세</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8B95A1; font-size: 14px; margin-bottom: 24px;'>선택하신 날짜에 마감되는 과제의 상세 현황입니다.</p>", unsafe_allow_html=True)

        # 해당 날짜 과제 추출
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
                remaining_amount = task['total_amount'] - task['completed_amount']
                progress = min(1.0, max(0.0, task['completed_amount'] / task['total_amount']))
                
                with st.expander(f"**{task['title']}**", expanded=True):
                    st.progress(progress)
                    st.markdown(
                        f"<p style='color: #8B95A1; font-size: 13px; text-align: right; margin-top: -8px; margin-bottom: 16px;'>"
                        f"진행률 {progress * 100:.1f}% ({task['completed_amount']:.0f}/{task['total_amount']:.0f} {task['unit']})</p>",
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
                            today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0.0, key=f"cal_dt_input_{idx}", value=0.0)
                            if st.button("기록하기", key=f"cal_dt_btn_{idx}"):
                                task['completed_amount'] += today_add
                                save_tasks(st.session_state.tasks)
                                st.success("기록되었습니다.")
                        
                        st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                        if st.button("과제 삭제", key=f"cal_dt_del_{idx}"):
                            # 실제 과제 목록에서 찾아 삭제
                            st.session_state.tasks = [t for t in st.session_state.tasks if not (t['title'] == task['title'] and t['end_date'] == task['end_date'])]
                            save_tasks(st.session_state.tasks)
                            st.success("과제가 삭제되었습니다.")
                        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------
    # 4-B. 날짜 미선택 시: 깔끔한 큰 월간 캘린더 화면 (Grid View)
    # ------------------------------------------
    else:
        st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
        if st.button("홈으로 돌아가기", key="back_from_cal_main"):
            set_page("home")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='tds-card' style='margin-top: 16px;'>", unsafe_allow_html=True)
        
        # 상단 월 변경 컨트롤
        col_prev, col_title, col_next = st.columns([1, 3, 1])
        with col_prev:
            st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
            if st.button("이전달", key="prev_month"):
                if st.session_state.cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
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
            st.markdown("</div>", unsafe_allow_html=True)

        # 마감일별 과제 매핑
        task_map = {}
        for task in st.session_state.tasks:
            ed = task['end_date']
            if ed not in task_map:
                task_map[ed] = []
            task_map[ed].append(task)

        # 요일 헤더 (일~토, 첨부 이미지 색상 반영)
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        col_head = st.columns(7)
        for idx, day_name in enumerate(weekdays):
            color = "#F43F5E" if idx == 0 else ("#3182F6" if idx == 6 else "#191F28")
            col_head[idx].markdown(
                f"<p style='text-align: left; font-weight: 600; font-size: 13px; color: {color}; margin-top: 12px; margin-bottom: 8px; padding-left: 4px;'>{day_name}</p>",
                unsafe_allow_html=True
            )

        # 달력 그리드 출력 (칸 내부에 과제 제목만 표시)
        c = calendar.Calendar(firstweekday=6)
        month_weeks = c.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
        today_str = today_obj.strftime("%Y-%m-%d")

        for week in month_weeks:
            cols = st.columns(7)
            for idx, day in enumerate(week):
                if day == 0:
                    cols[idx].write("")
                else:
                    date_str = f"{st.session_state.cal_year:04d}-{st.session_state.cal_month:02d}-{day:02d}"
                    day_tasks = task_map.get(date_str, [])
                    
                    # 날짜 칸 레이아웃 구성 (과제 제목만 표기)
                    cell_label = f"{day}\n"
                    if day_tasks:
                        task_titles = []
                        for t in day_tasks[:2]:
                            t_name = t['title']
                            if len(t_name) > 6:
                                t_name = t_name[:5] + ".."
                            task_titles.append(f"• {t_name}")
                        cell_label += "\n".join(task_titles)
                        if len(day_tasks) > 2:
                            cell_label += f"\n+{len(day_tasks)-2}개"
                    
                    cols[idx].markdown("<div class='cal-cell'>", unsafe_allow_html=True)
                    if cols[idx].button(cell_label, key=f"cal_grid_{date_str}"):
                        st.session_state.selected_calendar_date = date_str
                    cols[idx].markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
