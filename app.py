import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time
from datetime import datetime, timedelta, timezone

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

def get_kst_now():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)

# [중앙 DB] - 약국 관리자가 설정하는 실시간 데이터 저장소
if 'pharm_db' not in st.session_state:
    pharm_list = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
    st.session_state.pharm_db = {name: {
        'T_avg': 7.0, 'P_staff': 2, 'W_time': 1.0, 'B_type': 5.0, 'N_offline': 0, 'is_accepting': "예"
    } for name in pharm_list}

if 'role' not in st.session_state: st.session_state.role = None
if 'step' not in st.session_state: st.session_state.step = 1
if 'admin_step' not in st.session_state: st.session_state.admin_step = 1
if 'reservation' not in st.session_state: st.session_state.reservation = None
if 'pharmacy_orders' not in st.session_state: st.session_state.pharmacy_orders = []
if 'completed_orders' not in st.session_state: st.session_state.completed_orders = []

# --- [ETA 산출 로직: 약국 DB와 동기화] ---
def calculate_pharm_eta(pharm_name, w_complex=1.1):
    config = st.session_state.pharm_db[pharm_name]
    n_online = len([o for o in st.session_state.pharmacy_orders if o['pharm_name'] == pharm_name])
    n_wait = n_online + config['N_offline'] # 온라인 예약 + 현장 대기 
    
    numerator = n_wait * config['T_avg'] * config['W_time'] * w_complex
    eta_val = (numerator / config['P_staff']) + config['B_type']
    
    eta_str = f"{int(eta_val)}~{int(eta_val) + 2}" if eta_val % 1 != 0 else str(int(eta_val))
    return eta_str, n_wait, config['T_avg'], config['W_time'], config['P_staff'], config['B_type']

# --- [메인 화면] ---
if st.session_state.role is None:
    st.title("💊 PharmFlow 팜플로우")
    st.write("처방 이후 약국 수요를 데이터로 재배치합니다[cite: 8].")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🙋‍♂️ 환자용 서비스", use_container_width=True, type="primary"):
            st.session_state.role = "patient"; st.rerun()
    with col2:
        if st.button("👨‍⚕️ 약국용 관리자", use_container_width=True):
            st.session_state.role = "pharmacy"; st.rerun()

# --- [A. 환자용 서비스] ---
elif st.session_state.role == "patient":
    st.sidebar.button("🏠 처음으로", on_click=lambda: setattr(st.session_state, 'role', None))

    if st.session_state.step == 1:
        st.title("💊 PharmFlow")
        with st.container(border=True):
            st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
            if st.button("확인", use_container_width=True, type="primary"): st.session_state.step = 2; st.rerun()

    elif st.session_state.step == 2:
        st.subheader("📸 처방전 업로드")
        uploaded_file = st.file_uploader("처방전을 촬영하거나 업로드하세요.", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, caption="업로드된 처방전", use_container_width=True)
            
            # --- #1 피드백 반영: 개인정보 마스킹 시뮬레이션 ---
            if st.button("보안 분석 및 분석 시작", use_container_width=True, type="primary"):
                with st.status("🛡️ 개인정보 보호 처리 중...", expanded=True) as status:
                    st.write("1. 로컬 기기 내 이미지 스캔 중...")
                    time.sleep(0.8)
                    st.write("2. 민감 정보(주민번호, 성명) 식별 및 마스킹 완료")
                    time.sleep(0.8)
                    st.write("3. 조제용 약물 정보만 추출하여 보안 전송")
                    status.update(label="✅ 온디바이스 보안 처리 완료!", state="complete", expanded=False)
                time.sleep(0.5)
                st.session_state.step = 2.5; st.rerun()

    elif st.session_state.step == 2.5:
        st.subheader("📋 처방 정보 확인")
        st.caption("개인정보 보호를 위해 성명 및 주민번호는 마스킹 처리되었습니다.")
        drug_info = pd.DataFrame({"구분":["혈압약", "당뇨약", "해열제"], "명칭":["아모디핀정 5mg","메토포르민서방정","타이레놀정 500mg"],"용법":["1일 1회","1일 2회","필요 시"]})
        st.table(drug_info)
        if st.button("정보 확인 완료", use_container_width=True, type="primary"): st.session_state.step = 3; st.rerun()

    elif st.session_state.step == 3:
        st.subheader("🔍 주변 약국 실시간 현황")
        # --- #3 피드백 반영: 관리자 설정 변수 기반 실시간 ETA 추출 ---
        my_lat, my_lon = 35.91, 127.07
        df_list = []
        for name in st.session_state.pharm_db.keys():
            eta_s, _, _, _, _, _ = calculate_pharm_eta(name)
            df_list.append({'약국명': name, '예상시간': eta_s, 'eta_val': float(eta_s.split('~')[0])})
        
        df = pd.DataFrame(df_list).sort_values(by='eta_val') # 시간순 정렬 [cite: 31]
        df['lat'] = my_lat + np.array([0.002, -0.002, 0.001, -0.001, 0.003, -0.003, 0.004])
        df['lon'] = my_lon + np.array([0.002, -0.002, 0.005, -0.004, 0.003, -0.005, 0.001])
        
        st.pydeck_chart(pdk.Deck(map_style='light', initial_view_state=pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14),
            layers=[pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=65)]))

        for i, row in df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"### {row['약국명']}")
                c2.subheader(f"{row['예상시간']}분")
                if st.button(f"선택하기", key=f"sel_{i}", use_container_width=True):
                    st.session_state.reservation = row; st.session_state.step = 4; st.rerun()

    elif st.session_state.step == 4:
        res = st.session_state.reservation
        st.success(f"✅ {res['약국명']} 조제 요청 완료!")
        
        # --- #2 피드백 반영: 맞춤형 영양제 광고 (수익 모델) ---
        with st.container(border=True):
            st.subheader("🌟 PharmFlow 맞춤 건강 제안")
            st.write("처방받으신 '혈압약' 성분은 **코엔자임 Q10** 수치를 낮출 수 있습니다[cite: 81, 83].")
            c_ad1, c_ad2 = st.columns([1, 2])
            with c_ad1:
                st.markdown("### 💊") # 가상 이미지
            with c_ad2:
                st.write("**[광고] 프리미엄 코큐텐 60정**")
                st.write("팜플로우 예약 환자 특가: 18,900원")
                st.button("약국에서 함께 수령하기", type="secondary")
        
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.step = 1; st.rerun()

# --- [B. 약국용 관리자 화면 - 생략 없이 기존 변수 조절 가능] ---
elif st.session_state.role == "pharmacy":
    st.title("👨‍⚕️ 약국 관리자 대시보드")
    p_name = st.selectbox("관리할 약국", list(st.session_state.pharm_db.keys()))
    
    with st.expander("⚙️ 실시간 환경 설정 (환자 앱에 즉시 반영)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.pharm_db[p_name]['T_avg'] = st.number_input("평균 조제 시간(분)", value=st.session_state.pharm_db[p_name]['T_avg'])
            st.session_state.pharm_db[p_name]['P_staff'] = st.number_input("조제 인력 수", value=st.session_state.pharm_db[p_name]['P_staff'])
        with col2:
            status = st.select_slider("현장 혼잡도(N_offline)", options=["원활", "보통", "혼잡"])
            status_map = {"원활": 0, "보통": 5, "혼잡": 15}
            st.session_state.pharm_db[p_name]['N_offline'] = status_map[status]
    
    st.info(f"💡 현재 설정 기준으로 환자에게는 **{calculate_pharm_eta(p_name)[0]}분**으로 표시됩니다.")
