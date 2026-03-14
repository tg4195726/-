import streamlit as st
import requests
import re
import numpy as np
import random

# ==========================================
# 1. 네이버 API 설정 (본인의 키를 입력하세요)
# ==========================================
NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

def clean_html(raw_html):
    """API 결과값의 HTML 태그 제거"""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_analyzed_data(query):
    """네이버 쇼핑 API 결과 분석: 평균가 도출 및 상품 리스트 반환"""
    url = f"https://openapi.naver.com/v1/search/shop.json?query={query}&display=50"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get('items', [])
            if not items: return None
            
            # 가격순 정렬 및 필터링 (상위 20% ~ 70% 구간)
            prices = sorted([int(item['lprice']) for item in items])
            start_idx = int(len(prices) * 0.2)
            end_idx = int(len(prices) * 0.7)
            filtered_prices = prices[start_idx:end_idx]
            
            if not filtered_prices: return None
            
            return {
                "avg_market_price": np.mean(filtered_prices),
                "all_items": items,
                "min_price": prices[0]
            }
        return None
    except:
        return None

# ==========================================
# 2. 웹사이트 UI 구성
# ==========================================
st.set_page_config(page_title="당신의 지갑을 지켜드립니다", page_icon="🛡️", layout="centered")

st.title("🛡️ 지갑 지킴이: 스마트 소비 판독기")
st.write("시장 데이터를 분석해 당신의 지름신을 물리쳐 드립니다.")

st.markdown("---")

# [STEP 1] 상품 정보 입력
st.header("1. 어떤 물건을 보고 계신가요? 🔍")
col1, col2 = st.columns(2)
with col1:
    item_name = st.text_input("상품 이름 입력", placeholder="예: 무선 이어폰")
with col2:
    user_price = st.number_input("현재 보고 있는 가격 (원)", min_value=0, step=1000)

# 데이터 분석 수행
analysis = None
if item_name:
    with st.spinner('실시간 시장 가격 분석 중...'):
        analysis = get_analyzed_data(item_name)

st.markdown("---")

# [STEP 2] 주관적 필요도 진단
st.header("2. 냉정하게 생각하기 🤔")
q1_need = st.select_slider("내 삶에 얼마나 필요한가요?", options=["없어도 됨", "있으면 좋음", "대체불가 필수템"], value="있으면 좋음")
q2_similar = st.radio("비슷한 기능을 하는 물건이 이미 있나요?", ("전혀 없음", "비슷한 게 있음", "똑같은 게 있음"))
q3_days = st.number_input("이 물건을 사려고 고민한 기간 (일)", min_value=0, step=1)

st.markdown("---")

# [STEP 3] 최종 결과 도출
if st.button("📊 나의 소비 합리성 판독하기"):
    if not item_name or not analysis:
        st.error("상품 이름을 입력하고 API 설정을 확인해주세요.")
    else:
        # 1. 점수 계산 로직
        # 가성비 점수 (평균가 대비 저렴할수록 가점)
        avg_p = analysis['avg_market_price']
        price_diff_ratio = (avg_p - user_price) / avg_p
        cost_score = np.clip(price_diff_ratio * 150, -30, 30) 
        
        # 필요도 점수
        need_score = {"없어도 됨": 0, "있으면 좋음": 15, "대체불가 필수템": 30}[q1_need]
        
        # 대체재 점수
        similar_score = {"전혀 없음": 20, "비슷한 게 있음": 0, "똑같은 게 있음": -30}[q2_similar]
        
        # 고민 점수
        duration_score = np.min([q3_days * 2, 20])
        
        total_score = cost_score + need_score + similar_score + duration_score

        # 2. 결과 리포트 출력
        st.subheader(f"최종 합리성 점수: {total_score:.1f}점 / 100점")
        
        # 3. 현타 유발 리포트 (치킨 환산)
        price_diff = user_price - avg_p
        if price_diff > 0:
            st.error(f"⚠️ 시장 평균보다 **{price_diff:,.0f}원**을 더 지불하려고 하시네요!")
            
            chicken = price_diff // 20000
            gukbap = price_diff // 10000
            
            reasons = [
                f"차라리 그 돈으로 **치킨 {chicken:.0f}마리**를 시켜 먹는 건 어떨까요? 🍗",
                f"든든한 **국밥 {gukbap:.0f}그릇**을 먹고도 남는 돈입니다. 🍲",
                f"이 돈을 저축하면 1년 뒤에 더 멋진 걸 살 수 있어요! 💰"
            ]
            st.markdown(f"### {random.choice(reasons)}")
        else:
            st.success(f"💎 오! 시장 평균보다 **{abs(price_diff):,.0f}원** 저렴하게 찾으셨어요!")
            st.markdown("### 절약한 돈으로 맛있는 걸 사 드셔도 되겠네요! 🥳")

        # 4. 판정 결과
        if total_score >= 70:
            st.success("✅ **[구매 승인]** 이 정도면 충분히 합리적인 소비입니다!")
            st.balloons()
        elif total_score >= 40:
            st.warning("⚠️ **[고민 권고]** 가성비나 필요도가 조금 부족해요. 3일만 더 참아보죠.")
        else:
            st.error("🛑 **[구매 반려]** 이건 명백한 충동구매입니다! 창을 닫으세요.")

        # 5. 대체 상품 추천
        st.markdown("---")
        st.subheader("💡 대신 이런 가성비 제품은 어때요?")
        # 나보다 저렴한 상품들 중 상위 3개 추출
        recs = [i for i in analysis['all_items'] if int(i['lprice']) < user_price][:3]
        
        if recs:
            cols = st.columns(3)
            for i, rec in enumerate(recs):
                with cols[i]:
                    st.image(rec['image'], use_container_width=True)
                    st.caption(f"**{clean_html(rec['title'])}**")
                    st.write(f"{int(rec['lprice']):,}원")
                    st.link_button("최저가 확인", rec['link'])
        else:
            st.write("현재 보신 상품보다 가성비가 좋은 제품을 찾지 못했습니다.")
