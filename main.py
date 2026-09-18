import json
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px

# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="전국 시군구 아이 비율 지도",
    layout="wide"
)

# 노란 분위기 + 고급스러운 느낌
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Serif KR', serif;
}

.stApp {
    background: linear-gradient(
        180deg,
        #fffdf2 0%,
        #fff8d6 50%,
        #fff3b0 100%
    );
}

h1, h2, h3 {
    color: #7a5c00;
}

.block-container {
    padding-top: 2rem;
}

.baby {
    position: fixed;
    font-size: 32px;
    opacity: 0.12;
    z-index: 0;
}

.b1 { top: 8%; left: 3%; }
.b2 { top: 20%; right: 5%; }
.b3 { bottom: 15%; left: 8%; }
.b4 { bottom: 25%; right: 10%; }
</style>

<div class="baby b1">👶</div>
<div class="baby b2">🍼</div>
<div class="baby b3">👶</div>
<div class="baby b4">🧸</div>
""", unsafe_allow_html=True)

st.title("👶 전국 시군구 아이 비율 지도")
st.caption("0~14세 인구 비율 기준")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


# --------------------------------------------------
# 인구 데이터
# --------------------------------------------------
@st.cache_data
def load_population():
    df = pd.read_csv(
        POP_URL,
        compression="gzip",
        dtype={"코드": str}
    )

    latest_year = df["연도"].max()
    df = df[df["연도"] == latest_year].copy()

    return df, latest_year


# --------------------------------------------------
# 지도 경계
# --------------------------------------------------
@st.cache_data
def load_geo():
    gdf = gpd.read_file(GEO_URL)
    gdf["코드"] = gdf["코드"].astype(str).str.zfill(5)
    return gdf


# --------------------------------------------------
# 시군구별 아이 비율 계산
# --------------------------------------------------
@st.cache_data
def make_child_ratio(df):
    # 시군구 코드
    df["시군구코드"] = df["코드"].str[:5]

    # 전체 인구 열
    total_cols = [
        c for c in df.columns
        if c.startswith("계_")
    ]

    # 0~14세 인구 열
    child_cols = [f"계_{i}세" for i in range(15)]

    agg = (
        df.groupby("시군구코드")[total_cols]
        .sum()
        .reset_index()
    )

    agg["전체인구"] = agg[total_cols].sum(axis=1)
    agg["아이인구"] = agg[child_cols].sum(axis=1)

    agg["아이비율"] = (
        agg["아이인구"] /
        agg["전체인구"] * 100
    )

    return agg[["시군구코드", "아이비율"]]


# --------------------------------------------------
# 데이터 준비
# --------------------------------------------------
with st.spinner("데이터 불러오는 중..."):
    pop_df, latest_year = load_population()
    geo = load_geo()
    ratio = make_child_ratio(pop_df)

data = geo.merge(
    ratio,
    left_on="코드",
    right_on="시군구코드",
    how="left"
)

# --------------------------------------------------
# 단계 구분
# --------------------------------------------------
bins = [-999, 19, 23, 28, 38, 999]
labels = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상"
]

data["구간"] = pd.cut(
    data["아이비율"],
    bins=bins,
    labels=labels,
    include_lowest=True
)

# 옅은 노랑 → 진한 주황
color_map = {
    "19% 미만": "#fff7bc",
    "19~23%": "#fee391",
    "23~28%": "#fec44f",
    "28~38%": "#fe9929",
    "38% 이상": "#d95f0e"
}

# --------------------------------------------------
# 지도
# --------------------------------------------------
st.subheader(f"{latest_year}년 기준")

fig = px.choropleth(
    data,
    geojson=json.loads(data.to_json()),
    locations="코드",
    featureidkey="properties.코드",
    color="구간",
    color_discrete_map=color_map,
    category_orders={"구간": labels},
    custom_data=[
        "시군구",
        "시도",
        "아이비율"
    ]
)

fig.update_traces(
    hovertemplate=
    "<b>%{customdata[0]}</b><br>"
    "시도: %{customdata[1]}<br>"
    "아이 비율: %{customdata[2]:.2f}%"
    "<extra></extra>"
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    height=800,
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend_title_text="아이 비율 구간"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# --------------------------------------------------
# 상위 / 하위 10개
# --------------------------------------------------
rank_df = (
    data[["시도", "시군구", "아이비율"]]
    .sort_values("아이비율", ascending=False)
    .reset_index(drop=True)
)

top10 = rank_df.head(10).copy()
bottom10 = rank_df.tail(10).sort_values(
    "아이비율",
    ascending=True
)

top10["아이 비율(%)"] = top10["아이비율"].round(2)
bottom10["아이 비율(%)"] = bottom10["아이비율"].round(2)

top10 = top10[["시도", "시군구", "아이 비율(%)"]]
bottom10 = bottom10[["시도", "시군구", "아이 비율(%)"]]

col1, col2 = st.columns(2)

with col1:
    st.subheader("👶 아이 비율 높은 지역 TOP 10")
    st.dataframe(
        top10,
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("👴 아이 비율 낮은 지역 TOP 10")
    st.dataframe(
        bottom10,
        use_container_width=True,
        hide_index=True
    )

st.caption(
    "아이 비율 = 0~14세 인구 ÷ 전체 인구 × 100"
)
