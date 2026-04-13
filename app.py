import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="기온 매트릭스 분석", layout="wide")

st.title("🌡️ 기온 매트릭스 (일별 평균기온)")

# 1. 데이터 로드 (구글 시트에서 직접 가져오기)
@st.cache_data
def load_data():
    # 공유해주신 구글 스프레드시트의 CSV 내보내기 링크
    sheet_id = "13HrIz6OytYDykXeXzXJ02I6XbaKin1YaKBoO2kBd6Bs"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    df = pd.read_csv(url)
    
    # 날짜 데이터 전처리
    df['일자'] = pd.to_datetime(df['일자'])
    df['연도'] = df['일자'].dt.year
    df['월'] = df['일자'].dt.month
    df['일'] = df['일자'].dt.day
    return df

df = load_data()

# 2. 상단 컨트롤 UI (연도 범위 및 월 선택)
col1, col2 = st.columns([2, 1])

with col2:
    selected_month = st.selectbox("월 선택", list(range(1, 13)), index=0)

with col1:
    min_year, max_year = int(df['연도'].min()), int(df['연도'].max())
    selected_years = st.slider("연도 범위", min_year, max_year, (min_year, max_year))

# 데이터 필터링
filtered_df = df[(df['월'] == selected_month) & 
                 (df['연도'] >= selected_years[0]) & 
                 (df['연도'] <= selected_years[1])]

# 3. 마케팅 인사이트 메시지
st.info("💡 **분석 포인트:** 동절기 판매량은 같은 월이라도 **월초에 추워졌을 때** 그 효과가 월중까지 이어져 월 마감 실적 기여도가 훨씬 높습니다. 매트릭스 상단(1일~10일)의 푸른색(저온) 분포를 집중적으로 확인해보세요.")

# 4. 히트맵 데이터 준비
# 일(day)을 Y축, 연도(year)를 X축으로 하는 피벗 테이블 생성
pivot_df = filtered_df.pivot(index='일', columns='연도', values='평균기온(℃)')

# 1일부터 31일까지 모든 일자가 표시되도록 인덱스 보장 (없는 날짜는 NaN 처리)
pivot_df = pivot_df.reindex(range(1, 32))

# 5. 매트릭스 (히트맵) 시각화
fig_heatmap = px.imshow(
    pivot_df,
    labels=dict(x="연도", y="일", color="평균기온(℃)"),
    x=pivot_df.columns,
    y=pivot_df.index,
    color_continuous_scale='RdBu_r', # 파란색(추움) ~ 빨간색(더움)
    aspect="auto"
)
# Y축(일)이 1일부터 아래로 내려가도록 설정
fig_heatmap.update_yaxes(autorange="reversed", tickmode='linear', dtick=5)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# 6. 하단 월 평균 기온 트렌드 시각화
st.subheader(f"📊 {selected_month}월 연도별 평균 기온 추이")
monthly_avg = filtered_df.groupby('연도')['평균기온(℃)'].mean().reset_index()

fig_line = px.line(
    monthly_avg, 
    x='연도', 
    y='평균기온(℃)', 
    markers=True,
    color_discrete_sequence=['#1f77b4']
)
fig_line.update_layout(yaxis_title="월 평균 기온(℃)")
st.plotly_chart(fig_line, use_container_width=True)
