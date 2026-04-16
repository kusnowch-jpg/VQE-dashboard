import streamlit as st
import pandas as pd
import re
import io
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
    div[data-testid="stMetricLabel"] { color: #6c757d; font-weight: 700; }
    div[data-testid="stMetricValue"] { color: #0d6efd; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📊 VQE 장르별 작업 현황</h1></div>', unsafe_allow_html=True)

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

# --- 3. 데이터 로직 ---
st.sidebar.header("📂 데이터 관리")
uploaded_file = st.sidebar.file_uploader("인코딩 결과 CSV 업로드", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    date_col = None
    if '완료시간' in df.columns:
        date_col = '완료시간'
    elif '생성일자' in df.columns:
        date_col = '생성일자'
    
    if date_col:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])
    else:
        st.error("CSV에 '완료시간' 또는 '생성일자' 컬럼이 필요합니다.")
        st.stop()

    if '파일명' in df.columns:
        df[['장르', '타이틀']] = df['파일명'].apply(
            lambda x: pd.Series(extract_refined_data(x))
        )
        
        genre_order = ["드라마", "예능", "시사", "기타"]
        df['장르'] = pd.Categorical(df['장르'], categories=genre_order, ordered=True)
        
        # --- 4. 상단 실적 요약 ---
        counts = df['장르'].value_counts(sort=False)
        total_count = len(df)
        
        st.subheader("📍 전체 인코딩 실적 요약")
        m_total, m1, m2, m3, m4 = st.columns(5)
        m_total.metric("📁 전체 완료", f"{total_count} 편")
        m1.metric("📺 드라마", f"{counts.get('드라마', 0)} 편")
        m2.metric("🏃 예능", f"{counts.get('예능', 0)} 편")
        m3.metric("📰 시사", f"{counts.get('시사', 0)} 편")
        m4.metric("📦 기타", f"{counts.get('기타', 0)} 편")
        
        st.divider()

        # --- 5. 시계열 분석 ---
        st.subheader(f"📈 작업 추이 분석 ({date_col} 기준)")
        
        df_sorted = df.sort_values('작업날짜')
        df_sorted['count'] = 1
        
        # 5-1. 주간별 작업 편수: 월요일 시작 보정
        # W-MON은 일주일의 끝이 월요일임을 의미하므로, 시작일을 맞추기 위해 7일을 뺍니다.
        df_weekly = df_sorted.resample('W-MON', on='작업날짜')[['count']].sum().reset_index()
        df_weekly['작업날짜'] = df_weekly['작업날짜'] - pd.Timedelta(days=7)
        
        # 5-2. 월별 작업 현황 (Bar)
        df_sorted['연월'] = df_sorted['작업날짜'].dt.strftime('%Y-%m')
        df_monthly = df_sorted.groupby('연월')[['count']].sum().reset_index()

        t1, t2 = st.tabs(["주간 작업 추이 (월요일 기준)", "월별 작업 현황 (막대)"])
        
        with t1:
            fig_weekly = px.line(df_weekly, x='작업날짜', y='count', 
                                title="주차별 완료 건수 (X축: 해당 주 월요일)",
                                labels={'count': '완료 편수', '작업날짜': '주 시작일 (월)'},
                                markers=True,
                                color_discrete_sequence=['#0d6efd'])
            
            # [수정] X축 눈금을 데이터가 있는 월요일 지점에만 정확히 표시
            fig_weekly.update_xaxes(
                tickmode='array',
                tickvals=df_weekly['작업날짜'],
                tickformat="%m-%d", # 월-일 형식
                showgrid=True
            )
            fig_weekly.update_traces(line=dict(width=3))
            st.plotly_chart(fig_weekly, use_container_width=True)
            
        with t2:
            fig_monthly = px.bar(df_monthly, x='연월', y='count', 
                                  title="월간 단위 작업 합계",
                                  labels={'count': '월간 합계', '연월': '작업 월'},
                                  text_auto=True,
                                  color_discrete_sequence=['#198754'])
            fig_monthly.update_layout(xaxis_type='category')
            st.plotly_chart(fig_monthly, use_container_width=True)

        st.divider()

        # --- 6. 상세 내역표 ---
        st.subheader("📑 완료 콘텐츠 리스트 (Unique)")
        display_df = df[['장르', '타이틀']].drop_duplicates().sort_values(by=['장르', '타이틀'])
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
    else:
        st.error("CSV 파일에 '파일명' 컬럼이 필요합니다.")