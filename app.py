import streamlit as st
import pandas as pd
import re
import plotly.express as px

# --- 1. 페이지 및 디자인 설정 ---
st.set_page_config(page_title="VQE 작업 현황 대시보드", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .main-header { 
        background-color: #f8f9fa; 
        padding: 25px; 
        border-bottom: 3px solid #0d6efd;
        margin-bottom: 30px;
        text-align: center;
        border-radius: 0 0 20px 20px;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff; border: 1px solid #dee2e6;
        padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 정제 함수 ---
def extract_refined_data(path_string):
    target_str = str(path_string)
    filename = target_str.split('/')[-1] if '/' in target_str else target_str
    
    genre_type = "기타"
    if "드라마" in filename: genre_type = "드라마"
    elif "예능" in filename: genre_type = "예능"
    elif "시사" in filename or "교양" in filename: genre_type = "시사"
    
    temp_title = re.sub(r'\[.*?\]', '', filename).split('.')[0]
    temp_title = re.sub(r'\d+', '', temp_title).strip()
    temp_title = temp_title.replace('_', ' ').strip()
    
    keywords = ["드라마", "예능", "시사", "교양"]
    for word in keywords:
        temp_title = temp_title.replace(word, "").strip()
    
    return genre_type, temp_title if temp_title else "미분류 타이틀"

# --- 3. 사이드바 메뉴 구성 ---
with st.sidebar:
    st.header("🚀 VQE 매니저")
    # 메뉴 선택 라디오 버튼
    menu = st.radio(
        ("📊 실적 대시보드", "📑 완료 콘텐츠 리스트")
    )
    st.divider()
    st.header("📂 데이터 관리")
    uploaded_file = st.file_uploader("인코딩 결과 CSV 업로드", type=["csv"])

# --- 4. 메인 로직 ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 날짜 처리
    date_col = '완료시간' if '완료시간' in df.columns else ('생성일자' if '생성일자' in df.columns else None)
    if date_col:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])
    
    # 장르 및 타이틀 추출
    if '파일명' in df.columns:
        df[['장르', '타이틀']] = df['파일명'].apply(lambda x: pd.Series(extract_refined_data(x)))
        genre_order = ["드라마", "예능", "시사", "기타"]
        df['장르'] = pd.Categorical(df['장르'], categories=genre_order, ordered=True)

        # --- 페이지 1: 실적 대시보드 ---
        if menu == "📊 실적 대시보드":
            st.markdown('<div class="main-header"><h1>📊 VQE 작업 현황 요약</h1></div>', unsafe_allow_html=True)
            
            # 상단 지표
            counts = df['장르'].value_counts(sort=False)
            m_total, m1, m2, m3, m4 = st.columns(5)
            m_total.metric("📁 전체 완료", f"{len(df)} 편")
            m1.metric("📺 드라마", f"{counts.get('드라마', 0)} 편")
            m2.metric("🏃 예능", f"{counts.get('예능', 0)} 편")
            m3.metric("📰 시사", f"{counts.get('시사', 0)} 편")
            m4.metric("📦 기타", f"{counts.get('기타', 0)} 편")
            
            st.divider()

            # 시계열 분석 그래프
            st.subheader("📈 기간별 추이 분석")
            df_sorted = df.sort_values('작업날짜')
            df_sorted['count'] = 1
            
            # 주간 추이 (월요일 시작 보정)
            df_weekly = df_sorted.resample('W-MON', on='작업날짜')[['count']].sum().reset_index()
            df_weekly['작업날짜'] = df_weekly['작업날짜'] - pd.Timedelta(days=7)
            
            # 월별 추이 (막대)
            df_sorted['연월'] = df_sorted['작업날짜'].dt.strftime('%Y-%m')
            df_monthly = df_sorted.groupby('연월')[['count']].sum().reset_index()

            t1, t2 = st.tabs(["주간 추이 (월요일 기준)", "월별 현황 (막대)"])
            with t1:
                fig_weekly = px.line(df_weekly, x='작업날짜', y='count', markers=True, color_discrete_sequence=['#0d6efd'])
                fig_weekly.update_xaxes(tickmode='array', tickvals=df_weekly['작업날짜'], tickformat="%m-%d")
                st.plotly_chart(fig_weekly, use_container_width=True)
            with t2:
                fig_monthly = px.bar(df_monthly, x='연월', y='count', text_auto=True, color_discrete_sequence=['#198754'])
                st.plotly_chart(fig_monthly, use_container_width=True)

        # --- 페이지 2: 완료 콘텐츠 리스트 ---
        elif menu == "📑 완료 콘텐츠 리스트":
            st.markdown('<div class="main-header"><h1>📑 상세 콘텐츠 리스트</h1></div>', unsafe_allow_html=True)
            
            # 검색 및 필터 기능 추가
            search_query = st.text_input("🔍 타이틀 검색", "")
            selected_genre = st.multiselect("🏷️ 장르 필터", options=["드라마", "예능", "시사", "기타"], default=["드라마", "예능", "시사", "기타"])
            
            # 데이터 필터링
            display_df = df[['장르', '타이틀', date_col]].drop_duplicates().sort_values(by=[date_col], ascending=False)
            if search_query:
                display_df = display_df[display_df['타이틀'].str.contains(search_query, case=False)]
            display_df = display_df[display_df['장르'].isin(selected_genre)]
            
            st.write(f"총 **{len(display_df)}**개의 항목이 검색되었습니다.")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.markdown('<div class="main-header"><h1>미디어Ops팀 VQE 현황관리</h1></div>', unsafe_allow_html=True)
    st.info("왼쪽 사이드바에서 CSV 파일을 업로드하여 분석을 시작해 주세요.")
