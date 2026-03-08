import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time
from datetime import datetime, timedelta, timezone

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

# 한국 시간(KST) 산출 함수
def get_kst_now():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)

# [가상 데이터베이스] 7개 약국의 환경 설정을 중앙에서 관리
if 'pharm_db' not in st.session_state:
    pharm_list = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
    st.session_state.pharm_db = {name: {
        'T_avg': 7.0, 'P_staff': 2, 'W_time': 1.0, 'B_type': 5.0, 'N_offline': 0, 'is_accepting': "예"
    } for name in pharm_list}

if 'role' not in st.session_state: st.session_state.role = None
if 'step' not in st.session_state: st.session_state.step = 1
if 'admin_step' not in st.session_state: st.session_state.admin_step = 1
if 'selected_pharmacy' not in st.session_state: st.session_state.selected_pharmacy = None
if 'reservation' not in st.session_state: st.session_state.reservation = None
if 'pharmacy_orders' not in st.session_state: st.session_state.pharmacy_orders = []
if 'completed_orders' not in st.session_state: st.session_state.completed_orders = []
if 'last_clear_time' not in st.session_state: st.session_state.last_clear_time = time.time()

# 20분 메모리 자동 삭제 로직 (1200초)
if time.time() - st.session_state.last_clear_time > 1200:
    st.session_state.completed_orders = []
    st.session_state.last_clear_time = time.time()

# --- [알고리즘: ETA 산출 함수] ---
def calculate_pharm_eta(pharm_name, w_complex=1.1):
    config = st.session_state.pharm_db[pharm_name]
    # 해당 약국 앞으로 온 온라인 예약 건수 필터링
    n_online = len([o for o in st.session_state.pharmacy_orders if o['pharm_name'] == pharm_name])
    n_wait = n_online + config['N_offline']
    numerator = n_wait * config['T_avg'] * config['W_time'] * w_complex
    eta = (numerator / config['P_staff']) + config['B_type']
    return int(eta), n_wait, config['T_avg'], config['W_time'], config['P_staff'], config['B_type']

# --- [메인 진입로] ---
if st.session_state.role is None:
    st.title("💊 PharmFlow 팜플로우")
    st.write("사용자 유형을 선택해 주세요.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🙋‍♂️ 환자용 서비스", use_container_width=True, type="primary"):
            st.session_state.role = "patient"; st.session_state.step = 1; st.rerun()
    with col2:
        if st.button("👨‍⚕️ 약국용 관리자", use_container_width=True):
            st.session_state.role = "pharmacy"; st.session_state.admin_step = 1; st.rerun()

# --- [A. 환자용 서비스] ---
elif st.session_state.role == "patient":
    # 예약 완료 전까지는 언제든 처음으로 돌아가기 버튼 노출 (사이드바)
    if st.session_state.step < 4:
        if st.sidebar.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.role = None; st.session_state.step = 1; st.rerun()

    if st.session_state.step == 1:
        st.title("💊 PharmFlow")
        with st.container(border=True):
            st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
            if st.button("확인", use_container_width=True, type="primary"): st.session_state.step = 2; st.rerun()

    elif st.session_state.step == 2:
        st.subheader("📸 처방전 업로드")
        uploaded_file = st.file_uploader("이미지를 업로드하세요.", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
            if st.button("분석 시작", use_container_width=True, type="primary"): st.session_state.step = 2.5; st.rerun()

    elif st.session_state.step == 2.5:
        st.subheader("📋 처방 정보 확인")
        drug_info = pd.DataFrame({"인식된 명칭":["아모디핀정 5mg","메토포르민서방정 500mg","타이레놀정 500mg"],"용법":["1일 1회","1일 2회","필요 시"]})
        st.table(drug_info)
        if st.button("정보 확인 완료", use_container_width=True, type="primary"): st.session_state.step = 3; st.rerun()

    elif st.session_state.step == 3:
        st.subheader("🔍 주변 약국 실시간 현황")
        my_lat, my_lon = 35.91, 127.07
        pharm_names = list(st.session_state.pharm_db.keys())
        
        # 실시간 데이터베이스 연동 ETA 산출
        df_list = []
        for name in pharm_names:
            eta, _, _, _, _, _ = calculate_pharm_eta(
