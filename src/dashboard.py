import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Network AIOps | Operations Center",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API = "http://api:8000"

# =========================================================
# DARK THEME
# =========================================================
st.markdown(
    """
    <style>
    /* Main application */
    .stApp {
        background: linear-gradient(135deg, #07111f 0%, #101b30 100%);
        color: #e5edf8;
    }

    /* Dark Streamlit header */
    [data-testid="stHeader"],
    [data-testid="stToolbar"] {
        background: #07111f !important;
        color: #e5edf8 !important;
    }

    [data-testid="stHeader"] button,
    [data-testid="stToolbar"] button {
        color: #e5edf8 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0b1424 !important;
        border-right: 1px solid #263c59;
    }

    [data-testid="stSidebar"] * {
        color: #e5edf8;
    }

    /* Sidebar selectbox */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #14233a !important;
        border-color: #354a66 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] [data-baseweb="popover"] * {
        color: #f0f6ff !important;
    }

    /* Sidebar labels and checkbox */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label {
        color: #e5edf8 !important;
    }

    [data-testid="stSidebar"] [data-testid="stCheckbox"] {
        color: #e5edf8 !important;
    }

    /* Backend URL code box: dark background and readable URL */
    [data-testid="stSidebar"] [data-testid="stCode"] {
        background-color: #14233a !important;
        border: 1px solid #354d6c !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    [data-testid="stSidebar"] [data-testid="stCode"] pre,
    [data-testid="stSidebar"] [data-testid="stCode"] code,
    [data-testid="stSidebar"] [data-testid="stCode"] span {
        background-color: transparent !important;
        color: #f0f6ff !important;
        -webkit-text-fill-color: #f0f6ff !important;
        opacity: 1 !important;
    }

    /* General headings and text */
    h1, h2, h3, h4, p, label {
        color: #e5edf8;
    }

    .main-title {
        font-size: 32px;
        font-weight: 750;
        color: #f0f6ff;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #a9bdd7;
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* KPI cards */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #14233a, #101b2d);
        border: 1px solid #2a4261;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #b2c5de !important;
    }

    [data-testid="stMetricValue"] {
        color: #f0f6ff !important;
    }

    /* Connection status */
    .status-connected {
        display: inline-block;
        background: #123b32;
        color: #66e3b0;
        padding: 7px 13px;
        border-radius: 20px;
        font-weight: 600;
        margin: 8px 0 18px 0;
    }

    .status-disconnected {
        display: inline-block;
        background: #4a2027;
        color: #ff9ba5;
        padding: 7px 13px;
        border-radius: 20px;
        font-weight: 600;
        margin: 8px 0 18px 0;
    }

    /* Tabs */
    [data-testid="stTabs"] button {
        color: #c7d6ea !important;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #67c9ff !important;
    }

    /* Tables and alerts */
    [data-testid="stDataFrame"] {
        border: 1px solid #263c59;
        border-radius: 8px;
    }

    [data-testid="stAlert"] {
        background-color: #14233a;
        color: #e5edf8;
        border: 1px solid #263c59;
    }

    /* Buttons: readable without hovering */
    [data-testid="stSidebar"] [data-testid="stButton"] button,
    [data-testid="stDownloadButton"] button {
        background-color: #18304d !important;
        color: #f0f6ff !important;
        border: 1px solid #3b587a !important;
        border-radius: 8px;
        opacity: 1 !important;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button p,
    [data-testid="stSidebar"] [data-testid="stButton"] button span {
        color: #f0f6ff !important;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover {
        background-color: #254768 !important;
        color: #ffffff !important;
        border-color: #67c9ff !important;
    }

    hr {
        border-color: #26364e;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# API HELPERS
# =========================================================
def get_api_data(endpoint, params=None):
    """Fetch data from the FastAPI backend."""
    try:
        response = requests.get(
            f"{DEFAULT_API}{endpoint}",
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)


def records_to_dataframe(data, possible_keys):
    """Convert list or wrapped API responses into a DataFrame."""
    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        for key in possible_keys:
            value = data.get(key)
            if isinstance(value, list):
                return pd.DataFrame(value)

    return pd.DataFrame()


def normalize_boolean(series):
    """Convert common API boolean representations to True/False."""
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## 📡 Network AIOps")
    st.caption("Intelligent Network Operations")
    st.divider()

    st.markdown("### Dashboard Settings")

    record_limit = st.selectbox(
        "Telemetry records",
        options=[10, 25, 50, 100, 500, 1000],
        index=1,
    )

    anomaly_only = st.checkbox(
        "Show anomalies only",
        value=False,
    )

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

    st.divider()
    st.markdown("### Backend")
    st.code(DEFAULT_API, language=None)
    st.caption("Use Refresh Now to retrieve the latest data.")


# =========================================================
# HEADER
# =========================================================
st.markdown(
    '<div class="main-title">Network Operations Center</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Real-time telemetry, machine learning anomaly detection, "
    "and incident monitoring"
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# API HEALTH
# =========================================================
health, health_error = get_api_data("/health")

if health is None:
    st.markdown(
        '<span class="status-disconnected">● API Disconnected</span>',
        unsafe_allow_html=True,
    )
    st.error(
        "Cannot connect to FastAPI.\n\n"
        "Start the API in a separate terminal:\n\n"
        "`python -m uvicorn src.api:app "
        "--host 127.0.0.1 --port 8000`\n\n"
        f"Details: {health_error}"
    )
    st.stop()

st.markdown(
    '<span class="status-connected">● API Connected</span>',
    unsafe_allow_html=True,
)

if health.get("database_exists") is False:
    st.warning("The API reports that the database file does not exist.")


# =========================================================
# FETCH TELEMETRY AND INCIDENTS
# =========================================================
telemetry_params = {"limit": record_limit}
if anomaly_only:
    telemetry_params["anomaly_only"] = True

telemetry_data, telemetry_error = get_api_data(
    "/telemetry",
    params=telemetry_params,
)
incidents_data, incidents_error = get_api_data("/incidents")

if telemetry_error:
    st.error(f"Telemetry API error: {telemetry_error}")
if incidents_error:
    st.error(f"Incidents API error: {incidents_error}")

# Telemetry API returns {"count": ..., "events": [...]}
telemetry_df = records_to_dataframe(
    telemetry_data,
    ["events", "telemetry", "data", "results"],
)

incidents_df = records_to_dataframe(
    incidents_data,
    ["incidents", "data", "results", "events"],
)


# =========================================================
# NORMALIZE DATA
# =========================================================
if not telemetry_df.empty:
    if "timestamp" in telemetry_df.columns:
        telemetry_df["timestamp"] = pd.to_datetime(
            telemetry_df["timestamp"],
            errors="coerce",
            utc=True,
        )

    numeric_columns = [
        "latency_ms",
        "packet_loss_pct",
        "bandwidth_mbps",
        "interface_errors",
        "ml_score",
    ]

    for column in numeric_columns:
        if column in telemetry_df.columns:
            telemetry_df[column] = pd.to_numeric(
                telemetry_df[column],
                errors="coerce",
            )

    if "ml_prediction" in telemetry_df.columns:
        telemetry_df["ml_prediction"] = (
            telemetry_df["ml_prediction"]
            .fillna("UNKNOWN")
            .astype(str)
        )

    if "rule_alert" in telemetry_df.columns:
        telemetry_df["rule_alert"] = normalize_boolean(
            telemetry_df["rule_alert"]
        )

if not incidents_df.empty and "status" in incidents_df.columns:
    incidents_df["status"] = (
        incidents_df["status"].fillna("UNKNOWN").astype(str)
    )


# =========================================================
# KPI METRICS
# =========================================================
total_records = len(telemetry_df)

if (
    not telemetry_df.empty
    and "ml_prediction" in telemetry_df.columns
):
    ml_anomalies = int(
        telemetry_df["ml_prediction"].str.upper().eq("ANOMALY").sum()
    )
else:
    ml_anomalies = 0

if (
    not telemetry_df.empty
    and "rule_alert" in telemetry_df.columns
):
    rule_alerts = int(telemetry_df["rule_alert"].sum())
else:
    rule_alerts = 0

if (
    not incidents_df.empty
    and "status" in incidents_df.columns
):
    open_incidents = int(
        incidents_df["status"].str.upper().isin(["OPEN", "ACTIVE"]).sum()
    )
else:
    open_incidents = 0


# =========================================================
# KPI CARDS
# =========================================================
st.markdown("### Operations Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Telemetry Records", total_records)
with col2:
    st.metric("ML Anomalies", ml_anomalies)
with col3:
    st.metric("Rule Alerts", rule_alerts)
with col4:
    st.metric("Open Incidents", open_incidents)

st.divider()


# =========================================================
# DASHBOARD TABS
# =========================================================
overview_tab, telemetry_tab, incidents_tab = st.tabs(
    ["📊 Overview", "📡 Telemetry", "🚨 Incidents"]
)


# =========================================================
# OVERVIEW TAB
# =========================================================
with overview_tab:
    chart_col1, chart_col2 = st.columns([1.7, 1])

    with chart_col1:
        st.markdown("#### Network Latency")

        if (
            not telemetry_df.empty
            and "latency_ms" in telemetry_df.columns
        ):
            latency_df = telemetry_df.dropna(
                subset=["latency_ms"]
            ).copy()

            if not latency_df.empty:
                if "device_id" not in latency_df.columns:
                    latency_df["device_id"] = "Unknown device"

                if "timestamp" in latency_df.columns:
                    latency_df = latency_df.sort_values("timestamp")
                    x_column = "timestamp"
                else:
                    latency_df["record_number"] = range(
                        1, len(latency_df) + 1
                    )
                    x_column = "record_number"

                fig_latency = px.line(
                    latency_df,
                    x=x_column,
                    y="latency_ms",
                    color="device_id",
                    markers=True,
                    title="Latency by Device",
                    labels={
                        "timestamp": "Time",
                        "record_number": "Record",
                        "latency_ms": "Latency (ms)",
                        "device_id": "Device",
                    },
                    template="plotly_dark",
                )
                fig_latency.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e5edf8",
                    margin=dict(l=10, r=10, t=55, b=10),
                )
                st.plotly_chart(
                    fig_latency,
                    use_container_width=True,
                )
            else:
                st.info("No valid latency measurements available.")
        else:
            st.info("No telemetry latency data is available.")

    with chart_col2:
        st.markdown("#### ML Prediction Distribution")

        if (
            not telemetry_df.empty
            and "ml_prediction" in telemetry_df.columns
        ):
            prediction_counts = (
                telemetry_df["ml_prediction"]
                .value_counts()
                .rename_axis("Prediction")
                .reset_index(name="Count")
            )

            if not prediction_counts.empty:
                fig_predictions = px.pie(
                    prediction_counts,
                    names="Prediction",
                    values="Count",
                    hole=0.62,
                    title="Normal vs Anomaly",
                    template="plotly_dark",
                )
                fig_predictions.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e5edf8",
                    margin=dict(l=10, r=10, t=55, b=10),
                )
                st.plotly_chart(
                    fig_predictions,
                    use_container_width=True,
                )
            else:
                st.info("No ML predictions available.")
        else:
            st.info("No ML prediction data is available.")

    st.markdown("#### Latest Telemetry Events")
    if not telemetry_df.empty:
        st.dataframe(
            telemetry_df.head(10),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No telemetry records found. Check the telemetry API response.")

    st.markdown("#### Latest Incidents")
    if not incidents_df.empty:
        st.dataframe(
            incidents_df.head(5),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No incidents recorded.")


# =========================================================
# TELEMETRY TAB
# =========================================================
with telemetry_tab:
    st.markdown("### Telemetry Explorer")

    if not telemetry_df.empty:
        filtered_df = telemetry_df.copy()

        if "device_id" in filtered_df.columns:
            devices = sorted(
                filtered_df["device_id"].dropna().astype(str).unique().tolist()
            )
            selected_devices = st.multiselect(
                "Filter by device",
                options=devices,
                default=devices,
                key="telemetry_devices",
            )
            filtered_df = filtered_df[
                filtered_df["device_id"].astype(str).isin(selected_devices)
            ]

        if "ml_prediction" in filtered_df.columns:
            predictions = sorted(
                filtered_df["ml_prediction"].dropna().astype(str).unique().tolist()
            )
            selected_predictions = st.multiselect(
                "Filter by ML prediction",
                options=predictions,
                default=predictions,
                key="telemetry_predictions",
            )
            filtered_df = filtered_df[
                filtered_df["ml_prediction"].astype(str).isin(selected_predictions)
            ]

        st.caption(f"Showing {len(filtered_df)} telemetry records.")
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Telemetry CSV",
            data=csv_data,
            file_name="network_aiops_telemetry.csv",
            mime="text/csv",
        )
    else:
        st.info("No telemetry data available.")


# =========================================================
# INCIDENTS TAB
# =========================================================
with incidents_tab:
    st.markdown("### Incident Management")

    if not incidents_df.empty:
        filtered_incidents = incidents_df.copy()

        if "status" in filtered_incidents.columns:
            statuses = sorted(
                filtered_incidents["status"].dropna().astype(str).unique().tolist()
            )
            selected_statuses = st.multiselect(
                "Filter by incident status",
                options=statuses,
                default=statuses,
                key="incident_statuses",
            )
            filtered_incidents = filtered_incidents[
                filtered_incidents["status"].astype(str).isin(selected_statuses)
            ]

        st.caption(f"Showing {len(filtered_incidents)} incidents.")
        st.dataframe(
            filtered_incidents,
            use_container_width=True,
            hide_index=True,
        )

        incident_csv = filtered_incidents.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Incidents CSV",
            data=incident_csv,
            file_name="network_aiops_incidents.csv",
            mime="text/csv",
        )
    else:
        st.info("No incidents are currently recorded.")


# =========================================================
# FOOTER
# =========================================================
st.divider()
st.caption(
    "Network AIOps Operations Center | "
    "FastAPI + Kafka + Machine Learning + SQLite"
)
