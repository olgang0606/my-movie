import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import plotly.express as px

st.title("📊 어제의 박스오피스 분석 대시보드 (Plotly 확장판)")

# 한국 시간 기준으로 '어제'와 '그제' 날짜 계산
seoul_tz = ZoneInfo("Asia/Seoul")
today_seoul = datetime.now(seoul_tz).date()
yesterday_seoul = today_seoul - timedelta(days=1)
day_before_seoul = today_seoul - timedelta(days=2)

targetDt_yesterday = yesterday_seoul.strftime("%Y%m%d")
targetDt_daybefore = day_before_seoul.strftime("%Y%m%d")

url = "http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
api_key = st.secrets["KOBIS_KEY"]

def fetch_data(targetDt):
    params = {"key": api_key, "targetDt": targetDt}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    if "faultInfo" in data:
        return None
    return pd.DataFrame(data["boxOfficeResult"]["dailyBoxOfficeList"])

df_yesterday = fetch_data(targetDt_yesterday)
df_daybefore = fetch_data(targetDt_daybefore)

if df_yesterday is None or df_daybefore is None:
    st.error("❌ 박스오피스 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
else:
    num_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
    for df in [df_yesterday, df_daybefore]:
        for col in num_cols:
            df[col] = df[col].astype(int)

    df_yesterday = df_yesterday[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]]
    df_daybefore = df_daybefore[["movieNm", "audiCnt"]]

    merged = pd.merge(df_yesterday, df_daybefore[["movieNm", "audiCnt"]],
                      on="movieNm", how="left", suffixes=("", "_prev"))
    merged["audiDiff"] = merged["audiCnt"] - merged["audiCnt_prev"]
    merged["audiRate"] = (merged["audiDiff"] / merged["audiCnt_prev"]) * 100

    st.subheader("🎥 박스오피스 순위표 (증감률 포함)")
    st.dataframe(
        merged[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt", "audiDiff", "audiRate"]],
        use_container_width=True
    )

    st.subheader("👥 관객수 TOP 5")
    top5 = merged.sort_values("audiCnt", ascending=False).head(5)
    fig_top5 = px.bar(top5, x="movieNm", y="audiCnt", text="audiCnt", color="movieNm",
                      title="어제 관객수 상위 5편")
    fig_top5.update_traces(texttemplate="%{text:,}명", textposition="outside")
    st.plotly_chart(fig_top5, use_container_width=True)

    st.subheader("🏆 어제의 1위 영화")
    first_movie = merged[merged["rank"] == 1].iloc[0]
    st.metric(
        label=f"{first_movie['movieNm']} (개봉일: {first_movie['openDt']})",
        value=f"{first_movie['audiCnt']:,} 명",
        delta=f"{first_movie['audiDiff']:+,} 명 ({first_movie['audiRate']:+.1f}%)"
    )

    st.subheader("📈 누적 관객수 TOP 5")
    top5_acc = merged.sort_values("audiAcc", ascending=False).head(5)
    fig_acc = px.bar(top5_acc, x="movieNm", y="audiAcc", text="audiAcc", color="movieNm",
                     title="누적 관객수 상위 5편")
    fig_acc.update_traces(texttemplate="%{text:,}명", textposition="outside")
    st.plotly_chart(fig_acc, use_container_width=True)

    merged["audi_per_scrn"] = merged["audiCnt"] / merged["scrnCnt"]
    st.subheader("🎬 스크린당 평균 관객수")
    fig_scrn = px.scatter(merged, x="scrnCnt", y="audi_per_scrn", size="audiCnt", color="movieNm",
                          hover_name="movieNm", title="스크린 수 vs 스크린당 평균 관객수")
    st.plotly_chart(fig_scrn, use_container_width=True)

    merged["audi_per_show"] = merged["audiCnt"] / merged["showCnt"]
    st.subheader("🎞️ 회차당 평균 관객수")
    st.dataframe(merged[["rank", "movieNm", "audi_per_show"]].sort_values("audi_per_show", ascending=False))

