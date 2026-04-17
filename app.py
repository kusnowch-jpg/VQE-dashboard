import streamlit as st
import pandas as pd
import re
import io
import plotly.express as px
import requests
import json
import os
import time

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

# --- 2. 네이버 API 및 캐시 관리 클래스 ---
class NaverDataRefiner:
    def __init__(self, client_id, client_secret, cache_file='title_cache.json'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.api_url = "https://openapi.naver.com/v1/search/encyc.json"

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    def get_info(self, raw_title):
        # 1. 전처리: 파일명에서 핵심 키워드만 추출
        clean_keyword = re.sub(r'\[.*?\]', '', raw_title).split('.')[0]
        clean_keyword = re.sub(r'\d+회|E\d+|\d{6}', '', clean_keyword).strip()
        clean_keyword = clean_keyword.replace('_', ' ').strip()

        if not clean_keyword: return {"title": raw_title, "genre": "미분류"}
        
        # 2. 캐시 확인
        if clean_keyword in self.cache:
            return self.cache[clean_keyword]

        # 3. API 호출 (ID/Secret이 있을 때만)
        if not self.client_id or not self.client_secret:
            return {"title": clean_keyword, "genre": "API 미설정"}

        headers = {"X-Naver-Client-Id": self.client_id, "X-Naver-Client-Secret": self.client_secret}
        try:
            res = requests.get(self.api_url, headers=headers, params={"query": clean_keyword, "display": 1})
            items = res.json().get('items', [])
            if items:
                item = items[0]
                official_title = item['title'].replace('<b>', '').replace('</b>', '')
                desc = item['description']
                genre = "기타"
                if "드라마" in desc: genre = "드라마"
                elif "예능" in desc or "방송" in desc: genre = "예능"
                elif "시사" in desc or "교양" in desc: genre = "시사"
                
                result = {"title": official_title, "genre": genre}
            else:
                result = {"title": clean_keyword, "genre": "검색결과없음"}
            
            self.cache[clean_keyword] = result
            self._save_cache()
            time.sleep(0.1) # TPS 제한 준수
            return result
        except:
            return {"title": clean_keyword, "genre": "에러"}

# --- 3. 사이드바 구성 ---
with st.sidebar:
    st.header("🚀 VQE Dashboard v4.0")
    menu = st.radio("MENU", ("📊 실적 대시보드", "📑 완료 콘텐츠 리스트"))
    
    st.divider()
    st.subheader("🔑 네이버 API 설정")
    c_id = st.text_input("Client ID", type="password")
    c_secret = st.text_input("Client Secret", type="password")
    
    st.divider()
    uploaded_file = st.file_uploader("인코딩 결과 CSV 업로드", type=["csv"])

# --- 4. 메인 로직 ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    if '파일명' not in df.columns:
        st.error("'파일명' 컬럼이 필요합니다.")
        st.stop()

    # 날짜 처리
    date_col = next((c for c in ['완료시간', '생성일자', '작업시간'] if c in df.columns), None)
    if date_col:
        df['작업날짜'] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=['작업날짜'])

    # 데이터 정제 (Naver API 사용)
    with st.spinner('네이버 API를 통해 데이터를 정제 중입니다...'):
        refiner = NaverDataRefiner(c_id, c_secret)
        unique_files = df['파일명'].unique()
        
        # API 호출 및 결과 매핑
        results = {f: refiner.get_info(f) for f in unique_files}
        df['정제타이틀'] = df['파일명'].map(lambda x: results[x]['title'])
        df['장르'] = df['파일명'].map(lambda x: results[x]['genre'])

    # --- [페이지 1] 실적 대시보드 ---
    if menu == "📊 실적 대시보드":
        st.markdown('<div class="main-header"><h1>📊 VQE 지능형 작업 요약</h1></div>', unsafe_allow_html=True)
        
        # 상단 지표
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 작업수", f"{len(df)}건")
        c2.metric("드라마", f"{len(df[df['장르']=='드라마'])}건")
        c3.metric("예능", f"{len(df[df['장르']=='예능'])}건")
        c4.metric("시사/기타", f"{len(df[~df['장르'].isin(['드라마', '예능'])])}건")
        
        st.divider()
        
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("🗓️ 주간 작업 추이")
            df_weekly = df.resample('W-MON', on='작업날짜').size().reset_index(name='count')
            fig = px.line(df_weekly, x='작업날짜', y='count', markers=True, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_r:
            st.subheader("📂 장르별 분포")
            fig_pie = px.pie(df, names='장르', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- [페이지 2] 완료 콘텐츠 리스트 ---
    elif menu == "📑 완료 콘텐츠 리스트":
        st.markdown('<div class="main-header"><h1>📑 상세 작업 내역</h1></div>', unsafe_allow_html=True)
        search = st.text_input("🔍 타이틀 검색", "")
        f_df = df[df['정제타이틀'].str.contains(search, case=False)]
        st.dataframe(f_df[['장르', '정제타이틀', '파일명', date_col]], use_container_width=True, hide_index=True)

else:
    st.markdown('<div class="main-header"><h1>VQE 현황 관리 대시보드 v4.0</h1></div>', unsafe_allow_html=True)
    st.info("사이드바에 네이버 API 키를 입력하고 CSV를 업로드해주세요.")
    st.warning("⚠️ API 키가 없으면 기본 전처리 로직만 작동합니다.")
