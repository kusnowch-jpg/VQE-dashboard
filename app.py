import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import plotly.express as px

# --- 1. 페이지 및 디자인 설정 ---
st.set_page_config(page_title="VQE 지능형 작업 현황 대시보드", layout="wide")

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

# --- 2. 하이브리드 매핑 함수 (추가된 핵심 기능) ---

@st.cache_data(ttl=600) # 구글 시트 데이터 10분간 캐시
def load_google_sheet(url):
    """구글 시트에서 수동 매핑 데이터를 가져옵니다."""
    try:
        sheet_id = url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/1BKPCgK1cookirMYE24KkUgYmzMCc8S719I33d-X31CU/export?format=csv"
        return pd.read_csv(csv_url)
    except:
        return None

@st.cache_data(ttl=86400) # 네이버 검색 결과 24시간 캐시
def fetch_naver_title(filename):
    """구글 시트에 없을 경우 네이버 검색으로 타이틀을 유추합니다."""
    # 파일명 정제 (확장자 및 특수기호 제거)
    clean_query = re.sub(r'\[.*?\]|_|\.mpg|\.mp4|\.mkv', ' ', filename).strip()
    url = f"https://search.naver.com/search.naver?query={clean_query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 방송 프로그램 제목 또는 검색 결과 타이틀 추출
        title_tag = soup.select_one('h2._title strong') or soup.select_one('.api_title_area .tit_box .tit')
        return title_tag.get_text().strip() if title_tag else clean_query
    except:
        return clean_query

def get_hybrid_title(filename, mapping_df, use_naver):
    """하이브리드 로직: 시트 우선 -> 네이버 검색 -> 기본 정제 순"""
    # 1순위: 구글 시트 매핑
    if mapping_df is not None and not mapping_df.empty:
        match = mapping_df[mapping_df['파일명'] == filename]
        if not match.empty:
            return match.iloc[0]['참조타이틀'], "Google Sheet"
    
    # 2순위: 네이버 검색
    if use_naver:
        return fetch_naver_title(filename), "Naver Search"
    
    # 3순위: 기본 정제 로직
    temp_title = re.sub(r'\[.*?\]|\d+', '', filename).strip().replace('_', ' ')
    return temp_title if temp_title else "미분류 타이틀", "Default"

# --- 3. 사이드바 메뉴 및 파일 업로드 ---

# ※ 여기에 본인의 구글 시트 주소를 입력하세요.
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1BKPCgK1cookirMYE24KkUgYmzMCc8S719I33d-X31CU/edit"

with st.sidebar:
    st.header("🚀 VQE Dashboard")
    menu = st.radio("MENU", ("📊 실적 대시보드", "📑 완료 콘텐츠 리스트"))
    st.divider()
    
    st.header("⚙️ 지능형 매핑 설정")
    enable_naver = st.toggle("네이버 AI 검색 활성화", value=True)
    if st.button("🔄 캐시 및 참조데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    st.header("📂 데이터 관리")
    uploaded_file = st.file_uploader("인코딩 결과 CSV 업로드", type=["csv"])

# --- 4. 메인 로직 ---
mapping_data = load_google_sheet(GOOGLE_SHEET_URL)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 날짜 컬럼 자동 인식
    date_col = '완료시간' if '완료시간' in df.columns else ('생성일자' if '생성일자' in df.columns else None)
    
    if date_col:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])
    else:
        st.error("CSV에 '완료시간' 또는 '생성일자' 컬럼이 필요합니다.")
        st.stop()

    if '파일명' in df.columns:
        # 하이브리드 매핑 적용
        with st.spinner('지능형 타이틀 매핑 중...'):
            unique_files = df['파일명'].unique()
            # 중복 계산 방지를 위해 고유 파일명만 먼저 매핑
            mapped_results = {f: get_hybrid_title(f, mapping_data, enable_naver) for f in unique_files}
            
            df['타이틀'] = df['파일명'].map(lambda x: mapped_results[x][0])
            df['매핑출처'] = df['파일명'].map(lambda x: mapped_results[x][1])

            # 장르 추출 (기존 로직)
            def extract_genre(filename):
                if "드라마" in filename: return "드라마"
                elif "예능" in filename: return "예능"
                elif "시사" in filename or "교양" in filename: return "시사"
                return "기타"
            df['장르'] = df['파일명'].apply(extract_genre)
            
            genre_order = ["드라마", "예능", "시사", "기타"]
            df['장르'] = pd.Categorical(df['장르'], categories=genre_order, ordered=True)

        # --- [페이지 1] 실적 대시보드 ---
        if menu == "📊 실적 대시보드":
            st.markdown('<div class="main-header"><h1>📊 VQE 작업 현황 요약</h1></div>', unsafe_allow_html=True)
            
            counts = df['장르'].value_counts(sort=False)
            total_count = len(df)
            
            m_total, m1, m2, m3, m4 = st.columns(5)
            m_total.metric("📁 전체 완료", f"{total_count} 편")
            m1.metric("📺 드라마", f"{counts.get('드라마', 0)} 편")
            m2.metric("🏃 예능", f"{counts.get('예능', 0)} 편")
            m3.metric("📰 시사", f"{counts.get('시사', 0)} 편")
            m4.metric("📦 기타", f"{counts.get('기타', 0)} 편")
            
            st.divider()

            # (작업 추이 분석 - 기존 그래프 로직 유지)
            st.subheader(f"📈 작업 추이 분석 ({date_col} 기준)")
            df_sorted = df.sort_values('작업날짜')
            df_sorted['count'] = 1
            
            df_weekly = df_sorted.resample('W-MON', on='작업날짜')[['count']].sum().reset_index()
            df_weekly['작업날짜'] = df_weekly['작업날짜'] - pd.Timedelta(days=7)
            
            df_sorted['연월'] = df_sorted['작업날짜'].dt.strftime('%Y-%m')
            df_monthly = df_sorted.groupby('연월')[['count']].sum().reset_index()

            t1, t2 = st.tabs(["🗓️ 주간 추이", "📅 월별 현황"])
            with t1:
                fig_weekly = px.line(df_weekly, x='작업날짜', y='count', markers=True)
                fig_weekly.update_xaxes(tickformat="%m-%d")
                st.plotly_chart(fig_weekly, use_container_width=True)
            with t2:
                fig_monthly = px.bar(df_monthly, x='연월', y='count', text_auto=True)
                st.plotly_chart(fig_monthly, use_container_width=True)

        # --- [페이지 2] 완료 콘텐츠 리스트 ---
        elif menu == "📑 완료 콘텐츠 리스트":
            st.markdown('<div class="main-header"><h1>📑 상세 작업 리스트</h1></div>', unsafe_allow_html=True)
            
            col_s1, col_s2 = st.columns([2, 1])
            with col_s1:
                search_query = st.text_input("🔍 타이틀 검색", placeholder="프로그램 명을 입력하세요.")
            with col_s2:
                selected_genre = st.multiselect("🏷️ 장르 필터", options=["드라마", "예능", "시사", "기타"], default=["드라마", "예능", "시사", "기타"])
            
            display_df = df[['매핑출처', '장르', '타이틀', '파일명', date_col]].drop_duplicates()
            display_df = display_df.sort_values(by=[date_col], ascending=False)
            
            if search_query:
                display_df = display_df[display_df['타이틀'].str.contains(search_query, case=False)]
            display_df = display_df[display_df['장르'].isin(selected_genre)]
            
            st.info(f"총 **{len(display_df)}**건의 콘텐츠가 검색되었습니다.")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.markdown('<div class="main-header"><h1>미디어Ops팀 VQE 현황 관리</h1></div>', unsafe_allow_html=True)
    st.info("왼쪽 사이드바의 **[CSV 업로드]** 버튼을 통해 데이터를 불러와 주세요.")
