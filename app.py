import streamlit as st
import pandas as pd
import re
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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 처리 및 매핑 함수 (컬럼명 무관 방식) ---

@st.cache_data(ttl=600)
def load_google_sheet(url):
    """구글 시트에서 데이터를 가져옵니다."""
    try:
        # URL 형식 검증 및 변환
        if "/edit" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        else:
            csv_url = url
        
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return None

def get_mapped_title(filename, mapping_df):
    """
    구글 시트의 컬럼명에 상관없이 데이터를 매핑합니다.
    - 1번째 열: 검색 키워드
    - 2번째 열: 결과 타이틀
    """
    # 1순위: 구글 시트 매핑 확인
    if mapping_df is not None and not mapping_df.empty:
        for _, row in mapping_df.iterrows():
            # 첫 번째 열의 값이 파일명에 포함되어 있는지 확인 (대소문자 무시)
            keyword = str(row.iloc[0]).strip()
            if keyword.lower() in filename.lower():
                return str(row.iloc[1]).strip(), "Google Sheet"
    
    # 2순위: 기본 정제 로직 (시트에 없거나 로드 실패 시)
    temp_title = re.sub(r'\[.*?\]', '', filename).split('.')[0] # 대괄호 제거
    temp_title = re.sub(r'\d+', '', temp_title).strip()         # 숫자 제거
    temp_title = temp_title.replace('_', ' ').replace('-', ' ').strip()
    
    return temp_title if temp_title else "미분류 콘텐츠", "Default"

# --- 3. 사이드바 구성 ---

# ※ 여기에 본인의 구글 시트 URL을 정확히 입력하세요 (공유 권한: 링크가 있는 모든 사용자/뷰어)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/your_sheet_id_here/edit"

with st.sidebar:
    st.header("🚀 VQE Dashboard")
    menu = st.radio("MENU", ("📊 실적 대시보드", "📑 완료 콘텐츠 리스트"))
    
    if st.button("🔄 구글 시트 새로고침"):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    st.header("📂 데이터 업로드")
    uploaded_file = st.file_uploader("인코딩 결과 CSV 업로드", type=["csv"])

# --- 4. 메인 로직 ---
mapping_data = load_google_sheet(GOOGLE_SHEET_URL)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 필수 컬럼 존재 확인
    if '파일명' not in df.columns:
        st.error("CSV 파일에 '파일명' 컬럼이 존재해야 합니다.")
        st.stop()

    # 날짜 컬럼 자동 인식 및 전처리
    date_col = next((c for c in ['완료시간', '생성일자', '작업시간'] if c in df.columns), None)
    if date_col:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])
    else:
        st.warning("날짜 관련 컬럼을 찾을 수 없어 시계열 분석이 제한됩니다.")

    # 지능형 매핑 적용
    with st.spinner('구글 시트와 대조하여 타이틀 정제 중...'):
        unique_files = df['파일명'].unique()
        mapped_dict = {f: get_mapped_title(f, mapping_data) for f in unique_files}
        
        df['타이틀'] = df['파일명'].map(lambda x: mapped_dict[x][0])
        df['출처'] = df['파일명'].map(lambda x: mapped_dict[x][1])

    # 장르 분류 (단순 키워드 기준)
    def assign_genre(title):
        if any(x in title for x in ["드라마", "Drama"]): return "드라마"
        if any(x in title for x in ["예능", "Show"]): return "예능"
        if any(x in title for x in ["뉴스", "시사"]): return "시사"
        return "기타"
    df['장르'] = df['타이틀'].apply(assign_genre)

    # --- [페이지 1] 실적 대시보드 ---
    if menu == "📊 실적 대시보드":
        st.markdown('<div class="main-header"><h1>📊 VQE 인코딩 실적 요약</h1></div>', unsafe_allow_html=True)
        
        # 지표 출력
        c1, c2, c3 = st.columns(3)
        c1.metric("총 작업 완료", f"{len(df)} 건")
        c2.metric("시트 매칭 성공", f"{len(df[df['출처']=='Google Sheet'])} 건")
        c3.metric("장르 종류", f"{df['장르'].nunique()} 개")
        
        st.divider()
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("📅 날짜별 작업 추이")
            if '작업날짜' in df.columns:
                trend = df.resample('D', on='작업날짜').size().reset_index(name='count')
                fig = px.line(trend, x='작업날짜', y='count', markers=True)
                st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("🍕 장르별 비중")
            fig_pie = px.pie(df, names='장르', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- [페이지 2] 완료 콘텐츠 리스트 ---
    elif menu == "📑 완료 콘텐츠 리스트":
        st.markdown('<div class="main-header"><h1>📑 상세 작업 리스트</h1></div>', unsafe_allow_html=True)
        
        # 필터링 및 검색
        search = st.text_input("🔍 결과 내 검색 (타이틀 또는 파일명)", "")
        filtered_df = df[df['타이틀'].str.contains(search, case=False) | df['파일명'].str.contains(search, case=False)]
        
        st.dataframe(
            filtered_df[['출처', '장르', '타이틀', '파일명', date_col if date_col else '파일명']], 
            use_container_width=True, 
            hide_index=True
        )

else:
    st.markdown('<div class="main-header"><h1>VQE 현황 관리 대시보드</h1></div>', unsafe_allow_html=True)
    st.info("사이드바에서 인코딩 결과 CSV 파일을 업로드하면 분석이 시작됩니다.")
    st.write("📌 **구글 시트 연동 팁**: 시트의 1열에는 파일명에 포함될 키워드를, 2열에는 변환하고 싶은 정식 명칭을 적어주세요.")
