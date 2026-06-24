import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="급식 입찰 정밀 분석기", layout="wide")

st.title("🎯 급식 입찰 최적 투찰금액 자동 산출기")
st.markdown("기초가격을 입력하면, 해당 금액 구간에서 과거 가장 빈번하게 낙찰된 **최빈 투찰률**을 적용하여 **최적의 투찰금액**을 즉시 계산합니다.")

# 1. 파일 업로드 기능
uploaded_file = st.file_uploader("전자입찰목록 데이터 (CSV 또는 엑셀)를 업로드하세요.", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # 파일 읽기
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        df.rename(columns=lambda x: x.strip().replace('\n', ''), inplace=True)
        
        # 동적 컬럼 탐색
        col_base = [c for c in df.columns if '기초' in c][0]
        col_est = [c for c in df.columns if '예정가' in c][0]
        col_win = [c for c in df.columns if '낙찰금액' in c][0]
        
        # 투찰률 및 실투찰률 계산 (소수점 3자리 정밀도)
        df['투찰률(%)'] = (df[col_win] / df[col_base]) * 100
        df['실투찰률(%)'] = (df[col_win] / df[col_est]) * 100
        
        df['투찰률_정밀(3자리)'] = df['투찰률(%)'].round(3)
        df['실투찰률_정밀(3자리)'] = df['실투찰률(%)'].round(3)
        
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
                
        df['금액구간'] = df[col_base].apply(categorize_price)
        
        st.markdown("---")
        
        # ==========================================
        # 🔥 상단: 자동 투찰금액 산출기
        # ==========================================
        st.subheader("💡 최적 투찰금액 계산기")
        
        # 사용자 입력
        target_price = st.number_input("입찰 공고의 '기초가격'을 입력하세요 (원단위):", min_value=0, value=0, step=1000)
        
        if target_price > 0:
            target_category = categorize_price(target_price)
            cat_data = df[df['금액구간'] == target_category]
            
            if not cat_data.empty:
                # [핵심 로직] 해당 금액 구간의 '투찰률'과 '실투찰률' 최빈값(가장 많이 나온 값) 추출
                mode_bid_rate = cat_data['투찰률_정밀(3자리)'].mode().iloc[0]
                mode_actual_bid_rate = cat_data['실투찰률_정밀(3자리)'].mode().iloc[0]
                
                # 기초가격에 최빈 투찰률을 곱하여 최종 투찰금액 자동 계산
                # (1원 단위 절사를 위해 int 처리)
                optimal_bid_amount = int(target_price * (mode_bid_rate / 100))
                
                st.success(f"**{target_category}** 구간의 과거 데이터를 분석하여 최적의 금액을 산출했습니다.")
                
                # 결과 시각화 (강조된 메트릭 카드)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info("📌 적용된 최빈 투찰률")
                    st.metric(label="(낙찰금액/기초가격)", value=f"{mode_bid_rate:.3f}%")
                    
                with col2:
                    st.info("📌 참고용 최빈 실투찰률")
                    st.metric(label="(낙찰금액/예정가격)", value=f"{mode_actual_bid_rate:.3f}%")
                    
                with col3:
                    st.error("🏆 최종 권장 투찰금액")
                    st.metric(label="이 금액으로 입찰하세요", value=f"{optimal_bid_amount:,}원")
                
                st.markdown("---")
                
                # ==========================================
                # 시각화 차트: 데이터 밀집도 증명
                # ==========================================
                st.markdown(f"### 🔍 투찰률 분포도 (왜 **{mode_bid_rate:.3f}%** 인가?)")
                st.markdown(f"해당 금액 구간({target_category})에서 경쟁자들이 가장 많이 낙찰을 받아간 지점을 보여줍니다.")
                
                # 빈도수 계산
                freq_data = cat_data['투찰률_정밀(3자리)'].value_counts().sort_index()
                st.bar_chart(freq_data)
                
            else:
                st.warning(f"업로드된 데이터 중 '{target_category}' 구간에 해당하는 과거 기록이 부족합니다.")
        
        st.markdown("---")
        with st.expander("원본 데이터 및 구간별 상세 내역 확인하기"):
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다. 파일의 열 이름이나 형식을 확인해주세요.\n상세 오류: {e}")