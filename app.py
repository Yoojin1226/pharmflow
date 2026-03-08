import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

# 세션 상태 초기화 (역할 및 알고리즘 변수 포함)
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

# [알고리즘 핵심 변수] - 약사 화면에서 연동
if 'pharm_config' not in st.session_state:
    st.session_state.pharm_config = {
        'T_avg': 7.0,     # 평균 조제 시간
        'P_staff': 2,     # 조제 인력 수
        'W_time': 1.0,    # 시간대 가중치
        'B_type': 5.0,    # 약국 유형 보정값
        'N_offline': 0    # 오프라인 혼잡도 (원활:0, 보통:3, 혼잡:6)
    }

# --- [정교한 ETA 계산 알고리즘 함수] ---
def calculate_eta(n_wait_total, config, w_complex=1.1):
    # 공식: ETA = (N_wait * T_avg * W_time * W_complex) / P_staff + B_type
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
                    with st.spinner("🔍 처방전 성분을 분석 중입니다..."):
                        time.sleep(1.5)
                        if uploaded_file.size < 50000:
                            st.error("❌ 처방전 형식이 아닙니다.")
                        else:
                            st.session_state.step = 2.5
                            st.rerun()
            with col2:
                if st.button("⬅️ 이전 단계로", use_container_width=True):
                    st.session_state.step = 1
                    st.rerun()

    # #3.5. OCR 정보 확인 단계
    elif st.session_state.step == 2.5:
        st.subheader("📋 처방전 정보 인식 결과")
        drug_info = pd.DataFrame({
            "구분": ["약 이름", "약 이름", "약 이름"],
            "인식된 명칭": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
            "용법/용량": ["1일 1회 식후", "1일 2회 식후", "필요 시 1정"],
            "비고": ["혈압강하제", "당뇨병약", "해열진통제"]
        })
        st.table(drug_info)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("정보 확인 완료", use_container_width=True, type="primary"):
                st.session_state.step = 3
                st.rerun()
        with col2:
            if st.button("⬅️ 재촬영 하기", use_container_width=True):
                st.session_state.step = 2
                st.rerun()

    # #5 & #6. 지도 화면 및 약국 선택
    elif st.session_state.step == 3:
        if not st.session_state.is_accepting:
            st.error("현재 지역 약국들이 조제 예약을 받고 있지 않습니다.")
            if st.button("🏠 처음으로 돌아가기"): st.session_state.step = 1; st.rerun()
        else:
            st.subheader("🔍 주변 약국 실시간 현황")
            my_lat, my_lon = 35.91, 127.07
            
            # [알고리즘 반영] 약사가 설정한 값 기반으로 ETA 계산
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

            # 지도 레이어 설정
            view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
            
            st.pydeck_chart(pdk.Deck(
                map_style='light', # 흰 배경 문제를 해결하기 위한 안정적인 스타일 적용
                initial_view_state=view_state,
                layers=[
                    pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60),
                    pdk.Layer("ScatterplotLayer", me_df, get_position='[lon, lat]', get_color='[0, 120, 255, 255]', get_radius=85),
                    pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id_str', get_size=24, get_color=[255, 255, 255], get_alignment_baseline="'center'"),
                    pdk.Layer("TextLayer", me_df, get_position='[lon, lat]', get_text='label', get_size=22, get_color=[255, 255, 255], get_alignment_baseline="'center'")
                ]
            ))
            st.write("---")
            if st.button("⬅️ 이전 단계 (처방 정보 확인)", use_container_width=True):
                st.session_state.step = 2.5
                st.rerun()

            for i in range(len(df)):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {df.iloc[i]['id']}. {df.iloc[i]['약국명']}")
                    c2.subheader(f"{df.iloc[i]['예상시간']}분")
                    if st.button(f"{df.iloc[i]['id']}번 예약하기", key=f"bk_{i}", use_container_width=True):
                        st.session_state.pharmacy_orders.append({"order_id": f"P-{np.random.randint(100,999)}", "time": time.strftime("%H:%M"), "status": "접수됨"})
                        st.session_state.reservation = df.iloc[i]
                        st.session_state.step = 4
                        st.rerun()

    # #7~#9. 최종 완료 (돌아가기 버튼 없음)
    elif st.session_state.step == 4:
        res = st.session_state.reservation
        st.balloons()
        st.success("✅ 조제 예약이 완료되었습니다!")
        with st.container(border=True):
            st.markdown(f"### ⏱️ **{res['예상시간']}분 후**")
            st.write("예약하신 약이 완료될 예정입니다.")
            st.write("---")
            st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
            st.info(f"**[{res['id']}번 {res['약국명']}]** 조제 예약 완료")
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.step = 1; st.session_state.reservation = None; st.rerun()

# --- [B. 약국용 관리 대시보드] ---
elif st.session_state.role == "pharmacy":
    st.sidebar.button("🏠 초기화면으로", on_click=lambda: setattr(st.session_state, 'role', None))
    st.title("👨‍⚕️ PharmFlow 관리자")
    st.success("PharmFlow에 등록해주셔서 감사합니다.")

    with st.expander("⚙️ 알고리즘 변수 및 약국 환경 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.pharm_config['T_avg'] = st.number_input("평균 조제 시간(분)", value=7.0)
            st.session_state.pharm_config['P_staff'] = st.number_input("조제 인력 수", value=2)
            status = st.select_slider("내부 혼잡도 체크", options=["원활", "보통", "혼잡"])
            status_map = {"원활": 0, "보통": 3, "혼잡": 6}
            st.session_state.pharm_config['N_offline'] = status_map[status]
        with col2:
            st.session_state.pharm_config['B_type'] = st.selectbox("약국 유형 보정값", [5.0, 10.0, 2.0], 
                                                                format_func=lambda x: "내과 (+5)" if x==5 else "대학병원 (+10)" if x==10 else "소아과 (+2)")
            peak = st.checkbox("피크 가중치 적용 (1.2배)")
            st.session_state.pharm_config['W_time'] = 1.2 if peak else 1.0

    st.write("---")
    accept_toggle = st.radio("📡 조제 요청을 받으시겠습니까?", ["예", "아니오"], horizontal=True)
    st.session_state.is_accepting = (accept_toggle == "예")

    st.subheader("📥 실시간 조제 예약 목록")
    if not st.session_state.pharmacy_orders:
        st.info("현재 들어온 요청이 없습니다.")
    else:
        st.caption("✅ 조제가 예약되었습니다.")
        for i, order in enumerate(st.session_state.pharmacy_orders):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                c1.write(f"ID: {order['order_id']}")
                c2.write(f"접수: {order['time']}")
                if c3.button("조제 완료", key=f"done_{i}"):
                    st.session_state.pharmacy_orders.pop(i)
                    st.rerun()
