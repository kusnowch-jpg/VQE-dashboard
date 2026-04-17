import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. 페이지 설정 및 타이틀 수정
st.set_page_config(page_title="VQE 장르별 작업 현황", layout="wide") [cite: 651]

# 커스텀 CSS: 화이트 톤 테마 및 메트릭 카드 스타일 [cite: 620, 629]
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-top: 5px solid #007bff;
    }
    h1 { color: #1e3a8a; font-family: 'Malgun Gothic', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# 2. 경로 무시 및 파일명 파싱 함수 
def parse_vqe_filename(path_string):
    # 경로(w_folder/drama_folder/) 이후의 순수 파일명만 추출
    filename = str(path_string).split('/')[-1]
    
    genre = "기타"
    if "드라마" in filename: genre = "드라마"
    elif "예능" in filename: genre = "예능"
    elif "시사" in filename or "교양" in filename: genre = "시사" [cite: 621, 622]
    
    # 타이틀 및 편수 추출 로직 (정규표현식 활용)
    title = filename.split('_')[0].replace(f"[{genre}]", "").strip() if "_" in filename else filename
    episode = re.search(r'(\d+)회|\d+화', filename)
    ep_val = episode.group(0) if episode else "미분류"
    
    return genre, title, ep_val

# 3. 메인 화면 구성
st.title("📊 VQE 장르별 작업 현황") [cite: 651]

# 사이드바: CSV 파일 업로드
with st.sidebar:
    st.header("데이터 로드")
    uploaded_file = st.file_uploader("인코딩 결과 CSV 업로드", type=["csv"]) [cite: 544, 556]

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
    
    # '파일명' 컬럼 존재 여부 확인 후 파싱 적용
    if '파일명' in df_raw.columns:
        # 파싱 결과를 새로운 컬럼으로 추가
        df_raw[['분류장르', '타이틀', '편수']] = df_raw['파일명'].apply(
            lambda x: pd.Series(parse_vqe_filename(x))
        )
        
        # 4. 상단 메트릭: 전체 및 장르별 완료 편수 집계 [cite: 626, 627]
        total_count = len(df_raw)
        genre_counts = df_raw['분류장르'].value_counts()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📁 전체 완료", f"{total_count} 편") # f-string 문법 교정 [cite: 633, 646]
        m2.metric("📺 드라마", f"{genre_counts.get('드라마', 0)} 편") [cite: 630, 648]
        m3.metric("🏃 예능", f"{genre_counts.get('예능', 0)} 편")
        m4.metric("📰 시사", f"{genre_counts.get('시사', 0)} 편")
        
        st.write("---")
        
        # 5. 시각화 섹션 (병렬 배치) [cite: 344, 562]
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("장르별 작업 비중")
            fig_pie = px.pie(df_raw, names='분류장르', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col2:
            st.subheader("타이틀별 완료 실적 (Top 10)") [cite: 573]
            top_titles = df_raw['타이틀'].value_counts().head(10).reset_index()
            top_titles.columns = ['타이틀', '완료편수']
            fig_bar = px.bar(top_titles, x='완료편수', y='타이틀', orientation='h',
                             color='타이틀', color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_bar, use_container_width=True)

        # 6. 상세 데이터 리스트 [cite: 553, 563]
        st.subheader("📑 상세 작업 리스트")
        st.dataframe(df_raw[['분류장르', '타이틀', '편수', '파일명']], 
                     use_container_width=True, hide_index=True)
        
        # 결과 다운로드 버튼 [cite: 530, 552]
        csv = df_raw.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 파싱 결과 CSV 다운로드", data=csv, 
                           file_name="VQE_parsing_result.csv", mime="text/csv")
    else:
        st.error("CSV 파일에 '파일명' 컬럼이 포함되어야 합니다.")
else:
    st.info("왼쪽 사이드바에서 CSV 파일을 업로드해 주세요.") [cite: 413, 452]
