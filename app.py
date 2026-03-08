import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time
from datetime import datetime, timedelta, timezone

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

# 한국 시간(KST) 설정을 위한 함수
def get_kst_now():
    # UTC 시간에 9시간을 더해 한국 시간을 산출합니다.
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)

# 세션 상태 초기화
if 'role' not in st.session_state:
    st.session_state.role = None
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'admin_step' not in st.session_state:
    st.session_state.admin_step = 1
if 'selected_pharmacy' not in st.session_state:
    st.session_state.selected_pharmacy = None
if 'reservation' not in st.session_state:
    st.session_state.reservation = None
if 'is_accepting' not in st.session_state:
    st.session_state.is_accepting = "예" 
if 'pharmacy_orders' not in st.session_state:
    st.session_state.pharmacy_orders = []
if 'completed_orders' not in st.session_state:
    st.session_state.completed_orders = []
if 'last_clear_time' not in st.session_state:
    st.session_state.last_clear_time = time.time()

# 20분마다 데이터 자동 삭제 로직
current_time = time.time()
if current_time - st.session_state.last_clear_time > 1200:
    st.session_state.completed_orders = []
    st.session_state.last_clear_time = current_time

if 'pharm_config' not in st.session_state:
    st.session_state.pharm_config = {
        'T_avg': 7.0, 'P_staff': 2, 'W_time': 1.0, 'B_type': 5.0, 'N_offline': 0
    }

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
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("👨‍⚕️ 약국용 관리자", use_container_width=True):
            st.session_state.role = "pharmacy"
            st.session_state.admin_step = 1
            st.rerun()

# --- [A. 환자용 서비스] ---
elif st.session_state.role == "patient":
    # #2 피드백 반영: 조제 완료(Step 4)를 제외한 모든 단계에서 '처음으로 돌아가기' 버튼 노출
    if st.session_state.step < 4:
        if st.sidebar.button("🏠 처음으로 돌아가기 (선택취소)", use_container_width=True):
            st.session_state.role = None
            st.session_state.step = 1
            st.rerun()

    if st.session_state.step == 1:
        st.title("💊 PharmFlow 팜플로우")
        st.write("내 시간에 맞는 약국으로")
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
            st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
            if st.button("확인", use_container_width=True, type="primary"):
                st.session_state.step = 2
                st.rerun()

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

    elif st.session_state.step == 2.5:
        st.subheader("📋 처방전 정보 인식 결과")
        drug_info = pd.DataFrame({"인식된 명칭":["아모디핀정 5mg","메토포르민서방정 500mg","타이레놀정 500mg"],"용법":["1일 1회","1일 2회","필요 시"]})
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

    elif st.session_state.step == 3:
        if st.session_state.is_accepting == "아니오":
            st.error("🚨 현재 지역 약국들이 '대기 상태'입니다. 잠시 후 다시 시도해 주세요.")
            if st.button("🏠 처음으로 돌아가기", use_container_width=True):
                st.session_state.role = None
                st.session_state.step = 1
                st.rerun()
        else:
            st.subheader("🔍 주변 약국 실시간 현황")
            my_lat, my_lon = 35.91, 127.07
            current_pharm_queue = len([o for o in st.session_state.pharmacy_orders if o.get('pharm_name') == st.session_state.selected_pharmacy])
            eta_val = calculate_eta(current_pharm_queue, st.session_state.pharm_config)

            pharm_names = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
            np.random.seed(42)
            lats = my_lat + (np.random.uniform(-0.005, 0.005, size=7))
            lons = my_lon + (np.random.uniform(-0.005, 0.005, size=7))
            
            df = pd.DataFrame({'약국명': pharm_names, 'lat': lats, 'lon': lons, '예상시간': [eta_val, eta_val+2, eta_val+5, eta_val+1, eta_val+3, eta_val+8, eta_val+4]})
            df = df.sort_values(by='예상시간').reset_index(drop=True)
            df['id'] = range(1, len(df) + 1)
            df['id_str'] = df['id'].astype(str)

            me_df = pd.DataFrame({'lat': [my_lat], 'lon': [my_lon], 'label': ['Me']})

            view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
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
                    if st.button(f"{df.iloc[i]['id']}번 예약하기", key=f"book_{i}", use_container_width=True):
                        # #1 피드백 반영: 한국 시간(KST)으로 예약 시각 기록
                        unique_order_id = f"P-{int(time.time() * 1000) % 1000000}"
                        reservation_time = get_kst_now().strftime("%H:%M") # 한국 시간 적용
                        
                        st.session_state.pharmacy_orders.append({
                            "order_id": unique_order_id,
                            "pharm_name": df.iloc[i]['약국명'],
                            "res_time": reservation_time,
                            "status": "접수됨"
                        })
                        st.session_state.reservation = df.iloc[i]
                        st.session_state.step = 4
                        st.rerun()

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
            st.session_state.role = None; st.session_state.step = 1; st.session_state.reservation = None; st.rerun()

# --- [B. 약국용 관리자 화면] ---
elif st.session_state.role == "pharmacy":
    # 관리자 화면에서도 사이드바 초기화 가능
    if st.sidebar.button("🏠 초기화면으로 (로그아웃)", use_container_width=True):
        st.session_state.role = None
        st.session_state.admin_step = 1
        st.rerun()

    if st.session_state.admin_step == 1:
        st.title("👨‍⚕️ PharmFlow 관리자 접속")
        pharm_list = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
        selected = st.selectbox("관리하실 약국을 선택해 주세요.", pharm_list)
        if st.button("관리 페이지 진입", use_container_width=True, type="primary"):
            st.session_state.selected_pharmacy = selected
            st.session_state.admin_step = 2
            st.rerun()

    elif st.session_state.admin_step == 2:
        st.title(f"🏢 {st.session_state.selected_pharmacy}")
        st.success("PharmFlow에 등록해주셔서 감사합니다.")
        st.subheader("⚙️ 약국 환경 설정")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.pharm_config['T_avg'] = st.number_input("평균 조제 시간(분)", value=7.0)
                st.session_state.pharm_config['P_staff'] = st.number_input("조제 인력 수", value=2)
                status = st.select_slider("내부 혼잡도", options=["원활", "보통", "혼잡"])
                status_map = {"원활": 0, "보통": 3, "혼잡": 6}; st.session_state.pharm_config['N_offline'] = status_map[status]
            with col2:
                st.session_state.pharm_config['B_type'] = st.selectbox("약국 유형", [5.0, 10.0, 2.0], format_func=lambda x: "내과 밀집 (+5)" if x==5 else "대학병원 (+10)" if x==10 else "소아과 중심 (+2)")
                st.session_state.pharm_config['W_time'] = 1.2 if st.checkbox("피크 가중치 (1.2배)") else 1.0

        st.write("---")
        st.session_state.is_accepting = st.radio("📡 조제 요청을 받으시겠습니까?", ["예", "아니오"], horizontal=True)

        if st.session_state.is_accepting == "아니오":
            st.warning("⚠️ 현재 '대기 상태' 모드입니다.")
            if st.button("⬅️ 약국 다시 선택"): st.session_state.admin_step = 1; st.rerun()
        else:
            col_back, col_next = st.columns(2)
            with col_back:
                if st.button("⬅️ 약국 다시 선택"): st.session_state.admin_step = 1; st.rerun()
            with col_next:
                if st.button("다음 (예약 목록 확인) ➡️", use_container_width=True, type="primary"):
                    st.session_state.admin_step = 3
                    st.rerun()

    elif st.session_state.admin_step == 3:
        st.title(f"📥 {st.session_state.selected_pharmacy} 예약 목록")
        
        col_view, col_home = st.columns(2)
        with col_view:
            if st.button("📋 조제기록 확인", use_container_width=True):
                st.session_state.admin_step = 4; st.rerun()
        with col_home:
            if st.button("🏠 홈으로 이동", use_container_width=True):
                st.session_state.role = None; st.session_state.admin_step = 1; st.rerun()

        st.write("---")
        my_orders = [o for o in st.session_state.pharmacy_orders if o['pharm_name'] == st.session_state.selected_pharmacy]

        if not my_orders:
            st.info("현재 들어온 조제 요청이 없습니다.")
        else:
            st.caption(f"✅ {st.session_state.selected_pharmacy}의 실시간 요청 목록입니다.")
            for order in my_orders:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    c1.write(f"**{order['order_id']}**")
                    c2.write(f"예약 시각: {order['res_time']}") 
                    if c3.button("조제 완료", key=f"done_{order['order_id']}", use_container_width=True, type="primary"):
                        # 완료 시간도 KST로 기록
                        order['done_time'] = get_kst_now().strftime("%H:%M")
                        st.session_state.completed_orders.append(order)
                        st.session_state.pharmacy_orders = [o for o in st.session_state.pharmacy_orders if o['order_id'] != order['order_id']]
                        st.rerun()

    elif st.session_state.admin_step == 4:
        st.title(f"📜 {st.session_state.selected_pharmacy} 조제 완료 기록")
        st.caption("🕒 최근 20분간의 기록만 보존됩니다.")
        my_completed = [o for o in st.session_state.completed_orders if o['pharm_name'] == st.session_state.selected_pharmacy]
        if not my_completed:
            st.write("기록된 조제 완료 내역이 없습니다.")
        else:
            completed_df = pd.DataFrame(my_completed)
            st.table(completed_df[['res_time', 'done_time', 'order_id']].rename(columns={'res_time':'예약시간', 'done_time':'완료시간', 'order_id':'고유ID'}))
        if st.button("⬅️ 예약 목록으로 돌아가기", use_container_width=True):
            st.session_state.admin_step = 3; st.rerun()
