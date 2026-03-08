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
    st.session_state.is_accepting = True # 조제 요청 수락 여부
if 'pharmacy_orders' not in st.session_state:
    st.session_state.pharmacy_orders = []

# [약국 관리 변수 초기 설정] - 알고리즘 핵심 변수
if 'pharm_config' not in st.session_state:
    st.session_state.pharm_config = {
        'T_avg': 7.0,     # 평균 조제 시간
        'P_staff': 2,     # 조제 인력 수
        'W_time': 1.0,    # 시간대 가중치
        'B_type': 5.0,    # 약국 유형 보정값
        'N_offline': 0    # 오프라인 대기 보정 (원활:0, 보통:3, 혼잡:6)
    }

# --- [정교한 ETA 계산 알고리즘 함수] ---
def calculate_eta(n_wait_total, config, w_complex=1.1):
    # 공식: ETA = (N_wait * T_avg * W_time * W_complex) / P_staff + B_type
    n_wait = n_wait_total + config['N_offline'] # 온라인 예약 + 오프라인 혼잡도
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
        st.title("💊 PharmFlow")
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

    # #3.5. OCR 정보 확인 (알고리즘 변수 반영)
    elif st.session_state.step == 2.5:
        st.subheader("📋 처방전 정보 인식 결과")
        drug_info = pd.DataFrame({
            "인식된 명칭": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
            "용법": ["1일 1회", "1일 2회", "필요 시"],
            "복잡도": ["보통", "보통", "보통"]
        })
        st.table(drug_info)
        # 3개 약 기준 W_complex = 1.0 (알고리즘 반영)
        st.caption("ℹ️ 분석 결과: 3개 품목 인식됨 (복잡도 가중치 1.0 적용)")
        
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
            
            # [알고리즘 적용] 관리자 설정을 바탕으로 시간 산출
            current_online_queue = len(st.session_state.pharmacy_orders)
            eta_val = calculate_eta(current_online_queue, st.session_state.pharm_config)

            df = pd.DataFrame({
                '약국명': ['우석약국', '삼례종로약국', '삼례정문약국'],
                'lat': [35.912, 35.908, 35.911],
                'lon': [127.072, 127.068, 127.075],
                '예상시간': [eta_val, eta_val+3, eta_val+7] # 시연용 차등
            })
            df['id'] = range(1, len(df) + 1)
            
            # 지도 렌더링 (번호 및 Me 표시)
            view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
            st.pydeck_chart(pdk.Deck(layers=[
                pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60),
                pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id', get_size=26, get_color=[255,255,255], get_alignment_baseline="'center'")
            ], initial_view_state=view_state))

            for i in range(len(df)):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {df.iloc[i]['id']}. {df.iloc[i]['약국명']}")
                    c2.subheader(f"{df.iloc[i]['예상시간']}분")
                    if st.button(f"{df.iloc[i]['id']}번 예약하기", key=f"bk_{i}", use_container_width=True):
                        st.session_state.pharmacy_orders.append({"id": f"ORD-{time.time()}", "time": time.strftime("%H:%M"), "status": "접수됨"})
                        st.session_state.reservation = df.iloc[i]
                        st.session_state.step = 4
                        st.rerun()

    # #7~#9. 최종 완료 (다시 선택하기 삭제)
    elif st.session_state.step == 4:
        res = st.session_state.reservation
        st.balloons()
        st.success("✅ 조제 예약이 완료되었습니다!")
        st.info(f"**[{res['약국명']}]** {res['예상시간']}분 후 완료 예정")
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.step = 1; st.session_state.reservation = None; st.rerun()

# --- [B. 약국용 관리 대시보드] ---
elif st.session_state.role == "pharmacy":
    st.sidebar.button("🏠 초기화면으로", on_click=lambda: setattr(st.session_state, 'role', None))
    
    st.title("👨‍⚕️ PharmFlow 관리자")
    st.success("PharmFlow에 등록해주셔서 감사합니다. 실시간으로 약국 현황을 동기화합니다.") # 요청 2번 반영

    # 3️⃣ 변수 설정 단계 (알고리즘 변수 수집)
    with st.expander("⚙️ 알고리즘 변수 및 약국 환경 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.pharm_config['T_avg'] = st.number_input("평균 조제 시간(분)", value=7.0)
            st.session_state.pharm_config['P_staff'] = st.number_input("조제 인력 수(약사+보조)", value=2)
            # 오프라인 혼잡도 보정 (요청 1-2번 반영)
            status = st.select_slider("내부 혼잡도 체크", options=["원활", "보통", "혼잡"])
            status_map = {"원활": 0, "보통": 3, "혼잡": 6}
            st.session_state.pharm_config['N_offline'] = status_map[status]
        with col2:
            st.session_state.pharm_config['B_type'] = st.selectbox("약국 유형 보정값", [5.0, 10.0, 2.0], 
                                                                format_func=lambda x: "내과 밀집 (+5)" if x==5 else "대학병원 (+10)" if x==10 else "소아과 중심 (+2)")
            peak = st.checkbox("점심/퇴근 피크 시간대 적용 (1.2배)")
            st.session_state.pharm_config['W_time'] = 1.2 if peak else 1.0

    # 4️⃣ 조제 요청 수락 여부
    st.write("---")
    accept_toggle = st.radio("📡 조제 요청을 받으시겠습니까?", ["예", "아니오"], horizontal=True)
    st.session_state.is_accepting = (accept_toggle == "예")

    if not st.session_state.is_accepting:
        st.warning("현재 신규 조제 예약을 받지 않는 상태입니다.")
    else:
        # 5️⃣ & 6️⃣ 조제 예약 목록 및 완료 처리
        st.subheader("📥 실시간 조제 예약 목록")
        if not st.session_state.pharmacy_orders:
            st.info("현재 들어온 조제 요청이 없습니다.")
        else:
            st.caption("✅ 조제가 예약되었습니다. 리스트에서 상태를 관리하세요.")
            for i, order in enumerate(st.session_state.pharmacy_orders):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    c1.write(f"ID: {order['time']}")
                    c2.write(f"상태: **{order['status']}**")
                    if c3.button("조제 완료", key=f"done_{i}"):
                        st.session_state.pharmacy_orders.pop(i)
                        st.success("환자에게 완료 알림을 전송했습니다!")
                        st.rerun()
