import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'reservation' not in st.session_state:
    st.session_state.reservation = None

def get_est_time(avg, queue, staff):
    if staff == 0: return 999
    return int((queue * avg) / staff + 5)

# --- [#1 & #2. 메인 및 권한 동의] ---
if st.session_state.step == 1:
    st.title("💊 PharmFlow")
    st.write("내 시간에 맞는 약국으로")
    
    with st.container(border=True):
        st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
        st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
        if st.button("확인", use_container_width=True, type="primary"):
            st.session_state.step = 2
            st.rerun()

# --- [#3 & #4. 업로드 및 분석 화면] ---
elif st.session_state.step == 2:
    st.title("PharmFlow")
    st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.")
    
    st.subheader("📸 처방전 업로드")
    uploaded_file = st.file_uploader("이미지를 업로드하거나 촬영하세요.", type=['jpg', 'png', 'jpeg'])
    
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("분석 시작", use_container_width=True, type="primary"):
                with st.spinner("🔍 처방전 성분을 분석 중입니다..."):
                    time.sleep(2)
                    # 사진 검증 로직 (용량 기준)
                    if uploaded_file.size < 50000:
                        st.error("❌ 처방전 형식이 아닙니다. 처방전을 다시 찍어주세요.")
                    else:
                        st.session_state.step = 2.5
                        st.rerun()
        with col2:
            if st.button("⬅️ 이전 단계로", use_container_width=True):
                st.session_state.step = 1
                st.rerun()

# --- [#3.5. OCR 정보 확인 단계] ---
elif st.session_state.step == 2.5:
    st.subheader("📋 처방전 정보 인식 결과")
    st.success("사진에서 약 정보를 성공적으로 추출했습니다.")
    
    drug_info = pd.DataFrame({
        "구분": ["약 이름", "약 이름", "약 이름"],
        "인식된 명칭": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
        "용법/용량": ["1일 1회 식후", "1일 2회 식후", "필요 시 1정"],
        "비고": ["혈압강하제", "당뇨병약", "해열진통제"]
    })
    st.table(drug_info)
    
    st.warning("⚠️ 위 정보가 처방전 내용과 일치합니까?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("정보 확인 완료", use_container_width=True, type="primary"):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("⬅️ 재촬영 하기", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

# --- [#5 & #6. 지도 화면 및 약국 선택 (번호 매기기 적용)] ---
elif st.session_state.step == 3:
    st.subheader("🔍 주변 약국 실시간 현황")
    
    my_lat, my_lon = 35.91, 127.07 # 완주 삼례 기준
    np.random.seed(42)
    pharm_names = ['삼례종로약국', '우석약국', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
    
    lats = my_lat + (np.random.uniform(-0.005, 0.005, size=7))
    lons = my_lon + (np.random.uniform(-0.005, 0.005, size=7))
    
    df = pd.DataFrame({
        '약국명': pharm_names,
        'lat': lats,
        'lon': lons,
        'avg': [8, 7, 10, 9, 8, 11, 9],
        'queue': [5, 1, 12, 4, 3, 15, 6],
        'staff': [2, 2, 2, 2, 2, 1, 2]
    })
    
    # 조제 예상 시간 계산 및 정렬
    df['예상시간'] = df.apply(lambda x: get_est_time(x['avg'], x['queue'], x['staff']), axis=1)
    df = df.sort_values(by='예상시간').reset_index(drop=True)
    
    # 약국에 번호(ID) 부여 (1번부터 시작)
    df['id'] = range(1, len(df) + 1)
    df['id_str'] = df['id'].astype(str)

    # 지도 레이어
    view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)

    # 1) 약국 마커 (빨간 동그라미)
    layer_points = pdk.Layer(
        "ScatterplotLayer", df, get_position='[lon, lat]',
        get_color='[255, 75, 75, 200]', get_radius=60,
    )

    # 2) 내 위치 (파란색 큰 점)
    layer_me = pdk.Layer(
        "ScatterplotLayer", pd.DataFrame({'lat': [my_lat], 'lon': [my_lon]}),
        get_position='[lon, lat]', get_color='[0, 120, 255, 255]', get_radius=85,
    )

    # 3) 번호 표시 (동그라미 정중앙에 숫자 띄우기)
    layer_id_text = pdk.Layer(
        "TextLayer",
        df,
        get_position='[lon, lat]',
        get_text='id_str',
        get_size=26,
        get_color=[255, 255, 255], # 흰색 숫자로 선명하게
        get_alignment_baseline="'center'",
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer_points, layer_me, layer_id_text],
        initial_view_state=view_state,
        map_style=None
    ))
    
    st.write("---")
    st.caption("📍 파란 점이 현재 위치이며, 숫자는 하단 리스트의 번호와 일치합니다.")
    
    if st.button("⬅️ 이전 단계 (처방 정보 확인)", use_container_width=True):
        st.session_state.step = 2.5
        st.rerun()

    # 하단 약국 리스트 (번호 표시)
    for i in range(len(df)):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                # 번호와 약국명을 함께 표시
                st.markdown(f"### {df.iloc[i]['id']}. {df.iloc[i]['약국명']}")
            with col2:
                st.subheader(f"{df.iloc[i]['예상시간']}분")
            
            if st.button(f"{df.iloc[i]['id']}번 약국 예약하기", key=f"book_{i}", use_container_width=True):
                st.session_state.reservation = df.iloc[i]
                st.session_state.step = 4
                st.rerun()

# --- [#7~#9. 최종 완료] ---
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
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 다시 선택하기", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.step = 1
            st.session_state.reservation = None
            st.rerun()
