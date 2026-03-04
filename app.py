import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정 및 상태 관리] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

# 단계별 관리를 위한 세션 상태 초기화
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

# --- [#3 & #4. 업로드 화면] ---
elif st.session_state.step == 2:
    st.title("PharmFlow")
    st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.")
    
    st.subheader("📸 처방전 업로드")
    uploaded_file = st.file_uploader("이미지를 업로드하거나 촬영하세요.", type=['jpg', 'png', 'jpeg'])
    
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        
        # 버튼 2개 나열 (분석 / 이전으로)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("분석 시작", use_container_width=True, type="primary"):
                # [OCR 검증 로직]
                with st.spinner("🔍 처방전 성분을 분석 중입니다..."):
                    time.sleep(2)
                    # 파일 이름이나 크기로 가짜 사진 판별 (발표용 시나리오)
                    if "cat" in uploaded_file.name.lower() or uploaded_file.size < 50000:
                        st.error("❌ 처방전 형식이 아닙니다. 처방전을 다시 찍어주세요.")
                    else:
                        st.session_state.step = 2.5
                        st.rerun()
        with col2:
            if st.button("⬅️ 이전 단계로", use_container_width=True):
                st.session_state.step = 1
                st.rerun()

# --- [#3.5. OCR 데이터 추출 및 확인 (신규)] ---
elif st.session_state.step == 2.5:
    st.subheader("📋 처방전 정보 인식 결과")
    st.success("사진에서 약 정보를 성공적으로 추출했습니다.")
    
    # 약학 전공 지식을 활용한 처방 데이터 구성
    drug_info = pd.DataFrame({
        "구분": ["약 이름", "약 이름", "약 이름"],
        "인식된 명칭": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
        "용법/용량": ["1일 1회 식후", "1일 2회 식후", "필요 시 1정"],
        "비고": ["혈압강하제", "당뇨병약", "해열진통제"]
    })
    
    # 표로 정리해서 보여주기
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

# --- [#5 & #6. 지도 화면 및 약국 선택] ---
elif st.session_state.step == 3:
    st.subheader("🔍 주변 약국 실시간 현황")
    
    my_lat, my_lon = 35.91, 127.07
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
    
    df['예상시간'] = df.apply(lambda x: get_est_time(x['avg'], x['queue'], x['staff']), axis=1)
    df = df.sort_values(by='예상시간').reset_index(drop=True)

    # 파란색 내 위치
    me_df = pd.DataFrame({'lat': [my_lat], 'lon': [my_lon]})

    # [지도 레이어] - 이름표가 안 보이는 문제 해결을 위해 설정을 강화함
    view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)

    # 빨간 점 (약국)
    layer_points = pdk.Layer(
        "ScatterplotLayer", df, get_position='[lon, lat]',
        get_color='[255, 75, 75, 200]', get_radius=60,
    )

    # 파란 점 (나)
    layer_me = pdk.Layer(
        "ScatterplotLayer", me_df, get_position='[lon, lat]',
        get_color='[0, 120, 255, 255]', get_radius=80,
    )

    # 이름표 (검은색 글자, 배경색 없이 뚜렷하게)
    layer_text = pdk.Layer(
        "TextLayer",
        df,
        get_position='[lon, lat]',
        get_text='약국명',
        get_size=24, # 크기 더 키움
        get_color=[0, 0, 0, 255], # 완전 검정
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -15], # 점 위로 충분히 띄움
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer_points, layer_me, layer_text],
        initial_view_state=view_state,
        map_style=None
    ))
    
    st.write("---")
    st.caption("📍 파란 점이 현재 내 위치입니다.")
    
    if st.button("⬅️ 이전 단계 (처방 정보)", use_container_width=True):
        st.session_state.step = 2.5
        st.rerun()

    for i in range(len(df)):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{df.iloc[i]['약국명']}**")
            with col2:
                st.subheader(f"{df.iloc[i]['예상시간']}분")
            
            if st.button("선택 및 예약", key=f"book_{i}", use_container_width=True):
                st.session_state.reservation = df.iloc[i]
                st.session_state.step = 4
                st.rerun()

# --- [#7, #8, #9. 최종 완료] ---
elif st.session_state.step == 4:
    res = st.session_state.reservation
    st.balloons()
    st.success("✅ 조제 예약이 완료되었습니다!")
    
    with st.container(border=True):
        st.markdown(f"### ⏱️ **{res['예상시간']}분 후**")
        st.write("예약하신 약이 완료될 예정입니다.")
        st.write("---")
        st.warning("📍 약국에 도착하면 처방전을 데스크에 제출해주세요.")
        st.info(f"**{res['약국명']}** 조제 예약 완료")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 약국 다시 선택", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("🏠 처음으로 돌아가기", use_container_width=True):
            st.session_state.step = 1
            st.session_state.reservation = None
            st.rerun()
