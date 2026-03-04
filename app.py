import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- [1. 초기 설정] ---
st.set_page_config(page_title="💊PharmFlow", layout="centered")

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'reservation' not in st.session_state:
    st.session_state.reservation = None

# 예상 시간 계산 함수
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

# --- [#3 & #4. 업로드 및 OCR 분석 화면] ---
elif st.session_state.step == 2:
    st.title("PharmFlow")
    st.info("💡 처방전을 찍어 올리면 조제 가능한 약국을 찾아드려요.")
    
    st.subheader("📸 처방전 업로드")
    uploaded_file = st.file_uploader("이미지를 업로드하거나 촬영하세요.", type=['jpg', 'png', 'jpeg'])
    
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        
        if st.button("처방전 분석 시작", use_container_width=True, type="primary"):
            # [OCR 시뮬레이션]
            with st.status("🔍 처방전 데이터를 분석 중입니다...", expanded=True) as status:
                time.sleep(1.5)
                st.write("문자 추출 중 (OCR)...")
                time.sleep(1.0)
                
                # 가짜 이미지 판별 시나리오 (발표용: 파일 이름에 'error'가 들어가면 실패하게 설정 가능)
                if uploaded_file.size < 50000: # 너무 작은 파일(예시)
                    st.error("❌ 분석 실패: 처방전 형식이 아닙니다. 처방전을 다시 찍어주세요.")
                    status.update(label="분석 중단", state="error")
                else:
                    st.success("✅ 처방전 인증 완료")
                    status.update(label="분석 완료!", state="complete")
                    st.session_state.step = 2.5 # 분석 결과 확인 단계로 이동
                    st.rerun()

# --- [#3.5. 약 정보 확인 단계 (신규)] ---
elif st.session_state.step == 2.5:
    st.subheader("📋 처방 정보 확인")
    st.write("추출된 약 정보를 확인해 주세요.")
    
    # 약학 전공 지식을 반영한 샘플 데이터 (임의 설정)
    drug_data = {
        "약 이름": ["아모디핀정 5mg", "메토포르민서방정 500mg", "타이레놀정 500mg"],
        "용법": ["1일 1회 식후", "1일 2회 식후", "필요 시 복용"],
        "효능": ["혈압 조절", "당뇨 관리", "해열 진통"]
    }
    st.table(pd.DataFrame(drug_data))
    
    st.warning("⚠️ 정보가 올바른지 확인 후 아래 버튼을 눌러주세요.")
    if st.button("정보 확인 완료 (내 주변 약국 찾기)", use_container_width=True, type="primary"):
        st.session_state.step = 3
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

    # 내 위치 데이터
    me_df = pd.DataFrame({'lat': [my_lat], 'lon': [my_lon], 'name': ['내 위치']})

    # 지도 레이어 설정
    view_state = pdk.ViewState(latitude=my_lat, longitude=my_lon, zoom=14)

    # 약국 (빨간 점)
    pharm_layer = pdk.Layer(
        "ScatterplotLayer", df, get_position='[lon, lat]',
        get_color='[255, 75, 75, 200]', get_radius=55,
    )

    # 내 위치 (파란 점)
    me_layer = pdk.Layer(
        "ScatterplotLayer", me_df, get_position='[lon, lat]',
        get_color='[0, 100, 255, 255]', get_radius=80,
    )

    # [핵심 수정] 약국 이름 텍스트 - 크기를 키우고 가독성 향상
    text_layer = pdk.Layer(
        "TextLayer", df, get_position='[lon, lat]',
        get_text='약국명',
        get_size=22, # 더 크게 키움
        get_color=[30, 30, 30], # 진한 회색
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -15]
    )

    st.pydeck_chart(pdk.Deck(
        layers=[pharm_layer, me_layer, text_layer],
        initial_view_state=view_state,
        map_style=None
    ))
    
    st.write("---")
    st.caption("📍 파란 점이 현재 내 위치입니다.")
    st.caption("거리와 조제완료 시간을 고려하여 나에게 맞는 약국을 선택하세요.")

    for i in range(len(df)):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{df.iloc[i]['약국명']}**")
            with col2:
                st.subheader(f"{df.iloc[i]['예상시간']}분")
            
            if st.button("예약하기", key=f"book_{i}", use_container_width=True):
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
        st.info(f"**{res['약국명']}** 조제 예약 완료")
    
    if st.button("처음으로 돌아가기"):
        st.session_state.step = 1
        st.session_state.reservation = None
        st.rerun()
