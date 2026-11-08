"""Permit Clock: Streamlit app. Prototype only. Not legal, financial or lending advice.

Reads only the cached CSVs in data/ (no network calls on page load). See data/SOURCES.json.
Run: streamlit run app.py

Two pages, picked in the sidebar:
  1. Where should I build?   rank every OC city by time to move-in, then compare a shortlist
  2. How is my city doing?   one city against the county, and its own permitting promises
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis as A
import costs as C
import drafts as D

st.set_page_config(page_title="Permit Clock", layout="wide", initial_sidebar_state="auto")

U = A.UNKNOWN
PALETTE = ["#1f77b4", "#e8743b", "#2ca02c"]  # chosen cities, in order; same colors everywhere
GREY = "#cfd3d8"
STAGE_LABELS = {"ent_to_permit": "Approval → permit", "permit_to_co": "Permit → move-in"}
PATH_LABELS = {"total": "Whole path: approval → move-in", **STAGE_LABELS}
UNIT_LABELS = {None: "All types", "ADU": "ADU (backyard home)", "SFD": "Single-family detached",
               "SFA": "Single-family attached (townhome)", "2 to 4": "2 to 4 units",
               "5+": "5+ units", "MH": "Mobile home"}
SAME_DAY_FLAG_PCT = 50  # ASSUMPTION: share of same-day rows that triggers the caution
NOT_ENOUGH = "Not enough reported data"
LIKELY_HELP = ("**Likely** = half of this city's past projects were finished by then. "
               "**Plan for** = 8 in 10 were. Both come from what the city reported to the state "
               "in 2018–2025, so they describe the past, not a promise.")
TERMS = ("**Approval** = the city's planning approval (the entitlement). **Permit** = the "
         "building permit. **Move-in** = the certificate of occupancy (CO), the sign-off that "
         "people can live there.")


# ---------- data (cached, no network) ----------

@st.cache_data
def data() -> pd.DataFrame:
    return A.add_durations(A.load_a2())


@st.cache_data
def sources() -> dict:
    return json.loads((A.DATA_DIR / "SOURCES.json").read_text())


@st.cache_data
def programs(today: dt.date) -> pd.DataFrame:
    # today is an argument so the cache key changes each day; otherwise a long-running app
    # would keep counting "overdue" against the date it first loaded.
    return A.add_overdue(A.load_programs(), today)


@st.cache_data
def mc(city: str, unit_cat, start: str) -> dict:
    # monthly_cost=1, so r["cost"] holds months from approval to move-in; dollars are applied
    # on screen, which keeps the cache warm when the user edits the cost calculator.
    return A.monte_carlo(data(), city, unit_cat, start, 1.0)


@st.cache_data
def stage_summary(city: str, unit_cat, stage: str) -> dict:
    return A.summary(data(), city, unit_cat, stage)


@st.cache_data
def best_q(stage: str):
    return A.best_quartile(A.peer_medians(data(), None, stage))


@st.cache_data
def best_q_n(stage: str) -> int:
    """How many cities the OC fastest quarter is computed from (n >= MIN_N, not same-day)."""
    peers = A.peer_medians(data(), None, stage)
    return int((~peers["same_day"]).sum())


@st.cache_data
def yearly(city: str | None, stage: str) -> pd.DataFrame:
    return A.yearly_medians(data(), city, stage)


@st.cache_data
def rank_table(unit_cat, start: str, path: str) -> pd.DataFrame:
    """One row per OC jurisdiction: likely and plan-for months on the chosen path, with n.

    likely/plan are None where the city has fewer than MIN_N usable records (ASSUMPTION).
    """
    rows = []
    for c in cities:
        if path == "total":
            r = mc(c, unit_cat, start)
            known = r["co_date"]["P50"] != U
            rows.append({"city": c, "likely": r["cost"]["P50"] if known else None,
                         "plan": r["cost"]["P80"] if known else None,
                         "n": f"{r['n']['ent_to_permit']} approval→permit and "
                              f"{r['n']['permit_to_co']} permit→move-in records",
                         "likely_date": r["co_date"]["P50"] if known else None,
                         "plan_date": r["co_date"]["P80"] if known else None,
                         "rough": known and r["method"] != "paired"})
        else:
            sm = stage_summary(c, unit_cat, path)
            known = sm["P50"] != U
            rows.append({"city": c, "likely": sm["P50"] if known else None,
                         "plan": sm["P80"] if known else None, "n": f"{sm['n']} records",
                         "likely_date": None, "plan_date": None, "rough": False})
    return pd.DataFrame(rows)


def api_key() -> str | None:
    """Key from the environment, .env (local) or Streamlit secrets. Never shown or logged."""
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:  # no secrets file
            key = None
    return key or None


@st.cache_data(show_spinner="Drafting…")
def live_draft(city: str, row_items: tuple) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("no API key")
    return D.claude_draft(city, dict(row_items), key)


# ---------- formatting ----------

def half(x) -> float:
    """Months rounded to the nearest half month, as shown on screen."""
    return round(x * 2) / 2


def months(x) -> str:
    if x is None or x == U:
        return NOT_ENOUGH
    m = half(x)
    return f"{m:g} month{'' if m == 1 else 's'}"


def usd(x) -> str:
    """Dollars to the nearest $100, plain (for st.metric and charts)."""
    return f"${round(x, -2):,.0f}"


def usd_md(x) -> str:
    """Dollars for st.markdown, where a bare $ starts a math block."""
    return usd(x).replace("$", "\\$")


def date(x) -> str:
    return NOT_ENOUGH if x is None or x == U else pd.Timestamp(x).strftime("%b %Y")


def title(city: str) -> str:
    return city.title()


def month_gap(a, b) -> int:
    """Whole months between two shown dates (same arithmetic as the labels on screen)."""
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    return (a.year - b.year) * 12 + a.month - b.month


def ms(a, b) -> float:
    """Milliseconds from a to b, for Plotly bars on a date axis."""
    return (pd.Timestamp(b) - pd.Timestamp(a)).total_seconds() * 1000


def unit_phrase(unit_cat) -> str:
    return "all unit types" if unit_cat is None else UNIT_LABELS[unit_cat]


# ---------- charts ----------

def rank_chart(tbl: pd.DataFrame, highlight: dict[str, str], path: str) -> go.Figure | None:
    """Horizontal bars: solid = likely months, faded extension = plan-for. Fastest at the top."""
    known = tbl.dropna(subset=["likely"]).sort_values("likely", ascending=False)
    if known.empty:
        return None
    names = [title(c) + (" *" if r else "") for c, r in zip(known["city"], known["rough"])]
    colors = [highlight.get(c, GREY) for c in known["city"]]
    if path == "total":
        custom = [[months(l), date(ld), months(p), date(pd_), n] for l, ld, p, pd_, n in
                  zip(known["likely"], known["likely_date"], known["plan"], known["plan_date"],
                      known["n"])]
        hover = ("<b>%{y}</b><br>Likely: %{customdata[0]} (%{customdata[1]})<br>"
                 "Plan for: %{customdata[2]} (%{customdata[3]})<br>"
                 "Based on %{customdata[4]}<extra></extra>")
    else:
        custom = [[months(l), "", months(p), "", n] for l, p, n in
                  zip(known["likely"], known["plan"], known["n"])]
        hover = ("<b>%{y}</b><br>Likely: %{customdata[0]}<br>Plan for: %{customdata[2]}<br>"
                 "Based on %{customdata[4]}<extra></extra>")
    fig = go.Figure()
    fig.add_bar(y=names, x=[half(v) for v in known["likely"]], orientation="h", name="Likely",
                marker_color=colors, customdata=custom, hovertemplate=hover)
    fig.add_bar(y=names, x=[half(p) - half(l) for p, l in zip(known["plan"], known["likely"])],
                orientation="h", name="Plan for (extra)", marker_color=colors,
                marker_opacity=0.35, customdata=custom, hovertemplate=hover)
    fig.update_layout(barmode="stack", height=70 + 26 * len(known),
                      margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Months",
                      showlegend=False, yaxis=dict(tickfont=dict(size=12)))
    return fig


def timeline_chart(sel: list[str], res: dict[str, dict], start: dt.date) -> go.Figure | None:
    """Calendar bars per chosen city: approval → permit → move-in (likely), then plan-for."""
    fig, any_bar = go.Figure(), False
    for i, c in enumerate(sel):
        r, color, name = res[c], PALETTE[i % len(PALETTE)], title(c)
        p50 = r["permit_date"]["P50"]
        if p50 == U:
            fig.add_annotation(y=name, x=pd.Timestamp(start), text=f"{NOT_ENOUGH}",
                               showarrow=False, xanchor="left", font=dict(color="#6b7280"))
            continue
        any_bar = True
        fig.add_bar(y=[name], base=[pd.Timestamp(start)], x=[ms(start, p50)], orientation="h",
                    marker_color=color, name="Approval → permit", showlegend=(i == 0),
                    legendgroup="s1", hovertemplate=f"{name}<br>Permit likely {date(p50)}"
                    "<extra></extra>")
        co50, co80 = r["co_date"]["P50"], r["co_date"]["P80"]
        if co50 == U:
            fig.add_annotation(y=name, x=p50, text=f" permit → move-in: {NOT_ENOUGH.lower()}",
                               showarrow=False, xanchor="left", font=dict(color="#6b7280"))
            continue
        fig.add_bar(y=[name], base=[p50], x=[ms(p50, co50)], orientation="h",
                    marker_color=color, marker_pattern_shape="/", name="Permit → move-in",
                    showlegend=(i == 0), legendgroup="s2",
                    hovertemplate=f"{name}<br>Move-in likely {date(co50)}<extra></extra>")
        fig.add_bar(y=[name], base=[co50], x=[ms(co50, co80)], orientation="h",
                    marker_color=color, marker_opacity=0.35, name="Plan for (extra time)",
                    showlegend=(i == 0), legendgroup="s3",
                    hovertemplate=f"{name}<br>Plan for move-in by {date(co80)}<extra></extra>")
    if not any_bar:
        return None
    fig.add_vline(x=pd.Timestamp(start).timestamp() * 1000, line_dash="dot", line_color="#6b7280")
    fig.update_layout(barmode="stack", height=90 + 60 * len(sel),
                      margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(type="date", title=""),
                      yaxis=dict(autorange="reversed"),
                      legend=dict(orientation="h", y=1.1, x=0))
    return fig


def trend_chart(sel: list[str], stage: str) -> go.Figure:
    fig = go.Figure()
    oc = yearly(None, stage)
    fig.add_scatter(x=oc["YEAR"], y=[half(v) if pd.notna(v) else None for v in oc["P50"]],
                    mode="lines+markers", name="All of Orange County", line=dict(color="#111827"),
                    customdata=oc["n"], hovertemplate="%{x}: %{y} months (n=%{customdata})"
                    "<extra>All OC</extra>")
    for i, c in enumerate(sel):
        y = yearly(c, stage)
        if y["P50"].notna().sum() == 0:
            continue
        fig.add_scatter(x=y["YEAR"], y=[half(v) if pd.notna(v) else None for v in y["P50"]],
                        mode="lines+markers", name=title(c), line=dict(color=PALETTE[i % 3]),
                        connectgaps=False, customdata=y["n"],
                        hovertemplate="%{x}: %{y} months (n=%{customdata})<extra>" + title(c)
                        + "</extra>")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title="Typical months", xaxis_title="Report year",
                      legend=dict(orientation="h", y=1.1, x=0))
    return fig


# ---------- plain-language notes ----------

def city_notes(city: str, unit_cat, r: dict) -> list[str]:
    """Every caveat that applies to one city's forecast, in plain words, labels included."""
    notes = [f"Based on {r['n']['ent_to_permit']} approval → permit and "
             f"{r['n']['permit_to_co']} permit → move-in records that {title(city)} reported "
             f"for {unit_phrase(unit_cat)}, 2018–2025."]
    for s, label in STAGE_LABELS.items():
        if r["n"][s] < A.MIN_N:
            notes.append(f"{label}: fewer than {A.MIN_N} usable records (ASSUMPTION: minimum "
                         f"{A.MIN_N}), so it is shown as \"{NOT_ENOUGH.lower()}\". Try "
                         "\"All types\" or another city.")
    if r["co_date"]["P50"] != U and r["method"] != "paired":
        notes.append(f"Only {r['n_paired']} records show both stages for the same project, so "
                     "the two stages were combined as if independent (ASSUMPTION). Treat the "
                     "plan-for date as rough.")
    sd = stage_summary(city, unit_cat, "ent_to_permit")["same_day_pct"]
    if isinstance(sd, (int, float)) and sd >= SAME_DAY_FLAG_PCT:
        notes.append(f"Caution: {sd:.0f}% of its approval → permit records give the same date "
                     "for both steps. That is probably how the city reports (INFERRED), not "
                     "real speed, so its approval → permit time is likely understated.")
    return notes


def verdict(sel: list[str], res: dict[str, dict], cost: float | None) -> str:
    """One short paragraph: who is fastest, by how much, and what the wait costs."""
    known = [c for c in sel if res[c]["co_date"]["P50"] != U]
    if not known:
        return (f"None of the chosen cities reported enough projects to forecast "
                f"({NOT_ENOUGH.lower()}). Try \"All types\" or pick a city from the chart above.")
    known.sort(key=lambda c: res[c]["co_date"]["P50"])
    first = known[0]
    r0 = res[first]
    parts = [f"In **{title(first)}**, people would likely move in by "
             f"**{date(r0['co_date']['P50'])}**; plan for **{date(r0['co_date']['P80'])}** to "
             "be safe."]
    for c in known[1:]:
        r = res[c]
        gap = month_gap(r["co_date"]["P50"], r0["co_date"]["P50"])
        parts.append(f"**{title(c)}**: likely {date(r['co_date']['P50'])}, plan for "
                     f"{date(r['co_date']['P80'])}"
                     + (f", about **{months(gap)} longer**." if gap > 0 else
                        " (about the same)."))
    rough = [title(c) for c in known if res[c]["method"] != "paired"]
    if rough:
        parts.append(f"Figures for {' and '.join(rough)} are rough (see \"How we got this\").")
    for c in sel:
        if c not in known:
            parts.append(f"{title(c)}: {NOT_ENOUGH.lower()}.")
    if cost:
        parts.append("\n\n")  # money on its own line, so the dates read first
        c0 = r0["cost"]
        parts.append(f"At {usd_md(cost)} a month, the wait in {title(first)} costs about "
                     f"**{usd_md(c0['P50'] * cost)}**; set aside "
                     f"**{usd_md(c0['P80'] * cost - c0['P50'] * cost)}** more as contingency "
                     "in case it runs to the plan-for date.")
        for c in known[1:]:
            extra = (res[c]["cost"]["P50"] - c0["P50"]) * cost
            if extra >= 50:
                parts.append(f"{title(c)} would cost about **{usd_md(extra)}** more in waiting.")
    return " ".join(parts).replace(" \n\n ", "\n\n")


# ---------- app ----------

df = data()
cities = sorted(df["JURIS_NAME"].dropna().unique())

with st.sidebar:
    st.title("Permit Clock")
    st.caption("How long permits really take in Orange County cities, from the state's own "
               "housing reports.")
    page = st.radio("I want to…", ["Where should I build?", "How is my city doing?"],
                    label_visibility="collapsed")
    st.divider()

if page == "Where should I build?":
    with st.sidebar:
        unit_cat = st.selectbox("Unit type", list(UNIT_LABELS), format_func=UNIT_LABELS.get)
        start = st.date_input("Planning approval date", value=dt.date.today(),
                              help="The day the city approves the project (the entitlement). "
                                   "The forecast starts here.")
        sel = st.multiselect("Cities to compare (up to 3)", cities, default=["TUSTIN", "SANTA ANA"],
                             format_func=title, max_selections=3)
        with st.expander("What a month of waiting costs you"):
            use_cost = st.checkbox("Show costs in dollars", value=True)
            loan = st.number_input("Acquisition loan balance ($)", min_value=0, step=10_000,
                                   value=C.EXAMPLE["loan_balance"])
            rate = st.number_input("Interest rate (% per year)", min_value=0.0, step=0.25,
                                   value=C.SOURCES["interest_rate_pct"]["value"])
            value = st.number_input("Assessed value ($)", min_value=0, step=10_000,
                                    value=C.EXAMPLE["assessed_value"])
            tax = st.number_input("Property tax rate (% per year)", min_value=0.0, step=0.1,
                                  value=C.SOURCES["property_tax_pct"]["value"])
            build = st.number_input("Construction not yet built ($)", min_value=0, step=10_000,
                                    value=C.EXAMPLE["construction_budget"])
            esc = st.number_input("Construction cost rise (% per year)", min_value=0.0,
                                  step=0.5, value=C.SOURCES["escalation_pct"]["value"])
            fixed = st.number_input("Insurance, staff, other ($ per month)", min_value=0,
                                    step=100, value=C.EXAMPLE["fixed_monthly"])
            parts = C.monthly_cost(loan, rate, value, tax, build, esc, fixed)
            st.markdown(f"**≈ {usd_md(parts['total'])} per month** of waiting")
            st.caption(", ".join(f"{k.lower()} {usd_md(v)}" for k, v in parts.items()
                                 if k != "total"))
            st.caption("The dollar amounts start from a made-up one-home example (ASSUMPTION, "
                       "`lanes/3-fund-it/data/synthetic-example-deal.json`): replace them with "
                       "your project. The rates are sourced: prime rate "
                       f"{C.SOURCES['interest_rate_pct']['value']:.2f}% (Federal Reserve H.15 "
                       f"via FRED, {C.SOURCES['interest_rate_pct']['observed']}); property tax "
                       f"{C.SOURCES['property_tax_pct']['value']}% (Prop 13's 1% plus about "
                       "0.1% voter-approved debt, Legislative Analyst's Office); construction "
                       f"cost +{C.SOURCES['escalation_pct']['value']}%/yr (Turner Building Cost "
                       "Index Q3 2026, national). Checked 2026-11-08. Insurance and staff have "
                       "no public source: enter yours.")
        cost = parts["total"] if use_cost and parts["total"] > 0 else None

    st.header("Where should I build?")
    st.caption(f"Time from planning approval to move-in for {unit_phrase(unit_cat)}, if approval "
               f"came on {start:%b %d, %Y}. Hover a bar for dates and sample size.", help=TERMS)

    # 1. Every city, ranked.
    path = st.radio("Show", list(PATH_LABELS), format_func=PATH_LABELS.get, horizontal=True,
                    label_visibility="collapsed")
    tbl = rank_table(unit_cat, start.isoformat(), path)
    highlight = {c: PALETTE[i % 3] for i, c in enumerate(sel)}
    fig = rank_chart(tbl, highlight, path)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        rough = tbl[tbl["rough"] & tbl["likely"].notna()]
        st.caption("Solid bar = likely (half of past projects done by then). Faded bar = plan "
                   "for (8 in 10 done by then)."
                   + (" * = stages combined as if independent because few records show both "
                      "(ASSUMPTION); treat as rough." if len(rough) else ""), help=LIKELY_HELP)
    else:
        st.info(f"No city reported {A.MIN_N} or more {unit_phrase(unit_cat)} projects on this "
                "path. Try \"All types\".")
    missing = tbl[tbl["likely"].isna()]["city"].map(title).tolist()
    if missing:
        st.caption(f"{NOT_ENOUGH} (fewer than {A.MIN_N} usable records, ASSUMPTION): "
                   + ", ".join(missing) + ".")

    # 2. The shortlist.
    st.subheader("Your shortlist")
    if not sel:
        st.info("Pick up to three cities in the sidebar to compare them side by side.")
    else:
        res = {c: mc(c, unit_cat, start.isoformat()) for c in sel}
        st.markdown(verdict(sel, res, cost))
        tl = timeline_chart(sel, res, start)
        if tl is not None:
            st.plotly_chart(tl, use_container_width=True)
        cols = st.columns(len(sel))
        for i, c in enumerate(sel):
            r = res[c]
            with cols[i]:
                st.markdown(f"<span style='color:{PALETTE[i % 3]};font-size:1.3em'>●</span> "
                            f"**{title(c)}**", unsafe_allow_html=True)
                st.metric("Move-in, likely", date(r["co_date"]["P50"]), help=LIKELY_HELP)
                st.metric("Move-in, plan for", date(r["co_date"]["P80"]))
                if cost and r["co_date"]["P50"] != U:
                    st.metric("Cost of waiting, likely", usd(r["cost"]["P50"] * cost),
                              help="Months from approval to move-in × your cost per month.")
                    st.metric("Contingency to set aside",
                              usd(r["cost"]["P80"] * cost - r["cost"]["P50"] * cost),
                              help="The extra cost if the project runs to the plan-for date "
                                   "instead of the likely one.")
                for s, label in STAGE_LABELS.items():
                    sm = stage_summary(c, unit_cat, s)
                    st.caption(f"{label}: likely {months(sm['P50'])}"
                               + (f", plan for {months(sm['P80'])} (n={sm['n']})"
                                  if sm["P50"] != U else f" (n={sm['n']})"))
                with st.expander("How we got this"):
                    for note in city_notes(c, unit_cat, r):
                        st.markdown(f"- {note}")
        if start < dt.date.today():
            st.caption("Your approval date is in the past; dates are still counted from it.")

        # 3. Direction of travel.
        st.subheader("Is it getting faster?")
        stage_t = st.radio("Stage", list(STAGE_LABELS), format_func=STAGE_LABELS.get,
                           horizontal=True, label_visibility="collapsed", key="trend_stage",
                           index=1)
        st.plotly_chart(trend_chart(sel, stage_t), use_container_width=True)
        st.caption(f"Typical (median) months by the year the project was reported. A city's line "
                   f"has a gap where it reported fewer than {A.MIN_N} projects that year "
                   "(ASSUMPTION). Reports, not reality: cities that report entitlement and "
                   "permit on the same day look fast.")

    with st.expander("Sources and method"):
        src = sources()
        t = src["tables"]["oc_apr_a2.csv"]
        st.markdown(
            f"- **Data:** {t['name']}, {src['publisher']}. Resource `{t['resource_id']}`, "
            f"filter {t['filter']}, {t['rows']:,} rows, pulled {src['pulled_at_utc'][:10]}. "
            f"[API link]({t['url']}). Addresses, names and coordinates were dropped.\n"
            f"- {TERMS}\n"
            "- Durations use only records that report both dates in the same row. Cities with "
            f"fewer than {A.MIN_N} such records show \"{NOT_ENOUGH.lower()}\" (ASSUMPTION).\n"
            f"- Forecast: {A.N_DRAWS:,} random draws from that city's past projects, starting "
            "from your approval date. Where fewer than "
            f"{A.MIN_N} records hold both stages, the stages are drawn separately (ASSUMPTION: "
            "independent) and marked *.\n"
            "- Likely = the middle outcome (50th percentile). Plan for = the 80th percentile.")
        ana = stage_summary("ANAHEIM", None, "ent_to_permit")
        ful = stage_summary("FULLERTON", None, "ent_to_permit")
        hb = stage_summary("HUNTINGTON BEACH", None, "permit_to_co")
        org = stage_summary("ORANGE", "ADU", "permit_to_co")
        org_days = U if org["P50"] == U else f"{org['P50'] * A.DAYS_PER_MONTH:.0f} days"
        st.markdown(
            f"- **Same-day pattern:** Anaheim ({ana['same_day_pct']}% of n={ana['n']}) and "
            f"Fullerton ({ful['same_day_pct']}% of n={ful['n']}) report the approval date "
            "equal to the permit date. Probably how they report (INFERRED, not confirmed), so "
            "a short approval → permit time there is not proof of speed.\n"
            f"- **Huntington Beach:** {hb['n']} usable permit → move-in records out of "
            f"{hb['rows']:,} rows; its completion dates are largely missing.\n"
            f"- **Sources disagree (City of Orange ADUs, permit → move-in):** our median is "
            f"{org_days} (n={org['n']}). BackyardADU.net gives 263 days "
            "(https://backyardadu.net/data/build_times.csv, third party, checked 2026-11-07). "
            "Cite the APR for anything official.\n"
            "- **Cost of waiting:** see the calculator in the sidebar for every rate and its "
            "source. Dollar defaults are a made-up example (ASSUMPTION).")
        st.caption("Association, not cause: these numbers describe past reports and do not "
                   "explain why a city is faster or slower.")

else:
    prog_all = programs(dt.date.today())
    b_cities = sorted(set(prog_all["JURIS_NAME"]) | set(cities))
    with st.sidebar:
        city = st.selectbox("City", b_cities, index=b_cities.index("TUSTIN"), format_func=title)
    prog = prog_all[prog_all["JURIS_NAME"] == city]
    n_prog = len(prog)
    n_over = int((prog["overdue"] == "yes").sum())
    n_unk = int((prog["overdue"] == "unknown").sum())

    st.header(f"How is {title(city)} doing?")
    st.caption("Its typical permit times against the fastest quarter of Orange County cities, "
               "and the permitting promises in its own 2025 housing report.", help=TERMS)

    # 1. Three tiles.
    gaps = {}
    tiles = st.columns(3)
    for col, (s, label) in zip(tiles, STAGE_LABELS.items()):
        sm = stage_summary(city, None, s)
        bq = best_q(s)
        with col:
            if sm["P50"] == U:
                st.metric(label, NOT_ENOUGH, help=f"{sm['n']} usable records, below {A.MIN_N} "
                          "(ASSUMPTION: minimum sample).")
            elif sm["P50"] == 0:
                st.metric(label, "Same day", help="Most records give the same date for both "
                          "steps: probably a reporting pattern (INFERRED), not speed.")
            elif bq == U:
                st.metric(label, months(sm["P50"]), help=f"Typical (median) of n={sm['n']}. No "
                          "county benchmark for this stage.")
            else:
                gaps[label] = half(sm["P50"]) - half(bq)
                behind = gaps[label] >= 0.25
                st.metric(label, months(sm["P50"]),
                          delta=(f"+{months(gaps[label])} vs fastest quarter"
                                 if behind else "At or ahead of fastest quarter"),
                          delta_color="inverse" if behind else "normal",
                          help=f"Typical (median) of n={sm['n']} records, all unit types. "
                               f"Fastest quarter of OC cities = {months(bq)} "
                               f"({best_q_n(s)} cities with n ≥ {A.MIN_N}; same-day cities "
                               "left out, ASSUMPTION).")
    with tiles[2]:
        if n_prog:
            st.metric("Permitting promises overdue", f"{n_over} of {n_prog}",
                      delta=(f"{n_unk} more have no single target date" if n_unk else None),
                      delta_color="off",
                      help="Programs in the city's 2025 annual report that touch permitting. "
                           "Overdue = target date before today and not reported completed.")
        else:
            st.metric("Permitting promises", "None found",
                      help="No permitting-related programs in the 2025 Table D extract.")

    # 2. Rank among OC cities.
    st.subheader(f"Where {title(city)} sits among Orange County cities")
    path = st.radio("Show", list(PATH_LABELS), format_func=PATH_LABELS.get, horizontal=True,
                    label_visibility="collapsed", key="rank_path_b")
    tbl = rank_table(None, dt.date.today().isoformat(), path)
    fig = rank_chart(tbl, {city: PALETTE[0]}, path)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Solid bar = likely (half of past projects done by then). Faded bar = plan for "
                   "(8 in 10 done by then). All unit types, 2018–2025.", help=LIKELY_HELP)
    row = tbl[tbl["city"] == city].iloc[0]
    if row["likely"] is None or pd.isna(row["likely"]):
        st.caption(f"{title(city)} is not on the chart: {NOT_ENOUGH.lower()} on this path "
                   f"({row['n']}).")

    # 3. Promises: a skimmable list grouped by program, overdue first.
    st.subheader("Its permitting promises")
    if n_prog:
        status_word = pd.Series("Due later", index=prog.index)
        status_word[prog["status_bucket"] == "completed"] = "Done"
        status_word[prog["overdue"] == "yes"] = "Overdue"
        status_word[(prog["overdue"] == "unknown") & (prog["status_bucket"] != "completed")] = \
            "No single target date"
        counts = status_word.value_counts()
        order = [s for s in ["Overdue", "Due later", "No single target date", "Done"]
                 if s in counts.index]
        choice = st.radio("Show", ["All"] + [f"{s} ({counts[s]})" for s in order],
                          horizontal=True, label_visibility="collapsed", key="prog_filter")
        keep = pd.Series(True, index=prog.index) if choice == "All" else \
            status_word == choice.rsplit(" (", 1)[0]
        show = prog[keep]
        groups = A.program_groups(prog)
        method = prog["method"].iloc[0]
        st.caption("Grouped by program, most overdue first. Status and type were read from the "
                   "city's own text by "
                   + ("Claude Haiku (claude-haiku-5-5), not yet hand-checked"
                      if method.startswith("claude") else "a keyword match, not reviewed")
                   + ". Pick a promise below to read the city's own words.")
        DOT = {"Overdue": "#d62728", "Due later": "#e8a33b", "Done": "#2ca02c"}
        RANK = {"Overdue": 0, "Due later": 1, "No single target date": 2, "Done": 3}
        st.markdown("<style>.pc-h{font-weight:600;font-size:1.05em;margin-bottom:4px}"
                    ".pc-r{padding:2px 0 2px 14px;line-height:1.45}.pc-done{color:#6b7280}"
                    ".pc-m{color:#6b7280;font-size:0.85em;font-weight:400}</style>",
                    unsafe_allow_html=True)

        def tgt(i) -> str:
            t = prog.at[i, "target_date"]
            return date(t) if isinstance(t, str) else "no single date"

        def row_html(i) -> str:
            word = status_word[i]
            cls = "pc-r pc-done" if word == "Done" else "pc-r"
            item = A._clip(groups.at[i, "item"], 130)
            return (f"<div class='{cls}'><span style='color:{DOT.get(word, '#9ca3af')}'>●</span> "
                    f"{item} <span class='pc-m'>· {word.lower()} · target {tgt(i)} · "
                    f"city reports “{prog.at[i, 'status_bucket']}”</span></div>")

        if show.empty:
            st.info("No promises match this filter.")
        g_all = groups["group"]
        g_over = status_word.eq("Overdue").groupby(g_all).sum()
        g_first = pd.to_datetime(prog["target_date"], errors="coerce").groupby(g_all).min()
        g_rank = status_word.map(RANK).groupby(g_all).min()
        shown_groups = sorted(set(g_all[show.index]),
                              key=lambda g: (g_rank[g], -g_over[g],
                                             g_first[g] if pd.notna(g_first[g])
                                             else pd.Timestamp.max))
        for g in shown_groups:
            idx = sorted([i for i in show.index if g_all[i] == g],
                         key=lambda i: (RANK[status_word[i]], str(prog.at[i, "target_date"])))
            n_g = int((g_all == g).sum())
            with st.container(border=True):
                head = (f"<div class='pc-h'>{g} <span class='pc-m'>· "
                        + (f"{n_g} promises" if n_g > 1 else "1 promise")
                        + (f", {int(g_over[g])} overdue" if g_over[g] else "") + "</span></div>")
                st.markdown(head + "".join(row_html(i) for i in idx), unsafe_allow_html=True)

        # 4. Look closer at one promise, then draft a request about it (never sent).
        st.subheader("Look closer at one")
        opts = list(show.index) if not show.empty else list(prog.index)
        pick = st.selectbox("Promise", opts, key="draft_prog", label_visibility="collapsed",
                            format_func=lambda i: f"{status_word[i]} · "
                            f"{A._clip(groups.at[i, 'item'], 80)} ({A._clip(g_all[i], 50)})")
        p = prog.loc[pick]
        with st.container(border=True):
            st.markdown(f"**{g_all[pick]}**")
            st.markdown(f"**The city's objective:** {p['PROGRAM_OBJECTIVE']}")
            st.markdown(f"**Status reported by the city:** {p['PROGRAM_STATUS']}")
            st.caption(f"{status_word[pick]} · target {tgt(pick)} · type "
                       f"{p['category'][:1].upper() + p['category'][1:]} · status label "
                       f"\"{p['status_bucket']}\" · full program name: "
                       f"{' '.join(str(p['PROGRAM_NAME']).split())}")

        open_cats = sorted(set(prog.loc[prog["status_bucket"] != "completed", "category"])
                           - {"other"})
        lines = []
        for c in open_cats:
            peers = A.peers_completed(prog_all, city, c)
            label = c[:1].upper() + c[1:]  # display only: "fees" -> "Fees"
            lines.append(f"- **{label}:** " + (", ".join(title(p) for p in peers) if peers
                                                else "none reported completed"))
        if lines:
            with st.expander("Other OC cities that report finishing the same kind of promise"):
                st.markdown("\n".join(lines))
                st.caption("Self-reported by each city. Finishing a program does not show it "
                           "made that city faster.")

        st.markdown("**Ask the city about it**")
        st.caption("A polite note quoting the city's own promise. Nothing is sent: copy, review "
                   "and edit it yourself.")
        row = prog.loc[pick].to_dict()
        key = api_key()
        if key and st.button("Draft with Claude", key="draft_btn"):
            try:
                st.session_state["draft"] = (city, pick,
                                             live_draft(title(city), tuple(row.items())))
            except Exception as e:  # network, auth or model error: fall back and say so
                st.session_state["draft"] = (city, pick, None)
                st.warning(f"Live draft unavailable ({type(e).__name__}); showing the template.")
        saved = st.session_state.get("draft")
        if saved and saved[:2] == (city, pick) and saved[2]:
            label = "Draft: review before use (Claude Haiku, claude-haiku-5-5)"
            text, src = saved[2], "claude"
        else:
            label = ("Draft: review before use (template; "
                     + ("click the button for a Claude draft)" if key
                        else "live drafting unavailable: no API key set)"))
            text, src = D.static_template(title(city), row), "template"
        st.text_area(label, text, height=300, key=f"draft_text_{city}_{pick}_{src}")
    else:
        st.info(f"No permitting-related programs found for {title(city)} in the 2025 Table D "
                "extract. Try another city.")

    with st.expander("Sources and method"):
        src = sources()
        td = src["tables"]["oc_apr_tableD.csv"]
        st.markdown(
            f"- **Promises:** {td['name']}, {src['publisher']}. Resource `{td['resource_id']}`, "
            f"2025 report year, keyword-filtered to permitting topics, pulled "
            f"{src['pulled_at_utc'][:10]}. [API link]({td['url']})\n"
            "- **Overdue** = target date before today and status not \"completed\". \"No single "
            "target date\" when the target is a range or missing. Status labels can be wrong: "
            "read the city's own words on each card.\n"
            "- **Stage times:** APR Table A2, same-row date pairs, all unit types (see the "
            "\"Where should I build?\" page). Fastest quarter = 25th percentile of city medians "
            f"among cities with n ≥ {A.MIN_N}, leaving out same-day cities (ASSUMPTION).")
        st.caption("Association, not cause: a promise's status does not show it made a city "
                   "faster or slower. Nothing here says a city broke a law.")

st.caption("Prototype. Not legal, financial or lending advice. Check decisions with a professional.")
