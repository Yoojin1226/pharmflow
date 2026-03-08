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
if 'admin_step' not in st.session_state: # 약국 관리자용 단계 변수
    st.session_state.admin_step = 1
if 'selected_pharmacy' not in st.session_state: # 선택된 약국명
    st.session_state.selected_pharmacy = None
if 'reservation' not in st.session_state:
    st.session_state.reservation = None
if 'is_accepting' not in st.session_state:
    st.session_state.is_accepting = True 
if 'pharmacy_orders' not in st.session_state:
    st.session_state.pharmacy_orders = []

# [알고리즘 핵심 변수 설정]
if 'pharm_config' not in st.session_state:
    st.session_state.pharm_config = {
        'T_avg': 7.0, 'P_staff': 2, 'W_time': 1.0, 'B_type': 5.0, 'N_offline': 0
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

# --- [A. 환자용 서비스 - 기존 기능 유지] ---
elif st.session_state.role == "patient":
    st.sidebar.button("🏠 초기화면으로", on_click=lambda: setattr(st.session_state, 'role', None))
    # (환자용 코드 생략 - 이전과 동일하게 작동하도록 보존됨)
    # ... [이전 환자용 코드 블록 삽입] ...
    if st.session_state.step == 1:
        st.title("💊 PharmFlow 팜플로우")
        st.write("내 시간에 맞는 약국으로")
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
            st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
            if st.button("확인", use_container_width=True, type="primary"):
                st.session_state.step = 2
                st.rerun()
    # (중략 - 환자용 나머지 로직 동일)
    elif st.session_state.step == 2:
        st.title("PharmFlow")
        st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.")
        uploaded_file = st.file_uploader("이미지를 업로드하세요.", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
            if st.button("분석 시작", use_container_width=True, type="primary"):
                st.session_state.step = 2.5
                st.rerun()
    elif st.session_state.step == 2.5:
        st.subheader("📋 처방전 정보 인식 결과")
        drug_info = pd.DataFrame({"구분":["약 이름","약 이름","약 이름"],"인식된 명칭":["아모디핀정 5mg","메토포르민서방정 500mg","타이레놀정 500mg"],"용법":["1일 1회","1일 2회","필요 시"]})
        st.table(drug_info)
        if st.button("정보 확인 완료", use_container_width=True, type="primary"): st.session_state.step = 3; st.rerun()
    elif st.session_state.step == 3:
        if not st.session_state.is_accepting:
            st.error("현재 지역 약국들이 조제 예약을 받고 있지 않습니다.")
        else:
            st.subheader("🔍 주변 약국 실시간 현황")
            my_lat, my_lon = 35.91, 127.07
            current_online_queue = len(st.session_state.pharmacy_orders)
            eta_val = calculate_eta(current_online_queue, st.session_state.pharm_config)
            pharm_names = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
            df = pd.DataFrame({'약국명': pharm_names, 'lat': [my_lat+0.002, my_lat-0.002, my_lat+0.001, my_lat-0.001, my_lat+0.003, my_lat-0.003, my_lat+0.004], 'lon': [my_lon+0.002, my_lon-0.002, my_lon+0.005, my_lon-0.004, my_lon+0.003, my_lon-0.005, my_lon+0.001], '예상시간': [eta_val]*7})
            df['id'] = range(1, 8)
            st.pydeck_chart(pdk.Deck(map_style='mapbox://styles/mapbox/light-v9', initial_view_state=pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14), layers=[pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60), pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id', get_size=24, get_color=[255,255,255], get_alignment_baseline="'center'")]))
            for i in range(len(df)):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {df.iloc[i]['id']}. {df.iloc[i]['약국명']}")
                    c2.subheader(f"{df.iloc[i]['예상시간']}분")
                    if st.button(f"{df.iloc[i]['id']}번 예약하기", key=f"bk_{i}", use_container_width=True):
                        st.session_state.pharmacy_orders.append({"order_id": f"P-{np.random.randint(100,999)}", "time": time.strftime("%H:%M"), "status": "접수됨"})
                        st.session_state.reservation = df.iloc[i]
                        st.session_state.step = 4; st.rerun()
    elif st.session_state.step == 4:
        st.balloons(); st.success("✅ 조제 예약이 완료되었습니다!")
        if st.button("🏠 처음으로"): st.session_state.step = 1; st.session_state.reservation = None; st.rerun()

# --- [B. 약국용 관리자 화면 - 요청사항 반영] ---
elif st.session_state.role == "pharmacy":
    st.sidebar.button("🏠 초기화면으로", on_click=lambda: setattr(st.session_state, 'role', None))
    
    # #1. 약국 선택 화면 (Step 1)
    if st.session_state.admin_step == 1:
        st.title("👨‍⚕️ PharmFlow 관리자 접속")
        st.write("관리하실 약국을 선택해 주세요.")
        
        pharm_list = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
        selected = st.selectbox("약국 목록", pharm_list)
        
        if st.button("관리 페이지 진입", use_container_width=True, type="primary"):
            st.session_state.selected_pharmacy = selected
            st.session_state.admin_step = 2
            st.rerun()

    # #2. 약국 환경 설정 화면 (Step 2)
    elif st.session_state.admin_step == 2:
        st.title(f"🏢 {st.session_state.selected_pharmacy}")
        st.success(f"PharmFlow에 등록해주셔서 감사합니다.")
        
        st.subheader("⚙️ 약국 환경 설정") # 제목 변경 반영
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.pharm_config['T_avg'] = st.number_input("평균 조제 시간(분)", value=7.0)
                st.session_state.pharm_config['P_staff'] = st.number_input("조제 인력 수", value=2)
                status = st.select_slider("내부 혼잡도 체크", options=["원활", "보통", "혼잡"])
                status_map = {"원활": 0, "보통": 3, "혼잡": 6}
                st.session_state.pharm_config['N_offline'] = status_map[status]
            with col2:
                # "보정값" 단어 삭제 반영
                st.session_state.pharm_config['B_type'] = st.selectbox("약국 유형", [5.0, 10.0, 2.0], 
                                                                    format_func=lambda x: "내과 밀집 (+5)" if x==5 else "대학병원 (+10)" if x==10 else "소아과 중심 (+2)")
                peak = st.checkbox("피크 시간대 가중치 적용 (1.2배)")
                st.session_state.pharm_config['W_time'] = 1.2 if peak else 1.0

        st.write("---")
        accept_toggle = st.radio("📡 조제 요청을 받으시겠습니까?", ["예", "아니오"], horizontal=True)
        st.session_state.is_accepting = (accept_toggle == "예")

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("⬅️ 약국 다시 선택"):
                st.session_state.admin_step = 1
                st.rerun()
        with col_next:
            # #3. 다음 버튼 추가 반영
            if st.button("다음 (예약 목록 확인) ➡️", use_container_width=True, type="primary"):
                st.session_state.admin_step = 3
                st.rerun()

    # #3. 실시간 조제 예약 목록 화면 (Step 3)
    elif st.session_state.admin_step == 3:
        st.title(f"📥 {st.session_state.selected_pharmacy} 예약 관리")
        
        st.subheader("📋 실시간 조제 예약 목록")
        
        if not st.session_state.pharmacy_orders:
            st.info("현재 들어온 조제 요청이 없습니다.")
        else:
            st.caption("✅ 환자로부터 조제 요청이 들어오면 목록에 표시됩니다.") # 문구 반영
            for i, order in enumerate(st.session_state.pharmacy_orders):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    c1.write(f"ID: {order['order_id']}")
                    c2.write(f"접수 시각: {order['time']}")
                    # 조제 완료 버튼 반영
                    if c3.button("조제 완료", key=f"done_{i}", use_container_width=True, type="primary"):
                        st.session_state.pharmacy_orders.pop(i)
                        st.rerun()
        
        if st.button("⬅️ 설정 화면으로 돌아가기"):
            st.session_state.admin_step = 2
            st.rerun()
