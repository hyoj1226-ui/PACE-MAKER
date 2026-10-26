import streamlit as st
import json
import math
from datetime import datetime, date

# 1. 페이지 기본 설정
st.set_page_config(page_title="PACE MAKER", page_icon="🏃‍♂️", layout="centered")

# 2. 토스 디자인 시스템(TDS) 스타일 커스텀 CSS 주입
tds_style = """
<style>
    /* 전체 배경색 및 폰트 설정 */
    .stApp {
        background-color: #F2F4F6 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Pretendard", sans-serif;
        color: #191F28;
    }
    
    /* 상단 헤더 영역 여백 조정 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 680px !important;
    }

    /* 토스 스타일 카드 용 컨테이너 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {
        border-radius: 20px;
    }

    /* Expander(카드) 스타일 변경 */
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

    /* 버튼 스타일 (토스 블루) */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #3182F6 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 10px 16px !important;
        width: 100% !important;
        box-shadow: 0 2px 6px rgba(49, 130, 246, 0.2) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1B64DA !important;
        color: #FFFFFF !important;
    }

    /* 메트릭(숫자 강조) 디자인 */
    div[data-testid="stMetricValue"] {
        color: #3182F6 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #8B95A1 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E8EB !important;
    }

    /* 입력 폼 필드 스타일 */
    input, select {
        border-radius: 10px !important;
        border: 1px solid #E5E8EB !important;
    }

    /* 프로그레스 바 컬러 */
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

if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

# --- [상단 타이틀 영역] ---
st.markdown("<h2 style='font-weight: 700; color: #191F28; margin-bottom: 4px;'>🏃‍♂️ PACE MAKER</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #8B95A1; font-size: 15px; margin-bottom: 24px;'>목표가 틀어져도 괜찮아요. 오늘 할 일을 유연하게 맞춰드려요.</p>", unsafe_allow_html=True)

# --- [사이드바: 과제 등록] ---
with st.sidebar:
    st.markdown("<h3 style='font-size: 18px; font-weight: 700; color: #191F28;'>➕ 새 과제 추가</h3>", unsafe_allow_html=True)
    st.caption("새로운 과제나 학습 목표를 등록해 보세요.")
    
    with st.form("add_task_form"):
        title = st.text_input("과제 이름", placeholder="예: 수학 문제집 300제")
        unit = st.text_input("분량 단위", value="페이지")
        total_amount = st.number_input("총 분량", min_value=1.0, value=100.0)
        end_date = st.date_input("마감일")
        rest_days = st.number_input("예정된 휴식일 수", min_value=0, value=0)
        
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
                    "rest_days": int(rest_days)
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.success(f"'{title}' 과제가 추가되었습니다.")
                st.rerun()

# --- [메인 영역: 과제 카드 목록] ---
if not st.session_state.tasks:
    st.markdown(
        """
        <div style="background-color: #FFFFFF; padding: 40px 20px; border-radius: 20px; text-align: center; border: 1px solid #E5E8EB;">
            <p style="font-size: 16px; color: #8B95A1; margin: 0;">등록된 과제가 없습니다.<br>왼쪽 사이드바에서 첫 과제를 등록해 보세요!</p>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    today = date.today()
    for idx, task in enumerate(st.session_state.tasks):
        end_date = datetime.strptime(task['end_date'], "%Y-%m-%d").date()
        remaining_days = (end_date - today).days + 1 - task['rest_days']
        remaining_amount = task['total_amount'] - task['completed_amount']
        
        progress = min(1.0, max(0.0, task['completed_amount'] / task['total_amount']))
        
        with st.expander(f"📌 **{task['title']}**", expanded=True):
            # 진행률 프로그레스 바
            st.progress(progress)
            st.markdown(
                f"<p style='color: #8B95A1; font-size: 13px; text-align: right; margin-top: -8px; margin-bottom: 16px;'>"
                f"진행률 {progress * 100:.1f}% ({task['completed_amount']:.0f}/{task['total_amount']:.0f} {task['unit']})</p>",
                unsafe_allow_html=True
            )
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if remaining_amount <= 0:
                    st.balloons()
                    st.success("🎉 과제를 모두 완료했습니다!")
                elif remaining_days <= 0:
                    st.error("🚨 마감 기한이 지났습니다.")
                else:
                    daily_target = math.ceil(remaining_amount / remaining_days)
                    st.metric(label="오늘의 추천 목표", value=f"{daily_target} {task['unit']}")
                    st.caption(f"D-{remaining_days}일 남음 (휴식일 제외)")

            with col2:
                if remaining_amount > 0 and remaining_days > 0:
                    today_add = st.number_input(f"오늘 한 양 ({task['unit']})", min_value=0.0, key=f"input_{idx}", value=0.0)
                    if st.button("기록하기", key=f"btn_{idx}"):
                        task['completed_amount'] += today_add
                        save_tasks(st.session_state.tasks)
                        st.success("기록되었어요!")
                        st.rerun()
