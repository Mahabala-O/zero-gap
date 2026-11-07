"""Permit Clock: Streamlit app. Prototype only. Not legal, financial or lending advice.

Reads only the cached CSVs in data/ (no network calls on page load). See data/SOURCES.json.
Run: streamlit run app.py
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
import drafts as D

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
SAME_DAY_FLAG_PCT = 50  # ASSUMPTION: share of same-day rows that triggers the caution


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


@st.cache_data
def best_q(stage: str):
    return A.best_quartile(A.peer_medians(data(), None, stage))


@st.cache_data
def best_q_n(stage: str) -> int:
    """How many cities the OC best quartile is computed from (n >= MIN_N, not same-day)."""
    peers = A.peer_medians(data(), None, stage)
    return int((~peers["same_day"]).sum())


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


@st.cache_data
def programs() -> pd.DataFrame:
    return A.add_overdue(A.load_programs(), dt.date.today())


def half(x) -> float:
    """Months rounded to the nearest half month, as shown on screen."""
    return round(x * 2) / 2


def months(x) -> str:
    if x == U:
        return U
    m = half(x)
    return f"{m:g} month{'' if m == 1 else 's'}"


def dollars(x) -> str:
    return U if x == U else f"${round(x, -2):,.0f}"


def shown_contingency(r: dict):
    """P80 minus P50 cost as shown on screen (each rounded to $100), so the row adds up."""
    if r["contingency"] == U:
        return U
    return round(r["cost"]["P80"], -2) - round(r["cost"]["P50"], -2)


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
        parts.append(f"Budget **{dollars(shown_contingency(ra))}** contingency in "
                     f"{title(city_a)} (P80 minus P50 carrying cost, ASSUMPTION cost/month).")
    else:
        parts.append(f"Contingency for {title(city_a)} is **unknown**: too few records.")
    if ra["co_date"]["P80"] != U and rb["co_date"]["P80"] != U and city_a != city_b:
        # Gap = difference of the shown move-in months, so it matches the table's dates.
        pa, pb = pd.Timestamp(ra["co_date"]["P80"]), pd.Timestamp(rb["co_date"]["P80"])
        gap = (pa.year - pb.year) * 12 + pa.month - pb.month
        if gap == 0:
            parts.append("The two cities are about the same at P80.")
        else:
            fast, slow = (city_b, city_a) if gap > 0 else (city_a, city_b)
            parts.append(f"**{title(fast)}** is about **{months(abs(gap))}** faster than "
                         f"{title(slow)} at P80.")
    elif city_a != city_b:
        parts.append("Which city is faster is **unknown** for this unit type.")
    sep = [title(c) for k, c in picks.items()
           if res[k]["method"] != "paired" and res[k]["co_date"]["P80"] != U]
    sep = list(dict.fromkeys(sep))
    if sep:
        its = "its" if len(sep) == 1 else "their"
        parts.append(f"ASSUMPTION: too few records hold both stages for "
                     f"{' and '.join(sep)}, so {its} stages were drawn separately; "
                     f"treat {its} P80 as rough.")
    # ASSUMPTION: 50% threshold. Above it, a city's entitlement -> permit times mostly come
    # from rows where both dates are the same day (likely a reporting pattern, INFERRED).
    same = [title(c) for c in dict.fromkeys(picks.values())
            if isinstance(sd := stage_summary(c, unit_cat, "ent_to_permit")["same_day_pct"],
                          (int, float)) and sd >= SAME_DAY_FLAG_PCT]
    if same:
        whose = f"{same[0]}'s" if len(same) == 1 else f"{' and '.join(same)}'s each"
        its = "its" if len(same) == 1 else "their"
        parts.append(f"Caution: most of {whose} entitlement → permit records "
                     "give the same date for both (likely a reporting pattern, INFERRED), so "
                     f"{its} speed there may be overstated.")
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
        col["Contingency (P80 − P50)"] = dollars(shown_contingency(r))
        col["Method"] = ("stages drawn together" if r["method"] == "paired"
                         else "stages drawn separately (ASSUMPTION)")
        rows[f"{title(city)} ({k})"] = col
    # st.table wraps text, so City B's column stays on screen at phone width
    # (st.dataframe scrolled it off the right edge at 390 px).
    st.table(pd.DataFrame(rows))
    st.caption("Move-in dates come from whole simulated projects, so the P80 date is usually "
               "earlier than adding the two stage P80s: few projects are slow at both stages.")

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
            # Shown P80 minus shown P50 (half months), so a bar matches the table above it.
            ys.append(None if U in (sm["P50"], sm["P80"]) else half(sm["P80"]) - half(sm["P50"]))
        fig.add_bar(name=f"{title(city)} ({k})", x=list(STAGE_LABELS.values()), y=ys,
                    marker_color=COLORS[k])
    # Title as Streamlit text, not a Plotly title: Plotly clips long titles at phone width.
    st.markdown("**Which stage adds the most buffer (P80 − P50)**")
    fig.update_layout(yaxis_title="Extra months to plan for", xaxis_title="Stage",
                      barmode="group", height=320, margin=dict(l=10, r=10, t=10, b=10),
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
    prog_all = programs()
    b_cities = sorted(set(prog_all["JURIS_NAME"]) | set(cities))
    city = st.selectbox("City", b_cities, index=b_cities.index("TUSTIN"), format_func=title,
                        key="city_b_tab")
    prog = prog_all[prog_all["JURIS_NAME"] == city]

    # Stage medians vs the OC best quartile (all unit types).
    stage_rows, gaps = [], {}
    for s, label in STAGE_LABELS.items():
        sm = stage_summary(city, None, s)
        bq = best_q(s)
        if sm["P50"] == U:
            note = f"unknown (n={sm['n']}, below {A.MIN_N})"
        elif sm["P50"] == 0:
            note = "same-day (reporting pattern? INFERRED)"
        elif bq == U:
            note = U
        else:
            # Gap = difference of the shown (half-month) values, so the row adds up on screen.
            gaps[label] = half(sm["P50"]) - half(bq)
            note = (f"{months(gaps[label])} behind" if gaps[label] >= 0.25
                    else "at or ahead")
        stage_rows.append({"Stage": label,
                           f"{title(city)} median (n)": f"{months(sm['P50'])} (n={sm['n']})",
                           "OC best quartile (n)": (U if bq == U else
                                                    f"{months(bq)} ({best_q_n(s)} cities)"),
                           "Gap": note})

    n_prog = len(prog)
    n_over = int((prog["overdue"] == "yes").sum())
    head = []
    if gaps:
        slow = max(gaps, key=gaps.get)
        if gaps[slow] >= 0.25:
            head.append(f"Slowest stage: **{slow}**, about **{months(gaps[slow])}** behind the "
                        "fastest quarter of OC cities.")
        else:
            head.append(f"{title(city)} is at or ahead of the fastest quarter of OC cities "
                        "on the stages it reports.")
    else:
        head.append("How this city compares on stage times is **unknown** (too few records "
                    "or same-day reporting).")
    n_unk = int((prog["overdue"] == "unknown").sum())
    # With no programs, the info box below says so; "0 are past their target date" adds nothing.
    if n_prog:
        head.append(f"**{n_prog}** permitting-related programs in its 2025 report; "
                    f"**{n_over}** {'is' if n_over == 1 else 'are'} past their target date and "
                    "not reported completed"
                    # Without this, a city whose targets are all non-dates reads as "0 overdue".
                    + (f"; for **{n_unk}**, whether they are overdue is **unknown** (the target "
                       "is not a single date)." if n_unk else "."))
    st.markdown(" ".join(head))
    # st.table wraps text, so the benchmark column stays on screen at phone width
    # (st.dataframe scrolled it off the right edge at 390 px).
    st.table(pd.DataFrame(stage_rows).set_index("Stage"))
    st.caption("CO = certificate of occupancy, the sign-off that people can move in. "
               "Medians use all unit types and same-row date pairs. Best quartile = 25th "
               f"percentile of city medians among cities with n ≥ {A.MIN_N}, leaving out "
               "same-day (median 0) cities (ASSUMPTION: reporting pattern, not speed).")

    if n_prog:
        method = prog["method"].iloc[0]
        st.caption("Labels: " + ("Claude Haiku (claude-haiku-5-5), read from the city's own "
                                 "text; not yet hand-checked." if method.startswith("claude")
                                 else "keyword match, not reviewed."))
        show = prog.sort_values(["overdue", "target_date"], ascending=[False, True])
        labels = A.program_labels(show)
        st.dataframe(pd.DataFrame({
            "Overdue": show["overdue"],
            "Target date": show["target_date"].fillna(U),
            "Program": labels,
            "Status": show["status_bucket"],
            "Category": show["category"],
            "City's own status text": show["PROGRAM_STATUS"],
        }), use_container_width=True, hide_index=True,
            # Wide Program column so the label (and its objective snippet) is readable at 1280 px.
            column_config={"Program": st.column_config.TextColumn(width="large")})
        open_cats = sorted(set(prog.loc[prog["status_bucket"] != "completed", "category"])
                           - {"other"})
        lines = []
        for c in open_cats:
            peers = A.peers_completed(prog_all, city, c)
            lines.append(f"- **{c}:** " + (", ".join(title(p) for p in peers) if peers
                                            else "none reported completed"))
        if lines:
            st.markdown("**Peers that report completing the same kind of program** "
                        "(where this city's is not completed):\n" + "\n".join(lines))

        st.markdown("**Draft a request** (never sent: copy, review and edit it yourself)")
        opts = list(show.index)
        pick = st.selectbox("Program to ask about", opts, key="draft_prog",
                            format_func=lambda i: (f"[overdue: {show.at[i, 'overdue']}] "
                                                   f"{labels.at[i]}"))
        row = show.loc[pick].to_dict()
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
            label = ("Draft: review before use (static template; "
                     + ("click the button for a Claude draft)" if key
                        else "live drafting unavailable: no API key set)"))
            text, src = D.static_template(title(city), row), "template"
        st.text_area(label, text, height=300, key=f"draft_text_{city}_{pick}_{src}")
    else:
        st.info(f"No permitting-related programs found for {title(city)} in the 2025 Table D "
                "extract. Try another city.")

    with st.expander("Sources and caveats"):
        src = sources()
        td = src["tables"]["oc_apr_tableD.csv"]
        st.markdown(
            f"- **Programs:** {td['name']}, {src['publisher']}. Resource `{td['resource_id']}`, "
            f"2025 report year, keyword-filtered to permitting topics, pulled "
            f"{src['pulled_at_utc'][:10]}. [API link]({td['url']})\n"
            "- **Overdue** = target date before today and status not \"completed\". "
            "\"unknown\" when the target is not a single date. Status labels can be wrong: "
            "read the city's own text beside each row.\n"
            "- **Stage times:** APR Table A2 (see the Plan my project tab).")
        st.caption("Association, not cause: a program's status does not show it caused a "
                   "city to be faster or slower. Nothing here says a city broke a law.")

st.caption("Prototype. Not legal, financial or lending advice. Check decisions with a professional.")
