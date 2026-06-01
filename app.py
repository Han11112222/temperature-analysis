import streamlit as st
import pandas as pd
import plotly.express as px

# 기존 데이터프레임 변수명이 df라고 가정합니다.
# 데이터프레임의 첫 번째 컬럼명이 '구분'이고, 나머지 컬럼이 '1', '2' ... '12'인 기준입니다.

st.divider() # 시각적 분리선
st.subheader("📈 연도별 실적 및 예측 시나리오 비교")

# 1. 단추(위젯) 영역 생성: 두 개의 컬럼으로 나누어 배치
col1, col2 = st.columns(2)

with col1:
    # 데이터에서 연도(숫자)만 추출하여 내림차순 정렬
    year_list = [str(x) for x in df['구분'] if str(x).isdigit()]
    year_list.sort(reverse=True)
    
    # 최신 기온 연도 선택 (기본값: 가장 최신 연도인 2026)
    selected_year = st.selectbox(
        "최신 실적 연도 선택",
        options=year_list,
        index=0 
    )

with col2:
    # 4가지 예측 시나리오 선택 단추
    pred_list = [
        "[예측] ① 3년 평균",
        "[예측] ② 이상기온 제외",
        "[예측] ③ Max/Min 제외",
        "[예측] ④ 선형추세"
    ]
    selected_pred = st.radio(
        "예측 시나리오 선택",
        options=pred_list
    )

# 2. 그래프용 데이터 전처리
# 선택한 연도의 데이터 추출
df_year = df[df['구분'] == selected_year].drop(columns=['구분']).T
df_year.columns = [selected_year]

# 선택한 예측 데이터 추출
df_pred = df[df['구분'] == selected_pred].drop(columns=['구분']).T
df_pred.columns = [selected_pred]

# 그래프를 위해 두 데이터를 하나로 병합
df_plot = pd.concat([df_year, df_pred], axis=1)
df_plot.index.name = '월'
df_plot.reset_index(inplace=True)

# X축 가독성을 위해 '1' -> '1월' 형태로 변경
df_plot['월'] = df_plot['월'].astype(str) + "월"

# 3. Plotly를 활용한 동적 꺾은선 그래프 생성
fig = px.line(
    df_plot,
    x='월',
    y=[selected_year, selected_pred],
    markers=True, # 데이터 포인트에 마커 표시
    title=f"{selected_year}년 실적 vs {selected_pred} 비교",
    labels={'value': '평균기온 (℃)', 'variable': '구분'}
)

# 2026년처럼 아직 도래하지 않은 달의 데이터(None/NaN)가 그래프에서 끊기지 않게 처리
fig.update_traces(connectgaps=False) 

# 화면에 그래프 출력
st.plotly_chart(fig, use_container_width=True)
