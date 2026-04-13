import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="기온 매트릭스 분석", layout="wide")

st.title("🌡️ 기온 매트릭스 및 이상기온 분석")

# 1. 데이터 로드 (구글 시트에서 직접 가져오기)
@st.cache_data
def load_data():
    sheet_id = "13HrIz6OytYDykXeXzXJ02I6XbaKin1YaKBoO2kBd6Bs"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df['일자'] = pd.to_datetime(df['일자'])
    df['연도'] = df['일자'].dt.year
    df['월'] = df['일자'].dt.month
    df['일'] = df['일자'].dt.day
    return df

df = load_data()

# 2. 상단 컨트롤 UI (연도 범위 및 월 선택)
col1, col2 = st.columns([2, 1])
with col2:
    selected_month = st.selectbox("분석 대상 월 선택", list(range(1, 13)), index=0)

with col1:
    min_year, max_year = int(df['연도'].min()), int(df['연도'].max())
    selected_years = st.slider("기온 매트릭스 연도 범위", min_year, max_year, (min_year, max_year))

st.markdown("---")

# ---------------------------------------------------------
# 3. 최상단: 가스공사 기준 이상기온 판별 (최근 7년 기준)
# ---------------------------------------------------------
st.header(f"🚨 {selected_month}월 이상기온 판별 (한국가스공사 기준)")

# 해당 월의 연도별 평균 기온 계산
monthly_avg = df[df['월'] == selected_month].groupby('연도')['평균기온(℃)'].mean().reset_index()

# 분석 기준 연도 (데이터셋의 가장 마지막 연도)
target_year = max_year

if target_year in monthly_avg['연도'].values and len(monthly_avg[monthly_avg['연도'] < target_year]) >= 7:
    # 최근 7년 데이터 추출 (기준 연도 제외)
    past_7_years = monthly_avg[(monthly_avg['연도'] >= target_year - 7) & (monthly_avg['연도'] < target_year)].copy()
    
    # 7년 평균
    mean_7yr = past_7_years['평균기온(℃)'].mean()
    
    # 최대, 최소 제외한 5년 데이터
    max_idx = past_7_years['평균기온(℃)'].idxmax()
    min_idx = past_7_years['평균기온(℃)'].idxmin()
    past_5_years = past_7_years.drop(index=[max_idx, min_idx])
    
    # 5년 평균 (가스공사 기준: 소수점 첫째자리 반올림)
    mean_5yr = round(past_5_years['평균기온(℃)'].mean(), 1)
    
    # 5년 표준편차 (가스공사 산정식 반영: 모표준편차 분모 5 적용)
    std_5yr = np.sqrt(np.sum((past_5_years['평균기온(℃)'] - mean_5yr)**2) / 5)
    
    # 당해연도 평균기온
    curr_val = round(monthly_avg[monthly_avg['연도'] == target_year]['평균기온(℃)'].values[0], 1)
    
    # 이상기온 판별 (5년 평균과의 차이 절대값이 표준편차보다 큰 경우)
    is_abnormal = abs(curr_val - mean_5yr) > std_5yr
    
    # 요약 지표 (Metrics) 표시
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("최근 7년 평균", f"{mean_7yr:.1f}℃")
    m_col2.metric("5년 평균 (최대/최소 제외)", f"{mean_5yr:.1f}℃")
    m_col3.metric("5년 표준편차", f"{std_5yr:.2f}")
    
    status_text = "이상기온 발생!" if is_abnormal else "정상 범위"
    status_color = "inverse" if is_abnormal else "normal"
    m_col4.metric(f"기준 연도({target_year}) 평균", f"{curr_val:.1f}℃", delta=status_text, delta_color=status_color)

    # 시각화: 정상 범위 대역과 당해연도 기온 비교
    fig_bullet = go.Figure()

    # 정상 범위 대역 (표준편차 범위)
    fig_bullet.add_vrect(
        x0=mean_5yr - std_5yr, x1=mean_5yr + std_5yr,
        fillcolor="green", opacity=0.15,
        layer="below", line_width=0,
        annotation_text="정상 범위 (5년 평균 ± 표준편차)", annotation_position="top left"
    )

    # 5년 평균 기준선
    fig_bullet.add_trace(go.Scatter(
        x=[mean_5yr, mean_5yr], y=[-1, 1],
        mode="lines", name="5년 평균", 
        line=dict(color="gray", width=2, dash="dash")
    ))

    # 당해연도 마커
    marker_color = "#d62728" if is_abnormal else "#1f77b4" # 이상기온이면 빨간색, 정상은 파란색
    fig_bullet.add_trace(go.Scatter(
        x=[curr_val], y=[0],
        mode="markers+text", name=f"{target_year}년",
        marker=dict(size=24, color=marker_color, symbol="diamond"),
        text=[f"<b>{target_year}년 ({curr_val}℃)</b>"], textposition="top center"
    ))

    fig_bullet.update_layout(
        height=200,
        yaxis=dict(showticklabels=False, range=[-1, 1]),
        xaxis=dict(title="평균기온(℃)"),
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_bullet, use_container_width=True)

else:
    st.info("과거 7년치 데이터가 충분히 누적되지 않아 이상기온 판별 로직을 계산할 수 없습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 4. 일별 평균기온 매트릭스 (상세 분석)
# ---------------------------------------------------------
st.header("📊 상세 일별 기온 매트릭스")
st.info("💡 **분석 포인트:** 동절기 판매량은 **월초에 추워졌을 때** 실적 기여도가 훨씬 높습니다. 매트릭스 상단의 푸른색 분포를 확인하세요.")

# 데이터 필터링
filtered_df = df[(df['월'] == selected_month) & 
                 (df['연도'] >= selected_years[0]) & 
                 (df['연도'] <= selected_years[1])]

pivot_df = filtered_df.pivot(index='일', columns='연도', values='평균기온(℃)')
pivot_df = pivot_df.reindex(range(1, 32))

# 매트릭스 시각화
fig_heatmap = px.imshow(
    pivot_df,
    labels=dict(x="연도", y="일", color="평균기온(℃)"),
    x=pivot_df.columns,
    y=pivot_df.index,
    color_continuous_scale='RdBu_r',
    aspect="equal",  # 1:1 비율 적용 (가로세로 비율 고정)
    text_auto='.1f'  # 셀 내부에 기온 텍스트 표시 (소수점 1자리)
)

fig_heatmap.update_yaxes(autorange="reversed", tickmode='linear', dtick=1)
fig_heatmap.update_xaxes(side="top") # 연도를 상단에 표시하여 보기 편하게 조정

st.plotly_chart(fig_heatmap, use_container_width=True)
