import streamlit as st
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="급식 입찰 정밀 분석기", page_icon="🎯", layout="wide")

st.title("🎯 급식 입찰 최적 투찰금액 자동 산출기 (v5.0)")
st.markdown("업로드하신 **최신 데이터 양식**을 완벽하게 인식하도록 결측치(진행중 공고의 '-' 표기) 예외 처리 알고리즘을 탑재했습니다.")

# 1. 파일 업로드 기능
uploaded_file = st.file_uploader("전자입찰목록 데이터 (CSV 또는 엑셀)를 업로드하세요.", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # 열 이름 공백 및 줄바꿈 완벽 제거 ('낙찰금액 ' 등 띄어쓰기 방어)
        df.rename(columns=lambda x: str(x).strip().replace('\n', ''), inplace=True)
        
        # 필수 열 이름 강제 지정 (신규 양식 기준)
        col_base = '기초가격'
        col_est = '낙찰예정가'
        col_win = '낙찰금액'
        
        # ==========================================
        # 🔥 데이터 전처리 (결측치 및 문자열 '-' 예외 처리)
        # ==========================================
        # '진행중'인 공고는 금액이 '-'로 표기되어 수학 연산을 방해하므로, 안전한 숫자(NaN)로 변환
        for col in [col_base, col_est, col_win]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 분석을 위한 유효 데이터만 별도 추출 (예정가와 낙찰금액이 모두 존재하는 '낙찰 완료' 건)
        df_valid = df.dropna(subset=[col_base, col_est, col_win]).copy()
        
        if df_valid.empty:
            st.error("업로드된 데이터에 '낙찰이 완료된 유효 금액 데이터'가 없습니다. 파일 내용을 확인해주세요.")
            st.stop()
            
        # ==========================================
        # 🔥 사용자 맞춤형 2-Step 공식 적용 (유효 데이터 기준)
        # ==========================================
        # 1. 투찰율 = (낙찰예정가 / 기초가격) * 100
        df_valid['투찰율'] = (df_valid[col_est] / df_valid[col_base]) * 100
        
        # 2. 실투찰율 = (낙찰금액 / 낙찰예정가) * 100
        df_valid['실투찰율'] = (df_valid[col_win] / df_valid[col_est]) * 100
        
        # 소수점 3자리 정밀도 파생 변수
        df_valid['투찰율_정밀(3자리)'] = df_valid['투찰율'].round(3)
        df_valid['실투찰율_정밀(3자리)'] = df_valid['실투찰율'].round(3)
        
        # 금액 구간 나누기 함수
        def categorize_price(price):
            if price >= 15000000:
                return '1. 1,500만 원 이상'
            elif price >= 7000000:
                return '2. 700만 원 ~ 1,500만 원 미만'
            elif price >= 4000000:
                return '3. 400만 원 ~ 700만 원 미만'
            else:
                return '4. 400만 원 미만'
                
        df_valid['금액구간'] = df_valid[col_base].apply(categorize_price)
        
        # 화면에 보여줄 원본 데이터프레임에 빈 열을 만들고, 유효 데이터의 계산 결과를 덮어씌움
        df['투찰율'] = np.nan
        df['실투찰율'] = np.nan
        df.update(df_valid)
        
        st.markdown("---")
        
        # ==========================================
        # 상단: 2-Step 자동 투찰금액 산출기
        # ==========================================
        st.subheader("💡 2-Step 최적 투찰금액 계산기")
        
        target_price = st.number_input("입찰 공고의 '기초가격'을 입력하세요 (원단위):", min_value=0, max_value=99999999999, value=0, step=1000)
        
        if target_price > 0:
            target_category = categorize_price(target_price)
            cat_data = df_valid[df_valid['금액구간'] == target_category]
            
            if not cat_data.empty:
                # 최빈값 추출 알고리즘 구동
                mode_bid_rate = cat_data['투찰율_정밀(3자리)'].mode().iloc[0]
                mode_actual_bid_rate = cat_data['실투찰율_정밀(3자리)'].mode().iloc[0]
                
                # 예측 연산 실행
                expected_est_price = target_price * (mode_bid_rate / 100)
                optimal_bid_amount = int(expected_est_price * (mode_actual_bid_rate / 100))
                
                st.success(f"**{target_category}** 구간의 데이터를 분석하여 2단계 정밀 계산을 완료했습니다.")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info("📌 예상 낙찰예정가 비율 (투찰율)")
                    st.metric(label="(낙찰예정가 / 기초가격)", value=f"{mode_bid_rate:.3f}%")
                with col2:
                    st.info("📌 타격존 실투찰율")
                    st.metric(label="(낙찰금액 / 낙찰예정가)", value=f"{mode_actual_bid_rate:.3f}%")
                with col3:
                    st.error("🏆 최종 권장 투찰금액")
                    st.metric(label="이 금액으로 입찰하세요", value=f"{optimal_bid_amount:,}원")
                
                st.markdown("---")
                
                st.markdown(f"### 🔍 타격존 밀집도 시각화")
                st.markdown(f"경쟁자들이 가장 많이 맞춘 **실투찰율({mode_actual_bid_rate:.3f}%)**의 확률 분포입니다.")
                freq_data = cat_data['실투찰율_정밀(3자리)'].value_counts().sort_index()
                st.bar_chart(freq_data)
                
            else:
                st.warning(f"업로드된 데이터 중 '{target_category}' 구간에 해당하는 '완료된 입찰 기록'이 부족합니다.")
        
        st.markdown("---")
        
        # ==========================================
        # 🔥 하단: 지정된 11개 핵심 데이터만 노출 (결측치 포맷팅 포함)
        # ==========================================
        display_cols = ['공고번호', '수요기관명', '시작시간', '종료시간', '진행상태', col_base, '낙찰하한율', col_est, col_win, '투찰율', '실투찰율']
        available_cols = [col for col in display_cols if col in df.columns]
        
        df_display = df[available_cols].copy()
        
        # 엑셀처럼 깔끔하게 보이도록 서식 정리 ('-'와 숫자를 구분)
        def format_currency(x):
            if pd.isna(x): return "-"
            return f"{int(x):,}"
            
        def format_rate(x):
            if pd.isna(x): return "-"
            return f"{x:.4f}%"

        for col in [col_base, col_est, col_win]:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_currency)
                
        for col in ['투찰율', '실투찰율']:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_rate)
            
        st.subheader("📋 정제된 핵심 입찰 데이터")
        st.markdown("수십 개의 열 중 의사결정에 필요한 **11가지 핵심 지표**만 필터링하여 보여줍니다. *(진행 상태의 데이터는 연산에서 안전하게 제외되었습니다.)*")
        st.dataframe(df_display, use_container_width=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다. 파일 형식을 확인해주세요.\n상세 오류: {e}")
