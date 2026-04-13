import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="기온 분석 및 이상기온 대시보드", layout="wide")

st.title("🌡️ 기온 분석 및 이상기온 모니터링 대시보드")

# 1. 데이터 로드 (구글 시트에서 직접 가져오기)
@st.cache_data
def load_data():
    # 공유해주신 시트 ID
    sheet_id = "13HrIz6OytYDykXeXzXJ02I6XbaKin1YaKBoO2kBd6Bs"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df['일자'] = pd.to_datetime(df['일자'])
    df['연도'] = df['일자'].dt.year
    df['월'] = df['일자'].dt.month
    df['일'] = df['일자'].dt.day
    return df

df = load_data()

# 분석 기준 연도 (데이터셋의 가장 마지막 연도)
max_year = int(df['연도'].max())
target_year = max_year

# 2. 통합 컨트롤 UI (최상단) - 전체 분석 월 선택
st.subheader("🗓️ 전체 분석 월 선택")
selected_month = st.selectbox("", list(range(1, 13)), index=0, format_func=lambda x: f"{x}월")

st.markdown("---")

# 해당 월의 연도별 평균 기온 계산
monthly_avg = df[df['월'] == selected_month].groupby('연도')['평균기온(℃)'].mean().reset_index()

# ---------------------------------------------------------
# 3. 최상단: 월 평균기온 현황 요약 표
# ---------------------------------------------------------
st.header(f"📋 {selected_month}월 평균기온 현황 요약 (과거 데이터 및 이상 판별)")

if target_year in monthly_avg['연도'].values and len(monthly_avg[monthly_avg['연도'] < target_year]) >= 7:
    # 최근 7년 데이터 추출
    past_7_years = monthly_avg[(monthly_avg['연도'] >= target_year - 7) & (monthly_avg['연도'] < target_year)].copy()
    past_7_values = past_7_years['평균기온(℃)'].tolist()
    past_7_years_list = past_7_years['연도'].tolist()
    
    # 지표 계산
    curr_val = round(monthly_avg[monthly_avg['연도'] == target_year]['평균기온(℃)'].values[0], 1)
    mean_7yr = past_7_years['평균기온(℃)'].mean()
    
    max_idx = past_7_years['평균기온(℃)'].idxmax()
    min_idx = past_7_years['평균기온(℃)'].idxmin()
    past_5_years = past_7_years.drop(index=[max_idx, min_idx])
    
    mean_5yr = round(past_5_years['평균기온(℃)'].mean(), 1)
    std_5yr = np.sqrt(np.sum((past_5_years['평균기온(℃)'] - mean_5yr)**2) / 5)
    
    is_abnormal = abs(curr_val - mean_5yr) > std_5yr

    # 표 데이터 생성
    table_data = {
        '구분': ['월 평균', '5년 평균', '표준편차'],
        **{str(yr): ['', '', ''] for yr in past_7_years_list},
        '7년 평균': [f"{mean_7yr:.1f}", '', ''],
        str(target_year): [f"{curr_val:.1f}", '', '']
    }
    
    for i, yr in enumerate(past_7_years_list):
        table_data[str(yr)][0] = f"{past_7_values[i]:.1f}"
        
    table_data['구분'][1] = '5년 평균'
    table_data[str(target_year)][1] = f"{mean_5yr:.1f}"
    
    table_data['구분'][2] = '표준편차'
    table_data[str(target_year)][2] = f"{std_5yr:.4f}"
    
    if is_abnormal:
        table_data['구분'].append('판별결과')
        for k in table_data.keys():
            if k == '구분': continue
            table_data[k].append('')
        table_data[str(target_year)][3] = '🚨 이상'

    st.dataframe(pd.DataFrame(table_data), hide_index=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. 이상기온 판별 섹션 상세 (디자인 및 가독성 대폭 개선)
    # ---------------------------------------------------------
    st.header(f"🚨 {selected_month}월 이상기온 판별 상세 (한국가스공사 기준)")
    
    # [추가] 이상기온 발생 여부에 따른 직관적 알람 배너
    if is_abnormal:
        st.error(f"🚨 **주의:** {target_year}년 {selected_month}월은 가스공사 기준 **'이상기온'**으로 판별되었습니다! (도시가스 실적 변동에 유의하세요)", icon="🚨")
    else:
        st.success(f"✅ {target_year}년 {selected_month}월은 가스공사 기준 **'정상 기온'** 범위 내에 있습니다.", icon="✅")
    
    st.write("") # 약간의 여백 추가

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("최근 7년 평균", f"{mean_7yr:.1f}℃")
    m_col2.metric("5년 평균 (최대/최소 제외)", f"{mean_5yr:.1f}℃")
    m_col3.metric("5년 표준편차", f"{std_5yr:.2f}")
    
    status_text = "이상기온 발생!" if is_abnormal else "정상 범위"
    status_color = "inverse" if is_abnormal else "normal"
    m_col4.metric(f"기준 연도({target_year}) 평균", f"{curr_val:.1f}℃", delta=status_text, delta_color=status_color)

    fig_abnormal = go.Figure()
    
    # 정상 범위 하한/상한 계산
    lower_bound = mean_5yr - std_5yr
    upper_bound = mean_5yr + std_5yr

    # 정상 범위 대역 (디자인 개선: 테두리 추가 및 색상 조정)
    fig_abnormal.add_vrect(
        x0=lower_bound, x1=upper_bound,
        fillcolor="#2ca02c", opacity=0.15, layer="below", 
        line_width=1, line_dash="dot", line_color="green",
        annotation_text="정상 기온 범위", annotation_position="top left",
        annotation_font=dict(color="green", size=13, size=13)
    )
    
    # 5년 평균 기준선
    fig_abnormal.add_vline(
        x=mean_5yr, 
        line=dict(color="green", width=2, dash="dash"), 
        annotation_text=f"5년 평균 ({mean_5yr:.1f}℃)", 
        annotation_position="bottom right"
    )

    # [추가] 정상 범위 상한/하한 수치 표기 (그래프 내 직접 텍스트)
    fig_abnormal.add_annotation(
        x=lower_bound, y=-0.5, 
        text=f"◀ 하한: {lower_bound:.2f}℃", 
        showarrow=False, font=dict(color="green", size=12), xanchor="right"
    )
    fig_abnormal.add_annotation(
        x=upper_bound, y=-0.5, 
        text=f"상한: {upper_bound:.2f}℃ ▶", 
        showarrow=False, font=dict(color="green", size=12), xanchor="left"
    )

    # 당해연도 표식
    marker_color = "#d62728" if is_abnormal else "#1f77b4"
    fig_abnormal.add_trace(go.Scatter(
        x=[curr_val], y=[0], mode="markers+text", name=f"{target_year}년",
        marker=dict(size=35, color=marker_color, symbol="diamond", line=dict(color="white", width=2)),
        text=[f"<b>{target_year}년 ({curr_val}℃)</b>"], textposition="top center",
        textfont=dict(size=15, color=marker_color)
    ))
    
    # 과거 7년 데이터 포인트 (점 디자인 세련되게 변경)
    fig_abnormal.add_trace(go.Scatter(
        x=past_7_years['평균기온(℃)'], y=[0]*7, mode="markers", name="과거 7년",
        marker=dict(size=14, color="rgba(128, 128, 128, 0.5)", line=dict(color="gray", width=1)),
        hoverinfo="x+name"
    ))
    
    fig_abnormal.update_layout(
        height=320, 
        yaxis=dict(showticklabels=False, range=[-1.2, 1.2], showgrid=False, zeroline=False), 
        xaxis=dict(title="평균기온(℃)", gridcolor="#f0f0f0", showline=True, linecolor='lightgray'),
        showlegend=False,
        margin=dict(l=40, r=40, t=50, b=40),
        plot_bgcolor="white"
    )
    st.plotly_chart(fig_abnormal, use_container_width=True)

else:
    st.info("데이터가 충분하지 않습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 5. 일별 평균기온 매트릭스 (하단 평균 행 추가)
# ---------------------------------------------------------
st.header("📊 상세 일별 기온 매트릭스")

min_year_val = int(df['연도'].min())
selected_years = st.slider("기온 매트릭스 연도 범위 설정", min_year_val, max_year, (min_year_val, max_year))

filtered_df = df[(df['월'] == selected_month) & 
                 (df['연도'] >= selected_years[0]) & 
                 (df['연도'] <= selected_years[1])]

# 피벗 테이블 생성 (1~31일)
pivot_df = filtered_df.pivot(index='일', columns='연도', values='평균기온(℃)')
pivot_df = pivot_df.reindex(range(1, 32))

# --- 핵심: 월 평균 행 추가 ---
avg_series = filtered_df.groupby('연도')['평균기온(℃)'].mean()
pivot_df.loc['평균'] = avg_series 

# 매트릭스 시각화
fig_heatmap = px.imshow(
    pivot_df,
    labels=dict(x="연도", y="일", color="평균기온(℃)"),
    x=pivot_df.columns,
    y=pivot_df.index,
    color_continuous_scale='RdBu_r',
    aspect="auto",
    text_auto='.1f'  
)

fig_heatmap.update_yaxes(autorange="reversed", tickmode='linear')
fig_heatmap.update_xaxes(side="top", tickangle=0)

fig_heatmap.update_layout(
    height=850, # 평균 행 추가를 고려해 살짝 높임
    margin=dict(l=40, r=40, t=80, b=40)
)
fig_heatmap.update_traces(textfont=dict(size=14))

st.plotly_chart(fig_heatmap, use_container_width=True)
