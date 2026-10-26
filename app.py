import streamlit as st
import json
import math
from datetime import datetime, date

# 스트림릿 페이지 설정
st.set_page_config(page_title="PACE MAKER", page_icon="🏃‍♂️", layout="centered")

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

# 세션 상태 데이터 초기화
if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

# 메인 타이틀
st.title("🏃‍♂️ PACE MAKER")
st.caption("계획이 틀어져도 괜찮아요. 오늘 할 일을 알아서 다시 계산해 드립니다!")

# --- [사이드바: 과제 등록] ---
with st.sidebar:
    st.header("➕ 새 과제 등록")
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
                st.success(f"'{title}' 과제가 등록되었습니다!")
                st.rerun()

# --- [메인 영역: 과제 대시보드 및 수행량 기록] ---
st.subheader("📊 과제 진행 대시보드")

if not st.session_state.tasks:
    st.info("👈 왼쪽 사이드바에서 첫 과제를 등록해 보세요!")
else:
    today = date.today()
    for idx, task in enumerate(st.session_state.tasks):
        with st.expander(f"📌 **{task['title']}**", expanded=True):
            end_date = datetime.strptime(task['end_date'], "%Y-%m-%d").date()
            remaining_days = (end_date - today).days + 1 - task['rest_days']
            remaining_amount = task['total_amount'] - task['completed_amount']
            
            # 진행률 계산 및 프로그레스 바 표시
            progress = min(1.0, max(0.0, task['completed_amount'] / task['total_amount']))
            st.progress(progress, text=f"진행률: {progress * 100:.1f}% ({task['completed_amount']} / {task['total_amount']} {task['unit']})")
            
            col1, col2 = st.columns(2)
            
            # 연산 및 상태 출력
            with col1:
                if remaining_amount <= 0:
                    st.balloons()
                    st.success("🎉 과제를 모두 완료했습니다!")
                elif remaining_days <= 0:
                    st.error("🚨 마감 기한이 지났습니다!")
                else:
                    daily_target = math.ceil(remaining_amount / remaining_days)
                    st.metric(label="오늘의 PACE MAKER 목표", value=f"하루 {daily_target} {task['unit']}")
                    st.caption(f"남은 유효 기간: D-{remaining_days}일 (휴식일 차감)")

            # 수행량 입력
            with col2:
                if remaining_amount > 0 and remaining_days > 0:
                    st.write("**오늘 진행한 양 입력**")
                    today_add = st.number_input(f"진행량 ({task['unit']})", min_value=0.0, key=f"input_{idx}")
                    if st.button("기록 반영", key=f"btn_{idx}"):
                        task['completed_amount'] += today_add
                        save_tasks(st.session_state.tasks)
                        st.success("기록되었습니다!")
                        st.rerun()
