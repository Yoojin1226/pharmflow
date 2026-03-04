import streamlit as st
import time

# --- [초기 설정] ---
st.set_page_config(page_title="PharmFlow - 환자용", layout="centered")

# 단계별 진행을 위해 'step'이라는 기억 장치를 만듭니다.
if 'step' not in st.session_state:
    st.session_state.step = 'upload'  # 시작은 업로드 단계
if 'selected_pharmacy' not in st.session_state:
    st.session_state.selected_pharmacy = None
if 'final_time' not in st.session_state:
    st.session_state.final_time = 0

# 예상 조제 시간 산출 함수 [cite: 121]
def calculate_estimated_time(avg_time, current_queue, num_pharmacists):
    if num_pharmacists == 0: return 999
    return int((current_queue * avg_time) / num_pharmacists + 5)

# --- [화면 시작] ---
st.title("💊 PharmFlow (팜플로우)")

# --- [1단계: 업로드 페이지] ---
if st.session_state.step == 'upload':
    st.subheader("📸 1. 처방전 업로드")
    uploaded_file = st.file_uploader("처방전 사진을 올려주세요.", type=['jpg', 'png', 'jpeg'])
    
    if uploaded_file:
        st.image(uploaded_file, caption='처방전 확인', use_container_width=True)
        if st.button("인근 약국 찾기"):
            st.session_state.step = 'results' # 2단계로 이동
            st.rerun()

# --- [2단계: 약국 선택 페이지] ---
elif st.session_state.step == 'results':
    st.subheader("🔍 2. 최적 약국 선택")
    st.info("실시간 응답 데이터를 기반으로 대기 시간을 산출했습니다.") # [cite: 20]
    
    pharmacy_list = [
        {"name": "A 약국 (문전/혼잡)", "avg_time": 10, "queue": 15, "staff": 2, "type": "A"},
        {"name": "B 약국 (팜플로우 추천)", "avg_time": 8, "queue": 2, "staff": 2, "type": "B"}
    ]

    for pharm in pharmacy_list:
        est_time = calculate_estimated_time(pharm["avg_time"], pharm["queue"], pharm["staff"])
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{pharm['name']}**")
                if pharm['type'] == "B":
                    st.caption("✨ B급 입지 약국으로 대기 시간이 매우 짧습니다.") # [cite: 18]
            with col2:
                st.subheader(f"{est_time}분")
            
            if st.button(f"{pharm['name']} 조제 요청", key=f"btn_{pharm['name']}"):
                st.session_state.selected_pharmacy = pharm['name']
                st.session_state.final_time = est_time
                st.session_state.step = 'final' # 3단계로 이동
                st.rerun()

    if st.button("← 다시 업로드하기"):
        st.session_state.step = 'upload'
        st.rerun()

# --- [3단계: 최종 완료 페이지 - 여기가 안 뜨던 부분!] ---
elif st.session_state.step == 'final':
    st.subheader("✅ 3. 예약 완료")
    st.balloons() # 축하 효과
    
    # 요청하신 예상 완료 시간 표시 [cite: 25]
    min_t = max(5, st.session_state.final_time - 2)
    max_t = st.session_state.final_time + 5
    
    with st.container(border=True):
        st.markdown(f"### ⏱️ **{min_t}~{max_t}분 후 예약하신 약이 완료됩니다.**")
        st.write(f"지정하신 **[{st.session_state.selected_pharmacy}]**으로 데이터 전송이 끝났습니다.")
        st.caption("약국에 도착하시면 성함을 말씀해 주세요.")
    
    if st.button("처음으로 돌아가기"):
        st.session_state.step = 'upload'
        st.session_state.selected_pharmacy = None
        st.rerun()