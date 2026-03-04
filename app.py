import streamlit as st
import pandas as pd
import numpy as np
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="PharmFlow", layout="centered")

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'reservation' not in st.session_state:
    st.session_state.reservation = None

# 예상 조제 시간 산출 함수 [cite: 25, 121]
def get_est_time(avg, queue, staff):
    return int((queue * avg) / staff + 5)

# --- [#1. 로고 화면 & #2. 권한 동의] ---
if st.session_state.step == 1:
    st.title("💊 PharmFlow") # [cite: 1]
    st.write("처방 이후 단계에서 약국 수요를 재배치합니다.") # [cite: 4]
    
    with st.container(border=True):
        st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
        st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
        # 하늘색 확인 버튼 구현
        if st.button("확인", use_container_width=True, type="primary"):
            st.session_state.step = 2
            st.rerun()

# --- [#3. 튜토리얼 & #4. 사진 업로드] ---
elif st.session_state.step == 2:
    st.title("PharmFlow")
    # 튜토리얼 문구 [cite: 29]
    st.info("💡 처방전을 찍어 올리면 빠른 조제 약국을 찾아드려요.")
    
    st.subheader("📸 처방전 업로드")
    uploaded_file = st.file_uploader("이미지를 업로드하거나 촬영하세요.", type=['jpg', 'png', 'jpeg']) # [cite: 21]
    
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        if st.button("분석 시작", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# --- [#5. 지도 표시 및 약국 나열 & #6. 환자 선택] ---
elif st.session_state.step == 3:
    st.subheader("🔍 주변 약국 실시간 현황")
    
    # 가상의 현위치 기준 7개 약국 데이터 (진주 지역 등 가상 좌표)
    # 실제로는 약국 응답 데이터를 활용함 [cite: 23, 111]
    data = {
        '약국명': ['튼튼약국', '사랑약국(추천)', '중앙약국', '미소약국', '바른약국', '우리약국', '정성약국'],
        'lat': [35.18, 35.182, 35.178, 35.181, 35.179, 35.183, 35.177],
        'lon': [128.08, 128.082, 128.078, 128.081, 128.079, 128.083, 128.077],
        'avg': [8, 7, 10, 9, 8, 11, 9],
        'queue': [5, 1, 12, 4, 3, 15, 6],
        'staff': [2, 2, 2, 2, 2, 1, 2]
    }
    df = pd.DataFrame(data)
    
    # 시간 산출 및 정렬 [cite: 25]
    df['예상시간'] = df.apply(lambda x: get_est_time(x['avg'], x['queue'], x['staff']), axis=1)
    df = df.sort_values(by='예상시간').reset_index(drop=True)

    # 지도 표시 (확대/축소 가능)
    st.map(df, latitude='lat', longitude='lon', size=20, zoom=14)
    
    st.write("---")
    st.caption("가까운 거리와 조제완료 시간을 고려해 선택하세요.") # [cite: 16]

    # 약국 리스트 7개 나열
    for i in range(len(df)):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{df.iloc[i]['약국명']}**")
                st.caption(f"평균 응답 기반 산출 데이터") # [cite: 109]
            with col2:
                st.subheader(f"{df.iloc[i]['예상시간']}분")
            
            if st.button("예약하기", key=f"book_{i}", use_container_width=True):
                st.session_state.reservation = df.iloc[i]
                st.session_state.step = 4
                st.rerun()

# --- [#7, #8, #9. 예약 완료 및 내역] ---
elif st.session_state.step == 4:
    res = st.session_state.reservation
    st.balloons()
    
    st.success("✅ 조제 예약이 완료되었습니다!")
    
    with st.container(border=True):
        # #7. 완료 시간 표시
        st.markdown(f"### ⏱️ **{res['예상시간']}분 후**")
        st.markdown("예약하신 약이 완료될 예정입니다.")
        
        st.write("---")
        # #8. 데스크 제출 안내
        st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
        
        # #9. 예약 내역 상세
        st.write("📋 **내 예약 내역**")
        st.info(f"{res['약국명']} 조제 예약 완료")
    
    if st.button("처음으로 돌아가기"):
        st.session_state.step = 1
        st.session_state.reservation = None
        st.rerun()
