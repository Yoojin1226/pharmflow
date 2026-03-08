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

# 20분 메모리 자동 삭제 로직
if time.time() - st.session_state.last_clear_time > 1200:
    st.session_state.completed_orders = []
    st.session_state.last_clear_time = time.time()

def calculate_pharm_eta(pharm_name, w_complex=1.1):
    config = st.session_state.pharm_db[pharm_name]
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
        
        df_list = []
        for name in pharm_names:
            eta, _, _, _, _, _ = calculate_pharm_eta(name)
            df_list.append({'약국명': name, '예상시간': eta})
        
        df = pd.DataFrame(df_list)
        df['lat'] = my_lat + np.array([0.002, -0.002, 0.001, -0.001, 0.003, -0.003, 0.004])
        df['lon'] = my_lon + np.array([0.002, -0.002, 0.005, -0.004, 0.003, -0.005, 0.001])
        df = df.sort_values(by='예상시간').reset_index(drop=True)
        df['id'] = range(1, 8)
        df['id_str'] = df['id'].astype(str)

        me_df = pd.DataFrame({'lat': [my_lat], 'lon': [my_lon], 'label': ['Me']})

        # #4 피드백 반영: 지도 바탕 오류 해결 (안정적인 light 스타일 적용)
        view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)
        st.pydeck_chart(pdk.Deck(
            map_style='light', 
            initial_view_state=view_state,
            layers=[
                pdk.Layer("ScatterplotLayer", df, get_position='[lon, lat]', get_color='[255, 75, 75, 200]', get_radius=60),
                pdk.Layer("ScatterplotLayer", me_df, get_position='[lon, lat]', get_color='[0, 120, 255, 255]', get_radius=85),
                pdk.Layer("TextLayer", df, get_position='[lon, lat]', get_text='id_str', get_size=24, get_color=[255, 255, 255], get_alignment_baseline="'center'"),
                pdk.Layer("TextLayer", me_df, get_position='[lon, lat]', get_text='label', get_size=22, get_color=[255, 255, 255], get_alignment_baseline="'center'")
            ]
        ))

        for i in range(len(df)):
            p_name = df.iloc[i]['약국명']
            if st.session_state.pharm_db[p_name]['is_accepting'] == "예":
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {df.iloc[i]['id']}. {p_name}")
                    c2.subheader(f"{df.iloc[i]['예상시간']}분")
                    if st.button(f"{df.iloc[i]['id']}번 약국 선택", key=f"sel_{i}", use_container_width=True):
                        st.session_state.reservation = df.iloc[i]; st.session_state.step = 3.5; st.rerun()

    elif st.session_state.step == 3.5:
        p_name = st.session_state.reservation['약국명']
        # #1 피드백 반영: 사라졌던 변수 표출 및 수식 복구
        eta, n_wait, t_avg, w_time, p_staff, b_type = calculate_pharm_eta(p_name)
        st.subheader("🧪 ETA 산출 근거 확인")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- 실시간 대기($N_{{wait}}$): {n_wait}건")
            st.write(f"- 평균 조제 시간($T_{{avg}}$): {t_avg}분")
            st.write(f"- 조제 인력($P_{{staff}}$): {p_staff}명")
        with col2:
            st.write(f"- 시간 가중치($W_{{time}}$): {w_time}배")
            st.write(f"- 복잡 가중치($W_{{complex}}$): 1.1배")
            st.write(f"- 약국 유형 보정($B_{{type}}$): {b_type}분")

        st.write("---")
        st.latex(r"ETA = \frac{N_{wait} \times T_{avg} \times W_{time} \times W_{complex}}{P_{staff}} + B_{type}")
        st.latex(rf"ETA = \frac{{{n_wait} \times {t_avg} \times {w_time} \times 1.1}}{{{p_staff}}} + {b_type} = {eta}분")
        
        if st.button("위 산출 근거를 확인했으며, 조제를 요청합니다", use_container_width=True, type="primary"):
            res_time = get_kst_now().strftime("%H:%M")
            st.session_state.pharmacy_orders.append({
                "order_id": f"P-{int(time.time()*1000)%1000000}", "pharm_name": p_name, "res_time": res_time, "status": "접수됨"
            })
            st.session_state.step = 4; st.rerun()

    elif st.session_state.step == 4:
        res = st.session_state.reservation
        st.balloons(); st.success("✅ 조제 예약이 최종 완료되었습니다!")
        with st.container(border=True):
            st.markdown(f"### ⏱️ **{res['예상시간']}분 후**")
            st.write("예약하신 약이 완료될 예정입니다.")
            st.write("---")
            st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
            st.info(f"**[{res['id']}번 {res['약국명']}]** 조제 예약 완료")
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.role = None; st.session_state.step = 1; st.rerun()

# --- [B. 약국용 관리자 화면] ---
elif st.session_state.role == "pharmacy":
    # #2 피드백 반영: 로그아웃 창을 Expander로 감싸 항상 닫혀 있게 설정
    with st.sidebar.expander("🚪 시스템 설정", expanded=False):
        if st.button("로그아웃", use_container_width=True):
            st.session_state.role = None; st.session_state.admin_step = 1; st.rerun()

    # Step 1: 약국 선택
    if st.session_state.admin_step == 1:
        st.title("👨‍⚕️ 약국 관리자")
        selected = st.selectbox("관리하실 약국 선택", list(st.session_state.pharm_db.keys()))
        col_prev, col_next = st.columns(2)
        with col_prev: # #3 피드백 반영: 모든 페이지에 이전으로 버튼
            if st.button("⬅️ 초기 화면", use_container_width=True): st.session_state.role = None; st.rerun()
        with col_next:
            if st.button("관리 시작 ➡️", use_container_width=True, type="primary"):
                st.session_state.selected_pharmacy = selected; st.session_state.admin_step = 2; st.rerun()

    # Step 2: 메뉴 선택
    elif st.session_state.admin_step == 2:
        st.title(f"🏢 {st.session_state.selected_pharmacy} 관리")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ 약국 환경 설정", use_container_width=True, type="primary"): st.session_state.admin_step = 3; st.rerun()
        with col2:
            if st.button("📥 조제 예약 관리", use_container_width=True): st.session_state.admin_step = 4; st.rerun()
        if st.button("⬅️ 약국 다시 선택", use_container_width=True): st.session_state.admin_step = 1; st.rerun()

    # Step 3: 환경 설정
    elif st.session_state.admin_step == 3:
        p_name = st.session_state.selected_pharmacy
        st.subheader("⚙️ 약국 환경 설정")
        with st.container(border=True):
            st.session_state.pharm_db[p_name]['T_avg'] = st.number_input("평균 조제 시간(분)", value=st.session_state.pharm_db[p_name]['T_avg'])
            st.session_state.pharm_db[p_name]['P_staff'] = st.number_input("조제 인력 수", value=st.session_state.pharm_db[p_name]['P_staff'])
            status = st.select_slider("내부 혼잡도", options=["원활", "보통", "혼잡"])
            st.session_state.pharm_db[p_name]['N_offline'] = {"원활":0, "보통":3, "혼잡":6}[status]
            st.session_state.pharm_db[p_name]['B_type'] = st.selectbox("약국 유형", [5.0, 10.0, 2.0], format_func=lambda x: "내과(+5)" if x==5 else "대학병원(+10)" if x==10 else "소아과(+2)")
            st.session_state.pharm_db[p_name]['W_time'] = 1.2 if st.checkbox("피크 가중치 적용") else 1.0
        
        col_prev, col_save = st.columns(2)
        with col_prev: # #3 피드백 반영
            if st.button("⬅️ 메뉴로 돌아가기", use_container_width=True): st.session_state.admin_step = 2; st.rerun()
        with col_save:
            if st.button("설정 저장 ✅", use_container_width=True, type="primary"): st.session_state.admin_step = 2; st.rerun()

    # Step 4: 예약 및 기록 관리
    elif st.session_state.admin_step == 4:
        p_name = st.session_state.selected_pharmacy
        st.title(f"📥 {p_name} 예약/기록")
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
                            st.session_state.pharmacy_orders = [o for o in st.session_state.pharmacy_orders if o['order_id'] != order['order_id']]
                            st.rerun()
        with tab2:
            my_done = [o for o in st.session_state.completed_orders if o['pharm_name'] == p_name]
            if my_done: st.table(pd.DataFrame(my_done)[['res_time', 'done_time', 'order_id']].rename(columns={'res_time':'예약','done_time':'완료','order_id':'ID'}))
        
        if st.button("⬅️ 메뉴로 돌아가기", use_container_width=True): st.session_state.admin_step = 2; st.rerun()
