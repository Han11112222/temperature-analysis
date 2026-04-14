import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="기온 분석 및 이상기온 대시보드", layout="wide")

st.title("🌡️ 기온 분석 및 이상기온 모니터링 대시보드")

# 1. 데이터 로드 (구글 시트 연동 유지)
@st.cache_data(ttl=600)
def load_data():
    sheet_id = "13HrIz6OytYDykXeXzXJ02I6XbaKin1YaKBoO2kBd6Bs"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    
    if '공급량(M3)' in df.columns:
        df['공급량(M3)'] = pd.to_numeric(df['공급량(M3)'].astype(str).str.replace(',', ''), errors='coerce')
        
    df['일자'] = pd.to_datetime(df['일자'])
    df['연도'] = df['일자'].dt.year
    df['월'] = df['일자'].dt.month
    df['일'] = df['일자'].dt.day
    return df

df = load_data()

max_year = int(df['연도'].max())
target_year = max_year

# 2. 통합 컨트롤 UI
st.subheader("🗓️ 전체 분석 월 선택")
selected_month = st.selectbox("", list(range(1, 13)), index=0, format_func=lambda x: f"{x}월")

st.markdown("---")

monthly_avg = df[df['월'] == selected_month].groupby('연도')['평균기온(℃)'].mean().reset_index()

if '공급량(M3)' in df.columns:
    supply_data = df[df['월'] == selected_month].groupby('연도')['공급량(M3)'].sum().reset_index()
else:
    supply_data = pd.DataFrame({'연도': monthly_avg['연도'], '공급량(M3)': 0})

def get_supply(yr):
    val = supply_data[supply_data['연도'] == yr]['공급량(M3)'].values
    return val[0] if len(val) > 0 and not pd.isna(val[0]) else 0

valid_supplies = [get_supply(y) for y in monthly_avg['연도'] if get_supply(y) > 0]
max_s, min_s = (max(valid_supplies), min(valid_supplies)) if valid_supplies else (1, 0)

def scale_size(v):
    if v == 0 or max_s == min_s: return 15
    return 15 + ((v - min_s) / (max_s - min_s)) * 35 

# ---------------------------------------------------------
# 3. 최상단: 월 평균기온 현황 요약 표 (★ 배경 하이라이트 기능 추가)
# ---------------------------------------------------------
st.header(f"📋 {selected_month}월 평균기온 현황 요약")

if target_year in monthly_avg['연도'].values and len(monthly_avg[monthly_avg['연도'] < target_year]) >= 7:
    past_7_years = monthly_avg[(monthly_avg['연도'] >= target_year - 7) & (monthly_avg['연도'] < target_year)].copy()
    past_7_years_list = past_7_years['연도'].tolist()
    
    curr_val = round(monthly_avg[monthly_avg['연도'] == target_year]['평균기온(℃)'].values[0], 1)
    mean_7yr = past_7_years['평균기온(℃)'].mean()
    
    max_idx = past_7_years['평균기온(℃)'].idxmax()
    min_idx = past_7_years['평균기온(℃)'].idxmin()
    past_5_years = past_7_years.drop(index=[max_idx, min_idx])
    
    mean_5yr = round(past_5_years['평균기온(℃)'].mean(), 1)
    std_5yr = np.sqrt(np.sum((past_5_years['평균기온(℃)'] - mean_5yr)**2) / 5)
    is_abnormal = abs(curr_val - mean_5yr) > std_5yr

    past_7_temps = [round(monthly_avg[monthly_avg['연도'] == yr]['평균기온(℃)'].values[0], 1) for yr in past_7_years_list]
    max_t, min_t = max(past_7_temps), min(past_7_temps)

    table_data = {'구분': ['월 평균', '판별 요약']}
    
    for i, yr in enumerate(past_7_years_list):
        t = past_7_temps[i]
        t_str = f"🔺 {t}" if t == max_t else (f"🔻 {t}" if t == min_t else f"{t}")
        table_data[str(yr)] = [t_str, '']

    table_data['7년 평균'] = [f"{mean_7yr:.1f}", '']
    table_data[str(target_year)] = [f"{curr_val}", '']

    if len(past_7_years_list) >= 3:
        table_data[str(past_7_years_list[0])][1] = f"5년 평균 : {mean_5yr:.1f}℃"
        table_data[str(past_7_years_list[1])][1] = f"표준편차 : {std_5yr:.4f}"
        table_data[str(past_7_years_list[2])][1] = f"판정결과 : {'🚨 이상' if is_abnormal else '✅ 정상'}"

    df_table = pd.DataFrame(table_data)

    # ★ 데이터프레임 스타일링 함수 (이상고온: 붉은배경, 이상저온: 푸른배경)
    def apply_highlight(x):
        df_style = pd.DataFrame('', index=x.index, columns=x.columns)
        if is_abnormal:
            # 5년 평균보다 높으면 이상고온(붉은색), 낮으면 이상저온(푸른색)
            bg_color = '#ffebee' if curr_val > mean_5yr else '#e3f2fd'
            text_color = '#d32f2f' if curr_val > mean_5yr else '#1976d2'
            col_idx = df_table.columns.get_loc(str(target_year))
            # 첫 번째 줄('월 평균')의 당해연도 셀에만 스타일 적용
            df_style.iloc[0, col_idx] = f'background-color: {bg_color}; color: {text_color}; font-weight: bold;'
        return df_style

    styled_table = df_table.style.apply(apply_highlight, axis=None)
    st.dataframe(styled_table, hide_index=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. 이상기온 판별 상세 (공급량 비례 버블 차트 유지)
    # ---------------------------------------------------------
    st.header(f"🚨 {selected_month}월 이상기온 판별 상세 (한국가스공사 기준)")
    
    if is_abnormal:
        st.error(f"🚨 **주의:** {target_year}년 {selected_month}월은 가스공사 기준 **'이상기온'**으로 판별되었습니다! (도시가스 실적 변동에 유의하세요)", icon="🚨")
    else:
        st.success(f"✅ {target_year}년 {selected_month}월은 가스공사 기준 **'정상 기온'** 범위 내에 있습니다.", icon="✅")
    
    st.write("")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("최근 7년 평균", f"{mean_7yr:.1f}℃")
    m_col2.metric("5년 평균 (최대/최소 제외)", f"{mean_5yr:.1f}℃")
    m_col3.metric("5년 표준편차", f"{std_5yr:.2f}")
    
    status_text = "이상기온 발생!" if is_abnormal else "정상 범위"
    status_color = "inverse" if is_abnormal else "normal"
    m_col4.metric(f"기준 연도({target_year}) 평균", f"{curr_val:.1f}℃", delta=status_text, delta_color=status_color)

    fig_abnormal = go.Figure()
    lower_bound = mean_5yr - std_5yr
    upper_bound = mean_5yr + std_5yr

    fig_abnormal.add_vrect(
        x0=lower_bound, x1=upper_bound,
        fillcolor="#00BFFF", opacity=0.1, layer="below", 
        line_width=1, line_dash="solid", line_color="#00BFFF",
    )
    
    fig_abnormal.add_annotation(x=lower_bound, y=0.9, text=f"<b>하한: {lower_bound:.2f}℃</b>", showarrow=False, font=dict(color="#00BFFF", size=13), xanchor="right", yanchor="top")
    fig_abnormal.add_annotation(x=upper_bound, y=0.9, text=f"<b>상한: {upper_bound:.2f}℃</b>", showarrow=False, font=dict(color="#00BFFF", size=13), xanchor="left", yanchor="top")
    
    fig_abnormal.add_vline(x=mean_5yr, line=dict(color="#2ca02c", width=2, dash="dash"), annotation_text=f"5년 평균 ({mean_5yr:.1f}℃)", annotation_position="bottom right", annotation_font=dict(color="#2ca02c"))

    sizes_7yr, texts_7yr, x_vals = [], [], []
    for _, row in past_7_years.iterrows():
        y = int(row['연도'])
        if y == target_year - 1: continue 
        s = get_supply(y)
        sizes_7yr.append(scale_size(s))
        texts_7yr.append(f"<b>{y}년</b><br>평균기온: {row['평균기온(℃)']:.1f}℃<br>공급량: {s:,.0f} M3")
        x_vals.append(row['평균기온(℃)'])

    fig_abnormal.add_trace(go.Scatter(
        x=x_vals, y=[0]*len(x_vals), mode="markers", name="과거 7년",
        marker=dict(size=sizes_7yr, color="rgba(128, 128, 128, 0.5)", line=dict(color="gray", width=1)),
        hoverinfo="text", text=texts_7yr
    ))

    y1_year = target_year - 1
    if y1_year in past_7_years['연도'].values:
        y1_val = past_7_years[past_7_years['연도'] == y1_year]['평균기온(℃)'].values[0]
        y1_s = get_supply(y1_year)
        fig_abnormal.add_trace(go.Scatter(
            x=[y1_val], y=[0], mode="markers+text", name=f"작년({y1_year}년)",
            marker=dict(size=scale_size(y1_s), color="#9467bd", symbol="diamond", line=dict(color="white", width=2)),
            text=[f"<b>{y1_year}년 ({y1_val:.1f}℃)</b>"], textposition="top center", textfont=dict(size=13, color="#9467bd"),
            hoverinfo="text", hovertext=f"<b>{y1_year}년</b><br>평균기온: {y1_val:.1f}℃<br>공급량: {y1_s:,.0f} M3"
        ))

    curr_s = get_supply(target_year)
    fig_abnormal.add_trace(go.Scatter(
        x=[curr_val], y=[0], mode="markers+text", name=f"{target_year}년",
        marker=dict(size=scale_size(curr_s), color="#FF8C00", symbol="circle", line=dict(color="white", width=2)),
        text=[f"<b>{target_year}년 ({curr_val}℃)</b>"], textposition="bottom center", textfont=dict(size=15, color="#FF8C00"),
        hoverinfo="text", hovertext=f"<b>{target_year}년</b><br>평균기온: {curr_val:.1f}℃<br>공급량: {curr_s:,.0f} M3"
    ))
    
    fig_abnormal.update_layout(
        height=320, 
        yaxis=dict(showticklabels=False, range=[-1.3, 1.3], showgrid=False, zeroline=False), 
        xaxis=dict(title="평균기온(℃)", gridcolor="#f0f0f0", showline=True, linecolor='lightgray'),
        showlegend=False, margin=dict(l=40, r=40, t=20, b=40), plot_bgcolor="white"
    )
    st.plotly_chart(fig_abnormal, use_container_width=True)

else:
    st.info("데이터가 충분하지 않습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 5. 일별 평균기온 매트릭스 (31일 및 평균 누락 강제 방지 유지)
# ---------------------------------------------------------
st.header("📊 상세 일별 기온 매트릭스")

min_year_val = int(df['연도'].min())
selected_years = st.slider("기온 매트릭스 연도 범위 설정", min_year_val, max_year, (min_year_val, max_year))

filtered_df = df[(df['월'] == selected_month) & 
                 (df['연도'] >= selected_years[0]) & 
                 (df['연도'] <= selected_years[1])]

pivot_df = filtered_df.pivot(index='일', columns='연도', values='평균기온(℃)')
pivot_df = pivot_df.reindex(list(range(1, 32)))

avg_series = filtered_df.groupby('연도')['평균기온(℃)'].mean()
pivot_df.loc['평균'] = avg_series 

pivot_df.index = pivot_df.index.astype(str)
pivot_df.columns = pivot_df.columns.astype(str)

fig_heatmap = px.imshow(
    pivot_df,
    labels=dict(x="연도", y="일", color="평균기온(℃)"),
    x=pivot_df.columns,
    y=pivot_df.index,
    color_continuous_scale='RdBu_r',
    aspect="auto",
    text_auto='.1f'  
)

fig_heatmap.update_layout(
    height=1000, 
    margin=dict(l=40, r=40, t=80, b=40),
    yaxis=dict(
        type='category',
        tickmode='linear',
        dtick=1,
        autorange='reversed'
    ),
    xaxis=dict(
        type='category', 
        tickmode='linear', 
        dtick=1, 
        side='top'
    )
)
fig_heatmap.update_traces(textfont=dict(size=14))

st.plotly_chart(fig_heatmap, use_container_width=True)
