import sqlite3
import pandas as pd
import streamlit as st

DB = "database.db"

st.set_page_config(
    page_title="Energy Resource Planning Dashboard",
    page_icon="📊",
    layout="wide",
)

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB, check_same_thread=False)

@st.cache_data
def load_customer():
    return pd.read_sql_query("SELECT * FROM customer", get_connection())

@st.cache_data
def load_demand():
    return pd.read_sql_query("SELECT * FROM demand", get_connection())

customer = load_customer()
demand = load_demand()

# ---------- Sidebar ----------
st.sidebar.title("Filters")

year_min = int(min(customer["year"].min(), demand["year"].min()))
year_max = int(max(customer["year"].max(), demand["year"].max()))

year_range = st.sidebar.slider(
    "Planning horizon",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    step=1,
)

regions = sorted(customer["region"].dropna().unique())
sectors_customer = sorted(customer["sector"].dropna().unique())
sectors_demand = sorted(demand["sector"].dropna().unique())
trendlines = sorted(demand["trendline"].dropna().unique())

selected_regions = st.sidebar.multiselect(
    "Customer regions",
    regions,
    default=regions,
)

selected_customer_sectors = st.sidebar.multiselect(
    "Customer sectors",
    sectors_customer,
    default=sectors_customer,
)

selected_demand_sectors = st.sidebar.multiselect(
    "Demand sectors",
    sectors_demand,
    default=sectors_demand,
)

selected_trendlines = st.sidebar.multiselect(
    "Demand scenarios / trendlines",
    trendlines,
    default=trendlines,
)

# Apply filters.
c = customer[
    customer["year"].between(*year_range)
    & customer["region"].isin(selected_regions)
    & customer["sector"].isin(selected_customer_sectors)
].copy()

d = demand[
    demand["year"].between(*year_range)
    & demand["sector"].isin(selected_demand_sectors)
    & demand["trendline"].isin(selected_trendlines)
].copy()

# ---------- Tabs ----------
tab_kpi, tab_customer, tab_demand = st.tabs(
    ["KPI", "Customer", "Demand"]
)

# ---------- KPI TAB ----------
with tab_kpi:
    st.title("Energy Resource Planning Dashboard")
    st.caption(
        f"Interactive planning view: {year_range[0]}–{year_range[1]}"
    )

    total_customer = c["value"].sum()
    latest_year = year_range[1]

    latest_customer = c[c["year"] == latest_year]["value"].sum()

    if not d.empty:
        latest_demand = d[d["year"] == latest_year]["value"].sum()
    else:
        latest_demand = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customer records", f"{len(c):,}")
    col2.metric("Customer value", f"{total_customer:,.0f}")
    col3.metric(f"Customer value ({latest_year})", f"{latest_customer:,.0f}")
    col4.metric(f"Demand value ({latest_year})", f"{latest_demand:,.1f}")

    st.divider()

    st.subheader("Customer value by region")

    if c.empty:
        st.info("No customer data matches the selected filters.")
    else:
        region_summary = (
            c.groupby("region", as_index=False)["value"]
            .sum()
            .sort_values("value", ascending=False)
            .set_index("region")
        )
        st.bar_chart(region_summary)

    st.subheader("Demand scenarios")
    if d.empty:
        st.info("No demand data matches the selected filters.")
    else:
        scenario_summary = (
            d.groupby(["year", "trendline"], as_index=False)["value"]
            .sum()
            .pivot(index="year", columns="trendline", values="value")
        )
        st.line_chart(scenario_summary)

# ---------- CUSTOMER TAB ----------
with tab_customer:
    st.title("Customer")

    if c.empty:
        st.warning("No data matches the selected filters.")
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Customer value over time")

            chart = (
                c.groupby(["year", "sector"], as_index=False)["value"]
                .sum()
                .pivot(index="year", columns="sector", values="value")
            )
            st.line_chart(chart)

        with col2:
            st.subheader("Regional share")

            regional = (
                c.groupby("region", as_index=False)["value"]
                .sum()
                .sort_values("value", ascending=False)
            )
            st.dataframe(
                regional,
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Customer value by region and sector")

        pivot = pd.pivot_table(
            c,
            index="region",
            columns="sector",
            values="value",
            aggfunc="sum",
            fill_value=0,
        )

        st.dataframe(
            pivot.style.format("{:,.0f}"),
            use_container_width=True,
        )

        with st.expander("Show filtered records"):
            st.dataframe(
                c.sort_values(["year", "region", "sector"]),
                use_container_width=True,
                hide_index=True,
            )

# ---------- DEMAND TAB ----------
with tab_demand:
    st.title("Demand")

    if d.empty:
        st.warning("No data matches the selected filters.")
    else:
        # Scenario selector specifically for the main chart.
        chart_scenarios = st.multiselect(
            "Scenarios shown on chart",
            sorted(d["trendline"].unique()),
            default=sorted(d["trendline"].unique()),
            key="demand_chart_scenarios",
        )

        chart_d = d[d["trendline"].isin(chart_scenarios)]

        st.subheader("Demand trajectory")

        chart = (
            chart_d.groupby(["year", "trendline"], as_index=False)["value"]
            .sum()
            .pivot(index="year", columns="trendline", values="value")
        )
        st.line_chart(chart)

        st.subheader("Demand by sector")

        sector_chart = (
            chart_d.groupby(["year", "sector"], as_index=False)["value"]
            .sum()
            .pivot(index="year", columns="sector", values="value")
        )
        st.line_chart(sector_chart)

        st.subheader("Scenario comparison")

        comparison_year = st.slider(
            "Select year",
            min_value=year_range[0],
            max_value=year_range[1],
            value=year_range[1],
            key="comparison_year",
        )

        comparison = (
            d[d["year"] == comparison_year]
            .groupby(["trendline", "sector"], as_index=False)["value"]
            .sum()
        )

        st.dataframe(
            comparison.sort_values("value", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Show filtered demand records"):
            st.dataframe(
                d.sort_values(["year", "trendline", "sector"]),
                use_container_width=True,
                hide_index=True,
            )

st.sidebar.divider()
st.sidebar.caption("Data loaded from SQLite.")
