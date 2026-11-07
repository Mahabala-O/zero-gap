"""Permit Clock: Streamlit app. Prototype only. Not legal, financial or lending advice.

Reads only the cached CSVs in data/ (no network calls on page load). See data/SOURCES.json.
Run: streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis as A

st.set_page_config(page_title="Permit Clock", layout="centered")

# ASSUMPTION: $85,000 time cost / 48 months from the SYNTHETIC deal in
# lanes/3-fund-it/data/synthetic-example-deal.json. Not a real figure; replace with yours.
DEFAULT_MONTHLY_COST = 1771
COLORS = {"A": "#1f77b4", "B": "#e8743b"}  # City A / City B, same everywhere
STAGE_LABELS = {"ent_to_permit": "Entitlement → permit",
                "permit_to_co": "Permit → CO"}
UNIT_LABELS = {None: "All types", "ADU": "ADU", "SFD": "Single-family detached (SFD)",
               "SFA": "Single-family attached (SFA)", "2 to 4": "2 to 4 units",
               "5+": "5+ units", "MH": "Mobile home (MH)"}
U = A.UNKNOWN


@st.cache_data
def data() -> pd.DataFrame:
    return A.add_durations(A.load_a2())


@st.cache_data
def sources() -> dict:
    return json.loads((A.DATA_DIR / "SOURCES.json").read_text())


@st.cache_data
def run_mc(city: str, unit_cat, start: str, cost: float) -> dict:
    return A.monte_carlo(data(), city, unit_cat, start, cost)


@st.cache_data
def stage_summary(city: str, unit_cat, stage: str) -> dict:
    return A.summary(data(), city, unit_cat, stage)


def months(x) -> str:
    if x == U:
        return U
    m = round(x * 2) / 2
    return f"{m:g} month{'' if m == 1 else 's'}"


def dollars(x) -> str:
    return U if x == U else f"${round(x, -2):,.0f}"


def date(x) -> str:
    return U if x == U else pd.Timestamp(x).strftime("%b %Y")


def title(city: str) -> str:
    return city.title()


df = data()
cities = sorted(df["JURIS_NAME"].dropna().unique())

st.title("Permit Clock")
st.caption("How long will a small housing project take to permit and build in an Orange County "
           "city, and what does the uncertainty cost? From the state's own housing reports.")

tab_a, tab_b = st.tabs(["Plan my project", "City promise tracker"])

with tab_a:
    c1, c2 = st.columns(2)
    city_a = c1.selectbox("City A", cities, index=cities.index("TUSTIN"), format_func=title)
    city_b = c2.selectbox("City B", cities, index=cities.index("SANTA ANA"), format_func=title)
    c3, c4 = st.columns(2)
    unit_cat = c3.selectbox("Unit type", list(UNIT_LABELS), format_func=UNIT_LABELS.get)
    start = c4.date_input("Entitlement approval date", value=dt.date.today(),
                          help="Entitlement = the city's planning approval for the project. "
                               "The forecast starts here and runs to the certificate of "
                               "occupancy (CO), the sign-off that people can move in.")
    with st.expander("Carrying cost per month (ASSUMPTION)"):
        cost = st.number_input("Carrying cost, $ per month", min_value=0, step=100,
                               value=DEFAULT_MONTHLY_COST)
        st.caption("ASSUMPTION: $1,771/month is derived from the SYNTHETIC deal in "
                   "lanes/3-fund-it/data/synthetic-example-deal.json ($85k / 48 months). "
                   "It is not a real figure; replace it with yours.")

    picks = {"A": city_a, "B": city_b}
    res = {k: run_mc(c, unit_cat, start.isoformat(), float(cost)) for k, c in picks.items()}

    # Headline: contingency for City A, then which city is faster at P80 (move-in date).
    ra, rb = res["A"], res["B"]
    parts = []
    if ra["contingency"] != U:
        parts.append(f"Budget **{dollars(ra['contingency'])}** contingency in "
                     f"{title(city_a)} (P80 minus P50 carrying cost, ASSUMPTION cost/month).")
    else:
        parts.append(f"Contingency for {title(city_a)} is **unknown**: too few records.")
    if ra["co_date"]["P80"] != U and rb["co_date"]["P80"] != U and city_a != city_b:
        gap = (ra["co_date"]["P80"] - rb["co_date"]["P80"]).days / A.DAYS_PER_MONTH
        if abs(gap) < 0.5:
            parts.append("The two cities are about the same at P80.")
        else:
            fast, slow = (city_b, city_a) if gap > 0 else (city_a, city_b)
            parts.append(f"**{title(fast)}** is about **{months(abs(gap))}** faster than "
                         f"{title(slow)} at P80.")
    elif city_a != city_b:
        parts.append("Which city is faster is **unknown** for this unit type.")
    st.markdown(" ".join(parts))
    st.caption("P50 = half of past projects finished by then (likely). "
               "P80 = 80% finished by then (safe to plan). Past performance, not a promise.")

    # Small table: one column per city.
    rows = {}
    for k, city in picks.items():
        r = res[k]
        col = {}
        for s, label in STAGE_LABELS.items():
            sm = stage_summary(city, unit_cat, s)
            col[f"{label}, P50 / P80 (n)"] = (
                f"{months(sm['P50'])} / {months(sm['P80'])} (n={sm['n']})")
        col["Move-in (CO) date, P50 / P80"] = (
            f"{date(r['co_date']['P50'])} / {date(r['co_date']['P80'])}")
        col["Carrying cost, P50 / P80"] = f"{dollars(r['cost']['P50'])} / {dollars(r['cost']['P80'])}"
        col["Contingency (P80 − P50)"] = dollars(r["contingency"])
        col["Method"] = ("stages drawn together" if r["method"] == "paired"
                         else "stages drawn separately (ASSUMPTION)")
        rows[f"{title(city)} ({k})"] = col
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Dead-end help: say why it is unknown and what to try.
    for k, city in picks.items():
        unknown = [STAGE_LABELS[s] for s in STAGE_LABELS
                   if stage_summary(city, unit_cat, s)["P50"] == U]
        if unknown:
            st.info(f"{title(city)} reported fewer than {A.MIN_N} usable records for "
                    f"{' and '.join(unknown)} ({UNIT_LABELS[unit_cat]}), so it shows "
                    f"\"unknown\" (ASSUMPTION: minimum n = {A.MIN_N}). Try \"All types\" or "
                    "another city.")
    if start < dt.date.today():
        st.caption("Your start date is in the past; dates are still counted from it.")

    # One chart: which stage adds the most planning buffer (P80 - P50), per city.
    fig = go.Figure()
    for k, city in picks.items():
        ys = []
        for s in STAGE_LABELS:
            sm = stage_summary(city, unit_cat, s)
            ys.append(None if sm["P50"] == U else sm["P80"] - sm["P50"])
        fig.add_bar(name=f"{title(city)} ({k})", x=list(STAGE_LABELS.values()), y=ys,
                    marker_color=COLORS[k])
    fig.update_layout(title="Which stage adds the most buffer (P80 − P50)",
                      yaxis_title="Extra months to plan for", xaxis_title="Stage",
                      barmode="group", height=320, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Sources and caveats"):
        src = sources()
        t = src["tables"]["oc_apr_a2.csv"]
        st.markdown(
            f"- **Data:** {t['name']}, {src['publisher']}. Resource `{t['resource_id']}`, "
            f"filter {t['filter']}, {t['rows']:,} rows, pulled {src['pulled_at_utc'][:10]}. "
            f"[API link]({t['url']})\n"
            "- Durations use only records that report both dates in the same row. "
            f"Cells with fewer than {A.MIN_N} records show \"unknown\" (ASSUMPTION threshold).\n"
            "- Monte Carlo: 5,000 draws from that city's past records. When fewer than "
            f"{A.MIN_N} records hold both stages, the stages are drawn separately "
            "(ASSUMPTION: independent).")
        ana = stage_summary("ANAHEIM", None, "ent_to_permit")
        ful = stage_summary("FULLERTON", None, "ent_to_permit")
        hb = stage_summary("HUNTINGTON BEACH", None, "permit_to_co")
        org = stage_summary("ORANGE", "ADU", "permit_to_co")
        org_days = U if org["P50"] == U else f"{org['P50'] * A.DAYS_PER_MONTH:.0f} days"
        st.markdown(
            f"- **Same-day pattern:** Anaheim ({ana['same_day_pct']}% of n={ana['n']}) and "
            f"Fullerton ({ful['same_day_pct']}% of n={ful['n']}) report the entitlement date "
            "equal to the permit date. This is probably how they report (INFERRED, not "
            "confirmed), so a short entitlement → permit time there is not proof of speed.\n"
            f"- **Huntington Beach:** {hb['n']} usable permit → CO records out of {hb['rows']:,} "
            "rows; its completion dates are largely missing.\n"
            f"- **Sources disagree (City of Orange ADUs, permit → CO):** our median is "
            f"{org_days} (n={org['n']}). BackyardADU.net gives 263 days "
            "(https://backyardadu.net/data/build_times.csv, third party, checked 2026-11-07). "
            "Cite the APR for anything official.")
        st.caption("Association, not cause: these numbers describe past reports and do not "
                   "explain why a city is faster or slower.")

with tab_b:
    st.info("City promise tracker: not built yet (build step 5).")

st.caption("Prototype. Not legal, financial or lending advice. Check decisions with a professional.")
