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

    # ★ [핵심 해결 방법] 데이터를 그래프로 그리기 위해 무조건 숫자형(float)으로 강제 변환
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
