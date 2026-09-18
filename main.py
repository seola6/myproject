import base64
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="대한민국 아이 비율 지도",
    layout="wide"
)

# --------------------------------------------------
# 배경 이미지 읽기
# --------------------------------------------------
def get_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg = get_base64("background.png")

# --------------------------------------------------
# 스타일
# --------------------------------------------------
st.markdown(
    f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');

html, body, [class*="css"] {{
    font-family: 'Jua', sans-serif;
}}

.stApp {{
    background-image: url("data:image/png;base64,{bg}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.main {{
    background-color: rgba(255,255,255,0.72);
    border-radius: 30px;
}}

h1 {{
    text-align:center;
    color:#c97b00;
    font-size:3rem;
}}

h2,h3 {{
    color:#a86700;
}}

[data-testid="stDataFrame"] {{
    background-color: rgba(255,255,255,0.85);
    border-radius:20px;
}}

div[data-testid="stPlotlyChart"] {{
    background-color: rgba(255,255,255,0.65);
    border-radius:20px;
    padding:10px;
}}

</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 제목
# --------------------------------------------------
st.title("👶 대한민국 아이 비율 지도 🧸")
st.caption("시군구별 0~14세 인구 비율")

# --------------------------------------------------
# 데이터 주소
# --------------------------------------------------
POP_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
)

GEO_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
)

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

    r = requests.get(GEO_URL)
    r.raise_for_status()

    return r.json()

# --------------------------------------------------
# 지역 정보
# --------------------------------------------------
@st.cache_data
def region_info(geojson):

    rows = []

    for feature in geojson["features"]:

        p = feature["properties"]

        rows.append(
            {
                "코드": str(p["코드"]).zfill(5),
                "시도": p["시도"],
                "시군구": p["시군구"],
            }
        )

    return pd.DataFrame(rows)

# --------------------------------------------------
# 아이 비율 계산
# --------------------------------------------------
@st.cache_data
def child_ratio(df):

    df["시군구코드"] = df["코드"].str[:5]

    total_cols = [
        c
        for c in df.columns
        if c.startswith("계_")
    ]

    child_cols = [
        f"계_{i}세"
        for i in range(15)
    ]

    agg = (
        df.groupby("시군구코드")[total_cols]
        .sum()
        .reset_index()
    )

    agg["전체인구"] = agg[total_cols].sum(axis=1)
    agg["아이인구"] = agg[child_cols].sum(axis=1)

    agg["아이비율"] = (
        agg["아이인구"]
        / agg["전체인구"]
        * 100
    )

    return agg[
        ["시군구코드", "아이비율"]
    ]

# --------------------------------------------------
# 데이터 준비
# --------------------------------------------------
with st.spinner("아이들을 찾는 중... 👶"):

    pop_df, latest_year = load_population()

    geojson = load_geojson()

    region_df = region_info(geojson)

    ratio_df = child_ratio(pop_df)

    data = region_df.merge(
        ratio_df,
        left_on="코드",
        right_on="시군구코드",
        how="left",
    )

# --------------------------------------------------
# 구간
# --------------------------------------------------
bins = [-999, 19, 23, 28, 38, 999]

labels = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상",
]

data["구간"] = pd.cut(
    data["아이비율"],
    bins=bins,
    labels=labels,
    include_lowest=True,
)

color_map = {
    "19% 미만": "#fff7bc",
    "19~23%": "#fee391",
    "23~28%": "#fec44f",
    "28~38%": "#fe9929",
    "38% 이상": "#d95f0e",
}

# --------------------------------------------------
# 지도
# --------------------------------------------------
st.subheader(f"📅 {latest_year}년 기준")

fig = px.choropleth(
    data,
    geojson=geojson,
    locations="코드",
    featureidkey="properties.코드",
    color="구간",
    category_orders={"구간": labels},
    color_discrete_map=color_map,
    custom_data=[
        "시군구",
        "시도",
        "아이비율",
    ],
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
    visible=False,
)

fig.update_layout(
    height=850,
    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0,
    ),
    legend_title_text="아이 비율",
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

# --------------------------------------------------
# TOP 10
# --------------------------------------------------
rank_df = (
    data[
        ["시도", "시군구", "아이비율"]
    ]
    .sort_values(
        "아이비율",
        ascending=False,
    )
)

top10 = rank_df.head(10).copy()

bottom10 = (
    rank_df.tail(10)
    .sort_values("아이비율")
)

top10["아이 비율(%)"] = top10["아이비율"].round(2)
bottom10["아이 비율(%)"] = bottom10["아이비율"].round(2)

col1, col2 = st.columns(2)

with col1:
    st.subheader("👑 아이 비율 높은 지역 TOP 10")
    st.dataframe(
        top10[
            ["시도", "시군구", "아이 비율(%)"]
        ],
        hide_index=True,
        use_container_width=True,
    )

with col2:
    st.subheader("📉 아이 비율 낮은 지역 TOP 10")
    st.dataframe(
        bottom10[
            ["시도", "시군구", "아이 비율(%)"]
        ],
        hide_index=True,
        use_container_width=True,
    )

st.caption(
    "아이 비율 = 0~14세 인구 ÷ 전체 인구 × 100"
)
