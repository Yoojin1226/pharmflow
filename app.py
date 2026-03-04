import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow(팜플로우)", layout="centered")

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'reservation' not in st.session_state:
    st.session_state.reservation = None

def get_est_time(avg, queue, staff):
    return int((queue * avg) / staff + 5)

# --- [#1. 로고 화면 & #2. 권한 동의] ---
if st.session_state.step == 1:
    st.title("💊 PharmFlow")
    st.write("내 시간에 맞는 약국으로") 
    
    with st.container(border=True):
        st.markdown("<h1 style='text-align: center;'>📍</h1>", unsafe_allow_html=True)
        st.write("원활한 약국 찾기를 위해 위치 권한 허용에 동의해주세요.")
        if st.button("확인", use_container_width=True, type="primary"):
            st.session_state.step = 2
            st.rerun()

# --- [#3. 튜토리얼 & #4. 사진 업로드] ---
elif st.session_state.step == 2:
    st.title("PharmFlow")
    st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.") [cite: 29]
    
    st.subheader("📸 처방전 업로드")
    uploaded_file = st.file_uploader("이미지를 업로드하거나 촬영하세요.", type=['jpg', 'png', 'jpeg'])
    
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        if st.button("분석 시작", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# --- [#5. 완주 삼례 기반 지도 & #6. 약국 나열] ---
elif st.session_state.step == 3:
    st.subheader("🔍 주변 약국 실시간 현황")
    
    # 완주 삼례읍 행정복지센터 인근 좌표: 35.91, 127.07
    base_lat, base_lon = 35.91, 127.07
    
    # 무작위 약국 데이터 생성 (삼례 지역 반경 내)
    np.random.seed(42) # 고정된 무작위성
    pharm_names = ['삼례종로약국', '우석약국(추천)', '삼례정문약국', '중앙제일약국', '정성약국', '비비정약국', '삼례현대약국']
    
    lats = base_lat + (np.random.uniform(-0.005, 0.005, size=7))
    lons = base_lon + (np.random.uniform(-0.005, 0.005, size=7))
    
    df = pd.DataFrame({
        '약국명': pharm_names,
        'lat': lats,
        'lon': lons,
        'avg': [8, 7, 10, 9, 8, 11, 9],
        'queue': [5, 1, 12, 4, 3, 15, 6],
        'staff': [2, 2, 2, 2, 2, 1, 2]
    })
    
    df['예상시간'] = df.apply(lambda x: get_est_time(x['avg'], x['queue'], x['staff']), axis=1)
    df = df.sort_values(by='예상시간').reset_index(drop=True)

    # 파이덱(Pydeck)을 이용한 지도 시각화 (이름표 추가)
    view_state = pdk.ViewState(latitude=base_lat, longitude=base_lon, zoom=14, pitch=0)

    # 약국 위치 점 레이어
    layer_points = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position='[lon, lat]',
        get_color='[255, 75, 75, 160]',
        get_radius=40,
        pickable=True
    )

    # 지도 위 텍스트(약국이름) 레이어
    layer_text = pdk.Layer(
        "TextLayer",
        df,
        get_position='[lon, lat]',
        get_text='약국명',
        get_size=16,
        get_color=[0, 0, 0],
        get_alignment_baseline="'bottom'",
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer_points, layer_text],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v9'
    ))
    
    st.write("---")
    st.caption("가까운 거리와 조제완료 시간을 고려해 선택하세요.") [cite: 16]

    for i in range(len(df)):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{df.iloc[i]['약국명']}**")
                if "추천" in df.iloc[i]['약국명']:
                    st.info("✨ 대기 시간이 짧은 B급 입지 추천 약국입니다.") [cite: 18]
            with col2:
                st.subheader(f"{df.iloc[i]['예상시간']}분")
            
            if st.button("예약하기", key=f"book_{i}", use_container_width=True):
                st.session_state.reservation = df.iloc[i]
                st.session_state.step = 4
                st.rerun()

# --- [#7, #8, #9. 최종 완료 및 상세 내역] ---
elif st.session_state.step == 4:
    res = st.session_state.reservation
    st.balloons()
    
    st.success("✅ 조제 예약이 완료되었습니다!")
    
    with st.container(border=True):
        # #7. 예상 완료 시간 표시
        st.markdown(f"### ⏱️ **{res['예상시간']}분 후**")
        st.markdown("예약하신 약이 완료될 예정입니다.") [cite: 31]
        
        st.write("---")
        # #8. 데스크 제출 안내
        st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
        
        # #9. 예약 내역 상세
        st.write("📋 **내 예약 내역**")
        st.info(f"**{res['약국명']}** 조제 예약 완료")
    
    if st.button("처음으로 돌아가기"):
        st.session_state.step = 1
        st.session_state.reservation = None
        st.rerun()
