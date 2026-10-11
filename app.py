"""
BlinkIT Grocery Analytics Dashboard
Run with:  streamlit run app.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns
import streamlit as st

# ----------------------------------------------------------------------------
# Page config & styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="BlinkIT Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND_YELLOW = "#F8CB46"
BRAND_GREEN = "#0C831F"
PALETTE = [BRAND_GREEN, BRAND_YELLOW, "#2E9E4F", "#F5A623", "#5BB974", "#C9A227", "#8FD3A3", "#7A6A1E"]

st.markdown(
    f"""
    <style>
        .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }}
        #MainMenu, footer {{ visibility: hidden; }}

        .hero {{
            background: linear-gradient(120deg, {BRAND_GREEN} 0%, #1fa23a 100%);
            padding: 1.6rem 2rem; border-radius: 16px; color: white; margin-bottom: 1.2rem;
        }}
        .hero h1 {{ margin: 0; font-size: 2rem; color: white; }}
        .hero p  {{ margin: .3rem 0 0 0; opacity: .9; }}
        .hero .pill {{
            display:inline-block; background:{BRAND_YELLOW}; color:#222; font-weight:700;
            padding:2px 12px; border-radius:999px; font-size:.75rem; margin-bottom:.5rem;
        }}

        div[data-testid="stMetric"] {{
            background: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,.18);
            border-left: 5px solid {BRAND_GREEN};
            padding: 14px 18px; border-radius: 12px;
        }}
        div[data-testid="stMetricValue"] {{ font-size: 1.7rem; font-weight: 700; }}
        div[data-testid="stMetricLabel"] p {{ font-size: .85rem; opacity: .75; }}

        .insight {{
            background: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 12px; padding: 14px 18px; height: 100%;
        }}
        .insight .k {{ font-size: .78rem; opacity: .7; text-transform: uppercase; letter-spacing: .04em; }}
        .insight .v {{ font-size: 1.2rem; font-weight: 700; color: {BRAND_GREEN}; margin-top: 2px; }}

        button[data-baseweb="tab"] {{ font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Data loading & cleaning (same steps as the notebook)
# ----------------------------------------------------------------------------
DEFAULT_FILES = ["BlinkIT-Grocery-Data_Raw.csv", "BlinkIT_Grocery_Cleaned.csv"]


@st.cache_data(show_spinner="Loading data…")
def load_data(source) -> pd.DataFrame:
    df = pd.read_csv(source)
    df = df.drop_duplicates()

    # Fill missing item weights with the mean
    if "Item Weight" in df.columns:
        df["Item Weight"] = df["Item Weight"].fillna(df["Item Weight"].mean())

    # Standardise fat-content labels
    df["Item Fat Content"] = (
        df["Item Fat Content"]
        .replace({"LF": "Low Fat", "low fat": "Low Fat", "reg": "Regular"})
    )
    return df


def find_default_file():
    here = Path(__file__).parent
    for name in DEFAULT_FILES:
        if (here / name).exists():
            return here / name
    return None


with st.sidebar:
    st.markdown("## 🛒 BlinkIT Analytics")
    uploaded = st.file_uploader("Upload dataset (CSV)", type="csv", help="Raw or cleaned BlinkIT grocery CSV")

source = uploaded or find_default_file()
if source is None:
    st.markdown(
        '<div class="hero"><span class="pill">BLINKIT</span><h1>Grocery Sales Dashboard</h1>'
        "<p>Upload the dataset to get started.</p></div>",
        unsafe_allow_html=True,
    )
    st.info(
        "Upload **BlinkIT-Grocery-Data_Raw.csv** in the sidebar, or place it in the same "
        "folder as `app.py`."
    )
    st.stop()

df = load_data(source)

required = {"Item Type", "Item Fat Content", "Outlet Type", "Outlet Location Type",
            "Outlet Size", "Outlet Identifier", "Outlet Establishment Year",
            "Item Visibility", "Sales", "Rating"}
missing = required - set(df.columns)
if missing:
    st.error(f"The uploaded file is missing columns: {', '.join(sorted(missing))}")
    st.stop()

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Filters")

    def multi(label, col):
        opts = sorted(df[col].dropna().unique())
        return st.multiselect(label, opts, default=opts)

    sel_types = multi("Item Type", "Item Type")
    sel_fat = multi("Fat Content", "Item Fat Content")
    sel_outlet = multi("Outlet Type", "Outlet Type")
    sel_tier = multi("Location Tier", "Outlet Location Type")
    sel_size = multi("Outlet Size", "Outlet Size")

    ymin, ymax = int(df["Outlet Establishment Year"].min()), int(df["Outlet Establishment Year"].max())
    sel_years = st.slider("Establishment Year", ymin, ymax, (ymin, ymax))

    st.divider()
    st.caption(f"Dataset: {len(df):,} rows · {df.shape[1]} columns")

mask = (
    df["Item Type"].isin(sel_types)
    & df["Item Fat Content"].isin(sel_fat)
    & df["Outlet Type"].isin(sel_outlet)
    & df["Outlet Location Type"].isin(sel_tier)
    & df["Outlet Size"].isin(sel_size)
    & df["Outlet Establishment Year"].between(*sel_years)
)
f = df[mask]

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <span class="pill">BLINKIT</span>
        <h1>Grocery Sales Dashboard</h1>
        <p>Explore sales, products, outlets and customer ratings across the BlinkIT network.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if f.empty:
    st.warning("No data matches the current filters. Adjust the filters in the sidebar.")
    st.stop()


sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def compact(x, _=None):
    for div, suf in [(1e6, "M"), (1e3, "K")]:
        if abs(x) >= div:
            return f"{x / div:.1f}{suf}"
    return f"{x:.0f}"


def show(fig):
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def bar(series, title, size=(6, 3.6), horizontal=False, colors=None, rotate=0):
    fig, ax = plt.subplots(figsize=size)
    colors = colors or PALETTE[: len(series)]
    if horizontal:
        bars = ax.barh(series.index.astype(str), series.values, color=BRAND_GREEN)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(compact))
        ax.grid(axis="y", visible=False)
    else:
        bars = ax.bar(series.index.astype(str), series.values, color=colors)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(compact))
        ax.grid(axis="x", visible=False)
        plt.setp(ax.get_xticklabels(), rotation=rotate, ha="right" if rotate else "center")
    ax.bar_label(bars, labels=[compact(v) for v in series.values], padding=3, fontsize=8)
    ax.set_title(title)
    ax.set_xlabel("")
    ax.set_ylabel("")
    return fig


# ----------------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sales", f"₹{f['Sales'].sum():,.0f}")
k2.metric("Avg Sales / Item", f"₹{f['Sales'].mean():,.2f}")
k3.metric("Avg Rating", f"{f['Rating'].mean():.2f} ⭐")
k4.metric("Total Items", f"{len(f):,}")
k5.metric("Outlets", f"{f['Outlet Identifier'].nunique()}")

st.write("")

# ----------------------------------------------------------------------------
# Key insights (auto-generated; replaces the blanks in the notebook)
# ----------------------------------------------------------------------------
top_item = f.groupby("Item Type")["Sales"].sum().idxmax()
top_fat = f.groupby("Item Fat Content")["Sales"].sum().idxmax()
top_outlet = f.groupby("Outlet Type")["Sales"].sum().idxmax()
top_tier = f.groupby("Outlet Location Type")["Sales"].sum().idxmax()

c1, c2, c3, c4 = st.columns(4)
for col, k, v in [
    (c1, "Top item type", top_item),
    (c2, "Most popular fat content", top_fat),
    (c3, "Best outlet type", top_outlet),
    (c4, "Best location tier", top_tier),
]:
    col.markdown(f'<div class="insight"><div class="k">{k}</div><div class="v">{v}</div></div>',
                 unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------------
tab_over, tab_prod, tab_out, tab_rate, tab_data = st.tabs(
    ["📊 Overview", "🥦 Products", "🏬 Outlets", "⭐ Ratings & Visibility", "🗂 Data"]
)

# ---- Overview ---------------------------------------------------------------
with tab_over:
    a, b = st.columns(2)

    fat = f.groupby("Item Fat Content")["Sales"].sum()
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.pie(fat.values, labels=fat.index, autopct="%1.1f%%", startangle=90,
           colors=[BRAND_GREEN, BRAND_YELLOW], wedgeprops=dict(width=0.45, edgecolor="white"))
    ax.set_title("Sales by Fat Content")
    with a:
        show(fig)

    yr = f.groupby("Outlet Establishment Year")["Sales"].sum()
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.plot(yr.index, yr.values, marker="o", color=BRAND_GREEN, linewidth=2.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(compact))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.set_title("Sales by Outlet Establishment Year")
    with b:
        show(fig)

    a, b, c = st.columns(3)
    for col, field, title in [
        (a, "Outlet Type", "Sales by Outlet Type"),
        (b, "Outlet Location Type", "Sales by Location Tier"),
        (c, "Outlet Size", "Sales by Outlet Size"),
    ]:
        g = f.groupby(field)["Sales"].sum().sort_values(ascending=False)
        with col:
            show(bar(g, title, size=(4.5, 3.6), rotate=20))

# ---- Products ---------------------------------------------------------------
with tab_prod:
    metric = st.radio("Metric", ["Total Sales", "Average Sales"], horizontal=True)
    agg = "sum" if metric == "Total Sales" else "mean"
    g = f.groupby("Item Type")["Sales"].agg(agg).sort_values(ascending=True)
    show(bar(g, f"{metric} by Item Type", size=(10, 5.5), horizontal=True))

    a, b = st.columns(2)
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.boxplot(data=f, x="Item Fat Content", y="Sales", hue="Item Fat Content",
                palette=[BRAND_GREEN, BRAND_YELLOW], legend=False, ax=ax)
    ax.set_title("Sales Distribution by Fat Content")
    ax.set_xlabel("")
    with a:
        show(fig)

    top_items = (f.groupby(["Item Identifier", "Item Type"], as_index=False)["Sales"].sum()
                 .sort_values("Sales", ascending=False).head(10))
    b.markdown("**Top 10 items by sales**")
    b.dataframe(top_items, hide_index=True, width="stretch",
                column_config={"Sales": st.column_config.NumberColumn(format="₹%.0f")})

# ---- Outlets ----------------------------------------------------------------
with tab_out:
    out = (f.groupby(["Outlet Identifier", "Outlet Type", "Outlet Location Type", "Outlet Size"], as_index=False)
           .agg(Sales=("Sales", "sum"), AvgRating=("Rating", "mean"), Items=("Sales", "size"))
           .sort_values("Sales", ascending=False))

    a, b = st.columns([3, 2])
    top5 = out.head(5).set_index("Outlet Identifier")["Sales"]
    with a:
        show(bar(top5, "Top 5 Outlets by Sales", size=(7, 4)))

    b.markdown("**Outlet leaderboard**")
    b.dataframe(
        out.rename(columns={"AvgRating": "Avg Rating"}),
        hide_index=True, width="stretch", height=380,
        column_config={
            "Sales": st.column_config.ProgressColumn(
                format="₹%.0f", min_value=0, max_value=float(out["Sales"].max())),
            "Avg Rating": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    heat = f.pivot_table(index="Outlet Location Type", columns="Outlet Type", values="Sales", aggfunc="sum")
    fig, ax = plt.subplots(figsize=(10, 3.2))
    sns.heatmap(heat, annot=True, fmt=",.0f", cmap="Greens", cbar=False, ax=ax)
    ax.set_title("Sales: Location Tier × Outlet Type")
    ax.set_xlabel("")
    ax.set_ylabel("")
    show(fig)

# ---- Ratings & visibility ---------------------------------------------------
with tab_rate:
    a, b = st.columns(2)
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(f["Rating"], bins=10, kde=True, color=BRAND_GREEN, ax=ax)
    ax.set_title("Distribution of Ratings")
    with a:
        show(fig)

    sample = f.sample(min(len(f), 3000), random_state=1)
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.scatterplot(data=sample, x="Item Visibility", y="Sales", hue="Item Fat Content",
                    palette=[BRAND_GREEN, BRAND_YELLOW], alpha=0.55, ax=ax)
    ax.set_title("Item Visibility vs Sales")
    with b:
        show(fig)

    num_cols = [c for c in ["Item Visibility", "Item Weight", "Sales", "Rating"] if c in f.columns]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    sns.heatmap(f[num_cols].corr(), annot=True, fmt=".2f", vmin=-1, vmax=1, cmap="RdYlGn", ax=ax)
    ax.set_title("Correlation Heatmap")
    show(fig)
    st.caption("Values near 1 or −1 indicate a strong relationship; values near 0 indicate little relationship.")

# ---- Data -------------------------------------------------------------------
with tab_data:
    a, b = st.columns([3, 1])
    a.markdown(f"**{len(f):,} rows** match the current filters")
    b.download_button("⬇ Download filtered CSV", f.to_csv(index=False).encode("utf-8"),
                      file_name="BlinkIT_Grocery_Filtered.csv", mime="text/csv", width="stretch")
    st.dataframe(f, hide_index=True, width="stretch", height=450)

    with st.expander("Data quality summary"):
        q1, q2 = st.columns(2)
        q1.markdown("**Missing values (after cleaning)**")
        q1.dataframe(df.isnull().sum().rename("Missing"), width="stretch")
        q2.markdown("**Numeric summary**")
        q2.dataframe(df.describe().T, width="stretch")