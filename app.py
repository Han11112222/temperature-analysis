import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
 
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
# 3. 최상단: 월 평균기온 현황 요약 표
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
 
    table_data = {'구분': ['월 평균', '판정 결과', '5년 평균 :', '표준 편차 :']}
    
    if is_abnormal:
        abnormal_type = "(이상고온)" if curr_val > mean_5yr else "(이상저온)"
        target_str = f"{curr_val} {abnormal_type}"
        judgment_str = f"🚨 이상 {abnormal_type}"
    else:
        target_str = f"{curr_val}"
        judgment_str = "✅ 정상"
    
    for i, yr in enumerate(past_7_years_list):
        t = past_7_temps[i]
        if i == 0:
            table_data[str(yr)] = [f"{t}", '', f"{mean_5yr:.1f}℃", f"{std_5yr:.4f}"]
        else:
            table_data[str(yr)] = [f"{t}", '', '', '']
 
    table_data['7년 평균'] = [f"{mean_7yr:.1f}", '', '', '']
    table_data[str(target_year)] = [target_str, judgment_str, '', '']
 
    df_table = pd.DataFrame(table_data)
 
    def apply_highlight(x):
        df_style = pd.DataFrame('', index=x.index, columns=x.columns)
        
        for col in x.columns:
            if col in ['구분', '7년 평균']:
                continue
                
            val_str = x.loc[0, col]
            try:
                val = float(str(val_str).split()[0])
                
                is_anomaly_val = abs(val - mean_5yr) > std_5yr
                bg_color = '#ffebee' if (is_anomaly_val and val > mean_5yr) else ('#e3f2fd' if (is_anomaly_val and val < mean_5yr) else '')
                
                text_color = 'black'
                font_weight = 'normal'
                
                if col in [str(y) for y in past_7_years_list]:
                    if val == max_t:
                        text_color = '#d32f2f' 
                        font_weight = 'bold'
                    elif val == min_t:
                        text_color = '#1976d2' 
                        font_weight = 'bold'
                elif col == str(target_year):
                    if is_abnormal:
                        font_weight = 'bold'
 
                style_str = f'color: {text_color}; font-weight: {font_weight};'
                if bg_color:
                    style_str += f' background-color: {bg_color};'
                
                df_style.loc[0, col] = style_str
            except Exception:
                pass
 
        if is_abnormal:
            col_idx = x.columns.get_loc(str(target_year))
            text_color = '#d32f2f' if curr_val > mean_5yr else '#1976d2'
            df_style.iloc[1, col_idx] = f'color: {text_color}; font-weight: bold;'
            
        return df_style
 
    styled_table = df_table.style.apply(apply_highlight, axis=None)
    st.dataframe(styled_table, hide_index=True, use_container_width=True)
 
    st.caption("※ **이상기온 판단 기준**: 과거 7년 중 최고·최저 기온을 제외한 5년 평균 기온과의 차이 절대값이 5년 표준편차보다 큰 경우")
 
else:
    st.info("데이터가 충분하지 않습니다.")
 
st.markdown("---")
 
# ---------------------------------------------------------
# 4. 이상기온 판별 상세
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
 
fig_abnormal.add_annotation(x=lower_bound, y=0.9, text=f"<b>하한: {lower_bound:.2f}℃</b>", showarrow=False,
font=dict(color="#00BFFF", size=13), xanchor="right", yanchor="top")
fig_abnormal.add_annotation(x=upper_bound, y=0.9, text=f"<b>상한: {upper_bound:.2f}℃</b>", showarrow=False,
font=dict(color="#00BFFF", size=13), xanchor="left", yanchor="top")
 
fig_abnormal.add_vline(x=mean_5yr, line=dict(color="#2ca02c", width=2, dash="dash"),
annotation_text=f"5년 평균 ({mean_5yr:.1f}℃)", annotation_position="bottom right",
annotation_font=dict(color="#2ca02c"))
 
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
 
st.markdown("---")
 
# ---------------------------------------------------------
# 5. 일별 평균기온 매트릭스
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
 
# =====================================================================
# 6. 추가된 기능: 통합 시나리오 예측 매트릭스 및 엑셀 다운로드
# =====================================================================
st.markdown("---")
 
if st.toggle("📈 평균기온 10년 분석 및 미실적 월 예측 활성화"):
    st.header("🔮 연도별 월별 평균기온 및 시나리오 예측 매트릭스")
    
    # 1. 전체 10년 치 기본 데이터 구성
    monthly_all = df.groupby(['연도', '월'])['평균기온(℃)'].mean().reset_index()
    pivot_all = monthly_all.pivot(index='연도', columns='월', values='평균기온(℃)')
    
    for m in range(1, 13):
        if m not in pivot_all.columns:
            pivot_all[m] = np.nan
    pivot_all = pivot_all[list(range(1, 13))]
    
    start_year = target_year - 9
    recent_10_years = list(range(start_year, target_year + 1))
    
    for y in recent_10_years:
        if y not in pivot_all.index:
            pivot_all.loc[y] = [np.nan] * 12
            
    pivot_10yr = pivot_all.loc[recent_10_years].copy().sort_index()
    
    # 2. 모든 월(1~12월)에 대해 시나리오 예측 계산 수행
    pred_data = {
        '[예측] ① 3년 평균': [''] * 12,
        '[예측] ② 이상기온 제외': [''] * 12,
        '[예측] ③ Max/Min 제외 평균': [''] * 12,
        '[예측] ④ 선형추세': [''] * 12
    }
    
    for m in range(1, 13):
        hist_data = pivot_all.loc[start_year:target_year-1, m].dropna()
        if len(hist_data) >= 3:
            mean_3y = hist_data.iloc[-3:].mean()
            
            mean_val_10y = hist_data.mean()
            std_val_10y = hist_data.std(ddof=0)
            if std_val_10y > 0:
                hist_normal = hist_data[abs(hist_data - mean_val_10y) <= std_val_10y]
                mean_normal = hist_normal.mean() if len(hist_normal) > 0 else mean_val_10y
            else:
                mean_normal = mean_val_10y
 
            hist_ex_abnormal = hist_data[~hist_data.index.isin([hist_data.idxmax(), hist_data.idxmin()])]
            mean_ex_maxmin = hist_ex_abnormal.mean() if len(hist_ex_abnormal) > 0 else hist_data.mean()
            
            x = hist_data.index.values
            y = hist_data.values
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            trend_val = p(target_year)
            
            pred_data['[예측] ① 3년 평균'][m-1] = f"{mean_3y:.1f}"
            pred_data['[예측] ② 이상기온 제외'][m-1] = f"{mean_normal:.1f}"
            pred_data['[예측] ③ Max/Min 제외 평균'][m-1] = f"{mean_ex_maxmin:.1f}"
            pred_data['[예측] ④ 선형추세'][m-1] = f"{trend_val:.1f}"
    
    pred_df = pd.DataFrame(pred_data).T
    pred_df.columns = list(range(1, 13))
    
    # 데이터 병합 및 열 이름 정리
    combined_df = pd.concat([pivot_10yr, pred_df])
    combined_df = combined_df.reset_index()
    combined_df.rename(columns={'index': '구분'}, inplace=True)
 
    def apply_matrix_style(df_input):
        style_df = pd.DataFrame('', index=df_input.index, columns=df_input.columns)
        
        for idx in df_input.index:
            gubun_val = str(df_input.loc[idx, '구분'])
            if '[예측]' in gubun_val:
                style_df.loc[idx, :] = 'background-color: #f8f9fa; font-weight: bold; color: #444444; text-align: center;'
                style_df.loc[idx, '구분'] = 'background-color: #f8f9fa; font-weight: bold; color: #444444; text-align: left; white-space: nowrap;'
            else:
                style_df.loc[idx, '구분'] = 'text-align: left; font-weight: bold; white-space: nowrap;'
                
        hist_indices = list(range(len(recent_10_years)))
        
        for m in range(1, 13):
            hist_series = pd.to_numeric(df_input.loc[hist_indices, m], errors='coerce').dropna()
            
            mean_val, std_val = 0, 0
            if len(hist_series) >= 3:
                max_idx = hist_series.idxmax()
                min_idx = hist_series.idxmin()
                ex_series = hist_series.drop(index=[max_idx, min_idx], errors='ignore')
                
                if len(ex_series) > 0:
                    mean_val = ex_series.mean()
                    std_val = np.sqrt(np.sum((ex_series - mean_val)**2) / len(ex_series))
                else:
                    mean_val = hist_series.mean()
            
            for idx in hist_indices:
                val = df_input.loc[idx, m]
                if pd.notna(val) and val != "":
                    try:
                        val_f = float(val)
                        if std_val > 0 and abs(val_f - mean_val) > std_val:
                            if val_f > mean_val:
                               style_df.loc[idx, m] = 'background-color: #ffebee; color: black; text-align: center;'
                            else:
                               style_df.loc[idx, m] = 'background-color: #e3f2fd; color: black; text-align: center;'
                        else:
                            style_df.loc[idx, m] = 'text-align: center;'
                    except ValueError:
                        style_df.loc[idx, m] = 'text-align: center;'
                else:
                    style_df.loc[idx, m] = 'text-align: center;'
                    
        return style_df
 
    def custom_format(x):
        if pd.isna(x) or x == "": return ""
        if isinstance(x, (int, float)): return f"{x:.1f}"
        return str(x)
 
    styled_pivot = combined_df.style.format(custom_format, subset=list(range(1, 13))) \
                                   .apply(apply_matrix_style, axis=None)
                               
    st.dataframe(styled_pivot, use_container_width=True, hide_index=True, height=600)
 
    st.write("") # 버튼 위 여백 확보
    
    # ---------------------------------------------------------
    # 엑셀 파일 다운로드
    # ---------------------------------------------------------
    try:
        # openpyxl 엔진을 활용해 정식 .xlsx 포맷으로 변환 시도
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='기온예측매트릭스')
            
        st.download_button(
            label="📥 엑셀 파일 다운로드 (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"{target_year}년_기온예측_시나리오.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ImportError:
        # 클라우드에 openpyxl 모듈이 없을 경우, 엑셀에서 한글이 깨지지 않는 utf-8-sig CSV 포맷으로 우회 제공
        csv_data = combined_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 엑셀(CSV) 파일 다운로드",
            data=csv_data,
            file_name=f"{target_year}년_기온예측_시나리오.csv",
            mime="text/csv"
        )

    # ---------------------------------------------------------
    # ★ 추가된 기능: 동적 꺾은선 그래프
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 연도별 실적 및 예측 시나리오 비교")

    col1, col2 = st.columns(2)

    with col1:
        # combined_df에서 연도(숫자)만 추출하여 내림차순 정렬
        year_list = [str(x) for x in combined_df['구분'] if str(x).isdigit()]
        year_list.sort(reverse=True)
        
        selected_year = st.selectbox(
            "최신 실적 연도 선택",
            options=year_list,
            index=0 
        )

    with col2:
        # combined_df의 인덱스 이름과 완벽히 일치하도록 설정
        pred_list = [
            "[예측] ① 3년 평균",
            "[예측] ② 이상기온 제외",
            "[예측] ③ Max/Min 제외 평균", 
            "[예측] ④ 선형추세"
        ]
        selected_pred = st.radio(
            "예측 시나리오 선택",
            options=pred_list
        )

    # 그래프용 데이터 전처리 (combined_df 사용)
    df_year = combined_df[combined_df['구분'].astype(str) == selected_year].drop(columns=['구분']).T
    df_year.columns = [selected_year]

    df_pred = combined_df[combined_df['구분'] == selected_pred].drop(columns=['구분']).T
    df_pred.columns = [selected_pred]

    df_plot = pd.concat([df_year, df_pred], axis=1)
    df_plot.index.name = '월'
    df_plot.reset_index(inplace=True)

    # ★ 데이터를 그래프로 그리기 위해 숫자형(float)으로 강제 변환하여 오류 원천 차단
    df_plot[selected_year] = pd.to_numeric(df_plot[selected_year], errors='coerce')
    df_plot[selected_pred] = pd.to_numeric(df_plot[selected_pred], errors='coerce')

    # x축 월 표시 문자열로 변환
    df_plot['월'] = df_plot['월'].astype(str) + "월"

    # Plotly 라인 차트 생성
    fig_line = px.line(
        df_plot,
        x='월',
        y=[selected_year, selected_pred],
        markers=True,
        title=f"{selected_year}년 실적 vs {selected_pred} 비교",
        labels={'value': '평균기온 (℃)', 'variable': '구분'}
    )
    
    # 1월~12월 순서가 꼬이지 않도록 축 카테고리 순서 고정 및 빈 값 연결 설정
    fig_line.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=[f"{i}월" for i in range(1, 13)]
        )
    )
    fig_line.update_traces(connectgaps=False) 

    st.plotly_chart(fig_line, use_container_width=True)
