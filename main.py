# main.py

import json
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="전국 시군구 아이 비율 지도",
    layout="wide"
)

# --------------------------------------------------
# 스타일
# --------------------------------------------------
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
        #fff9dc 50%,
        #fff4b8 100%
    );
}

h1,h2,h3 {
    color:#7b5d00;
}

.baby{
    position:fixed;
    opacity:0.08;
    font-size:42px;
    z-index:0;
}

.b1{top:10%;left:2%;}
.b2{top:20%;right:4%;}
.b3{bottom:15%;left:4%;}
.b4{bottom:20%;right:8%;}
</style>

<div class="baby b1">👶</div>
<div class="baby b2">🍼</div>
<div class="baby b3">🧸</div>
<div class="baby b4">👶</div>
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
# GeoJSON
# --------------------------------------------------
@st.cache_data
def load_geojson():

    response = requests.get(GEO_URL, timeout=30)
    response.raise_for_status()

    geojson = response.json()

    return geojson


# --------------------------------------------------
# 아이 비율 계산
# --------------------------------------------------
@st.cache_data
def make_child_ratio(df):

    df["시군구코드"] = df["코드"].str[:5]

    total_cols = [
        c for c in df.columns
        if c.startswith("계_")
    ]

    child_cols = [
        f"계_{i}세"
        for i in range(15)
    ]

    sigungu = (
        df.groupby("시군구코드")[total_cols]
        .sum()
        .reset_index()
    )

    sigungu["전체인구"] = sigungu[total_cols].sum(axis=1)
    sigungu["아이인구"] = sigungu[child_cols].sum(axis=1)

    sigungu["아이비율"] = (
        sigungu["아이인구"]
        / sigungu["전체인구"]
        * 100
    )

    return sigungu


# --------------------------------------------------
# 시군구 이름 추출
# --------------------------------------------------
@st.cache_data
def make_region_info(geojson):

    rows = []

    for feature in geojson["features"]:

        prop = feature["properties"]

        rows.append({
            "코드": str(prop["코드"]).zfill(5),
            "시군구": prop["시군구"],
            "시도": prop["시도"]
        })

    return pd.DataFrame(rows)


# --------------------------------------------------
# 데이터 준비
# --------------------------------------------------
with st.spinner("데이터 불러오는 중..."):

    pop_df, latest_year = load_population()

    geojson = load_geojson()

    region_df = make_region_info(geojson)

    ratio_df = make_child_ratio(pop_df)

    data = region_df.merge(
        ratio_df,
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
    data_frame=data,
    geojson=geojson,
    locations="코드",
    featureidkey="properties.코드",
    color="구간",
    category_orders={"구간": labels},
    color_discrete_map=color_map,
    custom_data=[
        "시군구",
        "시도",
        "아이비율"
    ]
)

fig.update_traces(
    hovertemplate=
    "<b>%{customdata[0]}</b><br>" +
    "시도: %{customdata[1]}<br>" +
    "아이 비율: %{customdata[2]:.2f}%<extra></extra>"
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    height=850,
    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    ),
    legend_title_text="아이 비율 구간",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# --------------------------------------------------
# 순위 표
# --------------------------------------------------
rank_df = (
    data[
        [
            "시도",
            "시군구",
            "아이비율"
        ]
    ]
    .sort_values(
        "아이비율",
        ascending=False
    )
)

top10 = rank_df.head(10).copy()

bottom10 = (
    rank_df.tail(10)
    .sort_values("아이비율")
)

top10["아이 비율(%)"] = top10["아이비율"].round(2)
bottom10["아이 비율(%)"] = bottom10["아이비율"].round(2)

top10 = top10[
    ["시도", "시군구", "아이 비율(%)"]
]

bottom10 = bottom10[
    ["시도", "시군구", "아이 비율(%)"]
]

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("👶 아이 비율 높은 지역 TOP 10")
    st.dataframe(
        top10,
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("📉 아이 비율 낮은 지역 TOP 10")
    st.dataframe(
        bottom10,
        use_container_width=True,
        hide_index=True
    )

st.caption(
    "아이 비율 = 0~14세 인구 ÷ 전체 인구 × 100"
)
