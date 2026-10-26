import streamlit as st
import json
import math
from datetime import datetime, date, timedelta

# 1. 페이지 기본 설정 (이모티콘 제거)
st.set_page_config(page_title="PACE MAKER", layout="centered")

# 2. 토스 디자인 시스템(TDS) 커스텀 CSS
tds_style = """
<style>
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

    /* 토스 블루 기본 버튼 */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #3182F6 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 16px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1B64DA !important;
        color: #FFFFFF !important;
    }

    /* 삭제 버튼 전용 서브 스타일 */
    div.delete-btn > button {
        background-color: #FFF1F2 !important;
        color: #F43F5E !important;
        border: 1px solid #FFE4E6 !important;
    }
    div.delete-btn > button:hover {
        background-color: #FFE4E6 !important;
        color: #E11D48 !important;
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

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E8EB !important;
    }

    div[data-testid="stProgressBar"] > div > div {
        background-color: #3182F6 !important;
        border-radius: 10px !important;
    }
</style>
"""
st.markdown(tds_style, unsafe_allow_html=True)

FILENAME = "tasks.json"

# [저장 모듈] 데이터 불러오기
def load_tasks():
    try:
        with open(FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# [저장 모듈] 데이터 저장하기
def save_tasks(tasks):
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# 유효 작업 일수 계산 로직 (주말 제외 옵션 포함)
def calculate_valid_days(start_date, end_date, exclude_weekends, custom_rest_days):
    if start_date > end_date:
        return 0
    
    current = start_date
    valid_days = 0
    while current <= end_date:
        # 주말 제외 체크 옵션이 켜져 있으면 토요일(5), 일요일(6) 제외
        if exclude_weekends and current.weekday() >= 5:
            pass
        else:
            valid_days += 1
        current += timedelta(days=1)
        
    return max(0, valid_days - custom_rest_days)

if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

# --- [상단 타이틀 영역] ---
st.markdown("<h2 style='font-weight: 700; color: #191F28; margin-bottom: 4px;'>PACE MAKER</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #8B95A1; font-size: 15px; margin-bottom: 24px;'>목표가 틀어져도 괜찮습니다. 오늘 할 일을 유연하게 맞춰드립니다.</p>", unsafe_allow_html=True)

# --- [사이드바: 과제 추가 모듈] ---
with st.sidebar:
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28;'>새 과제 추가</h3>", unsafe_allow_html=True)
    
    with st.form("add_task_form"):
        title = st.text_input("과제 이름", placeholder="예: 수학 문제집 300제")
        unit = st.text_input("분량 단위", value="페이지")
        total_amount = st.number_input("총 분량", min_value=1.0, value=100.0)
        end_date = st.date_input("마감일")
        
        st.markdown("<p style='font-size: 13px; color: #8B95A1; margin-top: 8px; margin-bottom: 0px;'>일정 옵션</p>", unsafe_allow_html=True)
        exclude_weekends = st.checkbox("주말(토/일) 자동 제외", value=False)
        rest_days = st.number_input("추가 휴식일 수", min_value=0, value=0)
        
        submitted = st.form_submit_button("과제 등록하기")
        if submitted:
            if not title.strip():
                st.warning("과제 이름을 입력해 주세요.")
            else:
                new_task = {
                    "title": title,
                    "unit": unit,
                    "total_amount": float(total_amount),
                    "completed_amount": 0.0,
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "exclude_weekends": exclude_weekends,
                    "rest_days": int(rest_days)
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.success(f"'{title}' 과제가 추가되었습니다.")
                st.rerun()

# --- [메인 영역: 과제 대시보드 및 관리] ---
if not st.session_state.tasks:
    st.markdown(
        """
        <div style="background-color: #FFFFFF; padding: 40px 20px; border-radius: 20px; text-align: center; border: 1px solid #E5E8EB;">
            <p style="font-size: 15px; color: #8B95A1; margin: 0;">등록된 과제가 없습니다.<br>사이드바에서 새로운 과제를 등록해 보세요.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    today = date.today()
    for idx, task in enumerate(st.session_state.tasks):
        end_date = datetime.strptime(task['end_date'], "%Y-%m-%d").date()
        exclude_weekends = task.get('exclude_weekends', False)
        rest_days = task.get('rest_days', 0)
        
        remaining_days = calculate_valid_days(today, end_date, exclude_weekends, rest_days)
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
                    
                    option_info = []
                    if exclude_weekends:
                        option_info.append("주말 제외")
                    if rest_days > 0:
                        option_info.append(f"휴식일 {rest_days}일")
                    
                    info_str = f"남은 유효 기간 D-{remaining_days}일"
                    if option_info:
                        info_str += f" ({', '.join(option_info)})"
                    st.caption(info_str)

            with col2:
                if remaining_amount > 0 and end_date >= today and remaining_days > 0:
                    today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0.0, key=f"input_{idx}", value=0.0)
                    if st.button("기록하기", key=f"btn_{idx}"):
                        task['completed_amount'] += today_add
                        save_tasks(st.session_state.tasks)
                        st.success("기록되었습니다.")
                        st.rerun()
                
                # 과제 삭제 버튼
                st.markdown("<div class='delete-btn' style='margin-top: 8px;'>", unsafe_allow_html=True)
                if st.button("과제 삭제", key=f"del_{idx}"):
                    st.session_state.tasks.pop(idx)
                    save_tasks(st.session_state.tasks)
                    st.success("과제가 삭제되었습니다.")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
