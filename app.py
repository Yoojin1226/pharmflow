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

# --- [알고리즘: ETA 산출 및 도보 시간 계산] ---
def calculate_pharm_eta(pharm_name, w_complex=1.1):
    config = st.session_state.pharm_db[pharm_name]
    my_active_orders = [o for o in st.session_state.pharmacy_orders if o['pharm_name'] == pharm_name]
    n_online = len(my_active_orders)
    n_wait = n_online + config['N_offline']
    
    numerator = n_wait * config['T_avg'] * config['W_time'] * w_complex
    eta_raw = (numerator / config['P_staff']) + config['B_type']
    
    # 리스트 표시용 범위 텍스트 생성
    if eta_raw % 1 == 0: eta_str = str(int(eta_raw))
    else: eta_str = f"{int(eta_raw)}~{int(eta_raw) + 1}"
        
    return eta_raw, eta_str, n_wait, config['T_avg'], config['W_time'], config['P_staff'], config['B_type']

# 직선 거리 기반 도보 시간 계산 함수 (위도 1도 대략 111km 기준)
def get_walking_time(lat1, lon1, lat2, lon2):
    dist = np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111000 # 미터 단위
    walking_min = dist / 67 # 분당 약 67m 이동 (도보 4km/h)
    return int(walking_min)

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
    with st.sidebar.expander("로그아웃", expanded=False):
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.role = None; st.session_state.step = 1; st.rerun()

    # Step 1, 2, 2.5 로직 유지 (중략)
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

    # --- [스마트 라우팅이 적용된 지도 화면] ---
    elif st.session_state.step == 3:
        st.subheader("🔍 스마트 라우팅 최적 경로")
        st.caption("🚶‍♂️도보 시간과 ⏱️조제 시간을 합산하여 가장 빠른 약국을 추천합니다.")
        
        my_lat, my_lon = 35.91, 127.07
        pharm_names = list(st.session_state.pharm_db.keys())
        # 고정된 약국 좌표 (시연용)
        lats = my_lat + np.array([0.002, -0.002, 0.001, -0.001, 0.003, -0.003, 0.004])
        lons = my_lon + np.array([0.002, -0.002, 0.005, -0.004, 0.003, -0.005, 0.001])
        
        df_list = []
        for i, name in enumerate(pharm_names):
            eta_raw, eta_str, _, _, _, _, _ = calculate_pharm_eta(name)
            walk_time = get_walking_time(my_lat, my_lon, lats[i], lons[i])
            total_time = eta_raw + walk_time # 스마트 라우팅 핵심 공식
            
            df_list.append({
                '약국명': name, 'lat': lats[i], 'lon': lons[i],
                '조제시간': eta_str, '도보시간': walk_time, '총소요시간': total_time
            })
        
        df = pd.DataFrame(df_list)
        # 총 소요 시간이 가장 짧은 순으로 정렬 (스마트 라우팅 정렬)
        df = df.sort_values(by='총소요시간').reset_index(drop=True)
        df['id'] = range(1, 8)
        df['id_str'] = df['id'].astype(str)

        # 지도 렌더링 (이전 스타일 100% 보존)
        view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
        st.pydeck_chart(pdk.Deck(
            map_style='light', initial_view_state=view_state,
            layers=[
                pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60),
                pdk.Layer("ScatterplotLayer", pd.DataFrame({'lat':[my_lat],'lon':[my_lon]}), get_position='[lon, lat]', get_color='[0, 120, 255, 255]', get_radius=85),
                pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id_str', get_size=24, get_color=[255, 255, 255], get_alignment_baseline="'center'"),
                pdk.Layer("TextLayer", pd.DataFrame({'lat':[my_lat],'lon':[my_lon],'l':['Me']}), get_position='[lon, lat]', get_text='l', get_size=22, get_color=[255, 255, 255], get_alignment_baseline="'center'")
            ]
        ))

        for i in range(len(df)):
            p_name = df.iloc[i]['약국명']
            if st.session_state.pharm_db[p_name]['is_accepting'] == "예":
                with st.container(border=True):
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        st.markdown(f"### {df.iloc[i]['id']}. {p_name}")
                        st.caption(f"🚶‍♂️ 도보 약 {df.iloc[i]['도보시간']}분 | ⏱️ 조제 약 {df.iloc[i]['조제시간']}분")
                    with c2:
                        st.subheader(f"합계 {int(df.iloc[i]['총소요시간'])}분")
                        if st.button(f"{df.iloc[i]['id']}번 선택", key=f"sel_{i}", use_container_width=True):
                            st.session_state.reservation = df.iloc[i]; st.session_state.step = 3.5; st.rerun()

    # Step 3.5: ETA 산출 근거 (스마트 라우팅 설명 추가)
    elif st.session_state.step == 3.5:
        res = st.session_state.reservation
        p_name = res['약국명']
        _, eta_s, n_w, t_a, w_t, p_s, b_t = calculate_pharm_eta(p_name)
        
        st.subheader("🧪 스마트 라우팅(Smart Routing) 논리 검증")
        st.info(f"단순 리스트가 아닌, 이동 시간과 조제 시간을 합산한 최적 경로입니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**[1] 도보 이동 시간**")
            st.write(f"- 현재 위치 기준: 약 {res['도보시간']}분")
        with col2:
            st.write(f"**[2] 조제 예상 시간**")
            st.write(f"- 실시간 변수 대입: 약 {eta_s}분")
            
        st.write("---")
        st.latex(rf"Total = Walking({res['도보시간']}) + ETA({eta_s}) = {int(res['총소요시간'])}min")
        
        if st.button("최적 경로 확정 및 조제 요청", use_container_width=True, type="primary"):
            res_time = get_kst_now().strftime("%H:%M")
            st.session_state.pharmacy_orders.append({
                "order_id": f"P-{int(time.time()*1000)%1000000}", "pharm_name": p_name, "res_time": res_time, "status": "접수됨"
            })
            st.session_state.step = 4; st.rerun()
        if st.button("⬅️ 다시 선택하기", use_container_width=True): st.session_state.step = 3; st.rerun()

    # Step 4: 완료 화면 (범위 시간 반영)
    elif st.session_state.step == 4:
        res = st.session_state.reservation
        st.balloons(); st.success("✅ 조제 예약이 최종 완료되었습니다!")
        with st.container(border=True):
            st.markdown(f"### ⏱️ **{res['조제시간']}분 후**")
            st.write("예약하신 약이 완료될 예정입니다.")
            st.write("---")
            st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
            st.info(f"**[{res['약국명']}]** 조제 요청 완료 (이동시간 포함 총 {int(res['총소요시간'])}분 예상)")
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.role = None; st.session_state.step = 1; st.rerun()

# --- [B. 약국용 관리자 화면 - 기존 로직 100% 유지] ---
# (이하 관리자 코드는 이전과 동일하므로 생략하지만 실제 파일에는 포함되어야 함)
elif st.session_state.role == "pharmacy":
    # (이전 관리자 코드 삽입)
    with st.sidebar.expander("로그아웃", expanded=False):
        if st.button("로그아웃", use_container_width=True): st.session_state.role = None; st.session_state.admin_step = 1; st.rerun()
    if st.session_state.admin_step == 1:
        selected = st.selectbox("관리하실 약국 선택", list(st.session_state.pharm_db.keys()))
        if st.button("관리 시작 ➡️", use_container_width=True, type="primary"): st.session_state.selected_pharmacy = selected; st.session_state.admin_step = 2; st.rerun()
    elif st.session_state.admin_step == 2:
        st.title(f"🏢 {st.session_state.selected_pharmacy} 관리")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ 약국 환경 설정", use_container_width=True, type="primary"): st.session_state.admin_step = 3; st.rerun()
        with col2:
            if st.button("📥 조제 예약 관리", use_container_width=True): st.session_state.admin_step = 4; st.rerun()
    elif st.session_state.admin_step == 3:
        p_name = st.session_state.selected_pharmacy
        with st.container(border=True):
            st.session_state.pharm_db[p_name]['T_avg'] = st.number_input("평균 조제 시간(분)", value=st.session_state.pharm_db[p_name]['T_avg'])
            st.session_state.pharm_db[p_name]['P_staff'] = st.number_input("조제 인력 수", value=st.session_state.pharm_db[p_name]['P_staff'])
            status = st.select_slider("내부 혼잡도", options=["원활", "보통", "혼잡"])
            st.session_state.pharm_db[p_name]['N_offline'] = {"원활":0, "보통":3, "혼잡":6}[status]
            st.session_state.pharm_db[p_name]['B_type'] = st.selectbox("약국 유형", [5.0, 10.0, 2.0], format_func=lambda x: "내과(+5)" if x==5 else "대학병원(+10)" if x==10 else "소아과(+2)")
            st.session_state.pharm_db[p_name]['W_time'] = 1.2 if st.checkbox("피크 가중치 적용") else 1.0
        if st.button("설정 저장 ✅", use_container_width=True, type="primary"): st.session_state.admin_step = 2; st.rerun()
    elif st.session_state.admin_step == 4:
        p_name = st.session_state.selected_pharmacy
        tab1, tab2 = st.tabs(["대기 목록", "최근 조제 기록(20분)"])
        with tab1:
            my_orders = [o for o in st.session_state.pharmacy_orders if o['pharm_name'] == p_name]
            if not my_orders: st.info("요청이 없습니다.")
            else:
                for order in my_orders:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([1, 2, 1])
                        c1.write(f"**{order['order_id']}**"); c2.write(f"예약: {order['res_time']}")
                        if c3.button("조제 완료", key=f"d_{order['order_id']}", use_container_width=True, type="primary"):
                            order['done_time'] = get_kst_now().strftime("%H:%M")
                            st.session_state.completed_orders.append(order)
                            st.session_state.pharmacy_orders = [o for o in st.session_state.pharmacy_orders if o['order_id'] != order['order_id']]; st.rerun()
        if st.button("⬅️ 메뉴로 돌아가기"): st.session_state.admin_step = 2; st.rerun()
