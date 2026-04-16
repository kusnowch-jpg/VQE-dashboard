import streamlit as st
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go

# --- 1. 페이지 설정 및 이미지 스타일 스타일링 ---
st.set_page_config(page_title="VQE 작업 현황 대시보드", layout="wide")

st.markdown("""
    <style>
    /* 상단 네이비 헤더 스타일 */
    .main-header {
        background-color: #2c3e50;
        padding: 15px 30px;
        color: white;
        font-size: 24px;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 25px;
        display: flex;
        align-items: center;
    }
    /* 지표 카드 공통 스타일 */
    .metric-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: left;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .card-total { background-color: #4a90e2; }
    .card-drama { background-color: #55a630; }
    .card-variety { background-color: #f3722c; }
    .card-news { background-color: #7209b7; }
    
    .card-title { font-size: 16px; font-weight: 500; opacity: 0.9; }
    .card-value { font-size: 32px; font-weight: 800; margin-top: 5px; }
    
    /* 차트 컨테이너 스타일 */
    .chart-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 처리 함수 ---
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
    return genre_type, temp_title if temp_title else "미분류"

# --- 3. 사이드바 메뉴 ---
with st.sidebar:
    st.title("⚙️ 설정")
    menu = st.radio("메뉴 이동", ("📊 대시보드", "📑 작업 리스트"))
    st.divider()
    uploaded_file = st.file_uploader("CSV 데이터 업로드", type=["csv"])

# --- 4. 메인 대시보드 로직 ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    date_col = '완료시간' if '완료시간' in df.columns else ('생성일자' if '생성일자' in df.columns else None)
    
    if date_col and '파일명' in df.columns:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])
        df[['장르', '타이틀']] = df['파일명'].apply(lambda x: pd.Series(extract_refined_data(x)))
        
        # 헤더 표시
        st.markdown('<div class="main-header">📈 VQE 작업 현황 대시보드</div>', unsafe_allow_html=True)

        if menu == "📊 대시보드":
            # --- 상단 지표 섹션 (이미지 스타일 카드) ---
            counts = df['장르'].value_counts()
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.markdown(f'<div class="metric-card card-total"><div class="card-title">✔ 총 완료 콘텐츠</div><div class="card-value">{len(df):,} 편</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card card-drama"><div class="card-title">📺 드라마</div><div class="card-value">{counts.get("드라마", 0):,} 편</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card card-variety"><div class="card-title">🎭 예능</div><div class="card-value">{counts.get("예능", 0):,} 편</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="metric-card card-news"><div class="card-title">🎙️ 시사</div><div class="card-value">{counts.get("시사", 0):,} 편</div></div>', unsafe_allow_html=True)

            st.write("") # 간격 조절
            
            # --- 차트 섹션 (이미지 레이블 참조) ---
            col_left, col_right = st.columns([1, 1.5])
            
            with col_left:
                st.subheader("⚪ 장르별 완료 비율")
                pie_fig = px.pie(df, names='장르', hole=0, 
                                 color_discrete_map={'드라마':'#55a630', '예능':'#f3722c', '시사':'#7209b7', '기타':'#adb5bd'})
                pie_fig.update_traces(textinfo='percent+label')
                pie_fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(pie_fig, use_container_width=True)

            with col_right:
                st.subheader("📊 주간 인코딩 완료 추이")
                df_weekly = df.resample('W-MON', on='작업날짜').size().reset_index(name='count')
                df_weekly['작업날짜'] = df_weekly['작업날짜'] - pd.Timedelta(days=7)
                
                bar_fig = px.bar(df_weekly, x='작업날짜', y='count', text_auto=True)
                bar_fig.update_traces(marker_color='#4a90e2')
                bar_fig.update_xaxes(tickformat="%m-%d", title=None)
                bar_fig.update_layout(yaxis_title=None, margin=dict(t=20))
                st.plotly_chart(bar_fig, use_container_width=True)

            # --- 하단 테이블 섹션 ---
            st.subheader("📋 VQE 주요 콘텐츠 리스트")
            st.dataframe(df[['장르', '타이틀', date_col]].sort_values(by=date_col, ascending=False).head(10), 
                         use_container_width=True, hide_index=True)

        elif menu == "📑 작업 리스트":
            st.markdown("### 🔍 전체 작업 상세 내역")
            st.dataframe(df[['장르', '타이틀', date_col]], use_container_width=True)

else:
    st.info("왼쪽 사이드바에서 CSV 파일을 업로드해 주세요.")
