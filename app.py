import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

# 세션 상태 초기화
if 'role' not in st.session_state:
    st.session_state.role = None
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'reservation' not in st.session_state:
    st.session_state.reservation = None
if 'is_accepting' not in st.session_state:
    st.session_state.is_accepting = True 
if 'pharmacy_orders' not in st.session_state:
    st.session_state.pharmacy_orders = []

# [약국 관리 변수 초기 설정] - 알고리즘 핵심 변수
if 'pharm_config' not in st.session_state:
    st.session_state.pharm_config = {
        'T_avg': 7.0,     # 평균 조제 시간
        'P_staff': 2,     # 조제 인력 수
        'W_time': 1.0,    # 시간대 가중치
        'B_type': 5.0,    # 약국 유형 보정값
        'N_offline': 0    # 오프라인 대기 보정
    }

# --- [정교한 ETA 계산 알고리즘 함수] ---
def calculate_eta(n_wait_total, config, w_complex=1.1):
    n_wait = n_wait_total + config['N_offline'] 
    numerator = n_wait * config['T_avg'] * config['W_time'] * w_complex
    eta = (numerator / config['P_staff']) + config['B_type']
    return int(eta)

# --- [메인 진입로: 역할 선택] ---
if st.session_state.role is None:
    st.title("💊 PharmFlow 팜플로우")
    st.write("사용자 유형을 선택해 주세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🙋‍♂️ 환자용 서비스", use_container_width=True, type="primary"):
            st.session_state.role = "patient"
            st.rerun()
    with col2:
        if st.button("👨‍⚕️ 약국용 관리자", use_container_width=True):
            st.session_state.role = "pharmacy"
            st.rerun()

# --- [A. 환자용 서비스] ---
elif st.session_state.role == "patient":
    st.sidebar.button("🏠 초기화면으로", on_click=lambda: setattr(st.session_state, 'role', None))

    # #1 & #2. 메인 및 권한 동의
    if st.session_state.step == 1:
        st.title("💊 PharmFlow 팜플로우")
        st.write("내 시간에 맞는 약국으로")
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
            st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
            if st.button("확인", use_container_width=True, type="primary"):
                st.session_state.step = 2
                st.rerun()

    # #3 & #4. 업로드 및 분석
    elif st.session_state.step == 2:
        st.title("PharmFlow")
        st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.")
        st.subheader("📸 처방전 업로드")
        uploaded_file = st.file_uploader("이미지를 업로드하세요.", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("분석 시작", use_container_width=True, type="primary"):
                    with st.spinner("🔍 분석 중..."):
                        time.sleep(1.5)
                        st.session_state.step = 2.5
                        st.rerun()
            with col2:
                if st.button("⬅️ 이전으로", use_container_width=True):
                    st.session_state.step = 1
                    st.rerun()

    # #3.5. OCR 정보 확인
    elif st.session_state.step == 2.5:
        st.subheader("📋 처방전 정보 인식 결과")
        drug_info = pd.DataFrame({
            "구분": ["약 이름", "약 이름", "약 이름"],
            "인식된 명칭": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
            "용법": ["1일 1회", "1일 2회", "필요 시"]
        })
        st.table(drug_info)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("정보 확인 완료", use_container_width=True, type="primary"):
                st.session_state.step = 3
                st.rerun()
        with col2:
            if st.button("⬅️ 재촬영", use_container_width=True):
                st.session_state.step = 2
                st.rerun()

    # #5 & #6. 지도 화면 및 약국 선택
    elif st.session_state.step == 3:
        if not st.session_state.is_accepting:
            st.error("현재 지역 약국들이 조제 예약을 받고 있지 않습니다.")
            if st.button("🏠 처음으로"): st.session_state.step = 1; st.rerun()
        else:
            st.subheader("🔍 주변 약국 실시간 현황")
            my_lat, my_lon = 35.91, 127.07
            
            # [알고리즘 반영 데이터]
            current_online_queue = len(st.session_state.pharmacy_orders)
            eta_val = calculate_eta(current_online_queue, st.session_state.pharm_config)

            pharm_names = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
            np.random.seed(42)
            lats = my_lat + (np.random.uniform(-0.005, 0.005, size=7))
            lons = my_lon + (np.random.uniform(-0.005, 0.005, size=7))
            
            df = pd.DataFrame({
                '약국명': pharm_names, 'lat': lats, 'lon': lons,
                '예상시간': [eta_val, eta_val+2, eta_val+5, eta_val+1, eta_val+3, eta_val+8, eta_val+4]
            })
            df = df.sort_values(by='예상시간').reset_index(drop=True)
            df['id'] = range(1, len(df) + 1)
            df['id_str'] = df['id'].astype(str)

            me_df = pd.DataFrame({'lat': [my_lat], 'lon': [my_lon], 'label': ['Me']})

            # 지도 레이어 (검은 배경 해결 및 번호/Me 표시 복구)
            view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
            
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9', # 밝은 지도로 변경
                initial_view_state=view_state,
                layers=[
                    pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60),
                    pdk.Layer("ScatterplotLayer", me_df, get_position='[lon, lat]', get_color='[0, 120, 255, 255]', get_radius=85),
                    pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id_str', get_size=24, get_color=[255, 255, 255], get_alignment_baseline="'center'
