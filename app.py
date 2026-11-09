"""Permit Clock: Streamlit app. Prototype only. Not legal, financial or lending advice.

Reads only the cached CSVs in data/ (no network calls on page load). See data/SOURCES.json
and docs/design-guidelines.md. Run: streamlit run app.py

Two pages, picked in the sidebar:
  1. What did my city promise?            a city's permitting promises from its own housing
                                          element annual report, with overdue ones flagged
  2. After approval, how long to move-in? OC cities ranked on reported permit times, with a
                                          shortlist, a timeline and the cost of waiting
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
import ui

st.set_page_config(page_title="Permit Clock", layout="wide", initial_sidebar_state="auto")
ui.inject_css()

U = A.UNKNOWN
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
PAGE_PROMISES = "What did my city promise?"
PAGE_TIMING = "After approval, how long to move-in?"
STATUS_WORD = {"yes": "Overdue", "no": "Due later", "recurring": "Recurring",
               U: "No single target date"}
STATUS_TONE = {"Overdue": "danger", "Due later": "warning", "Recurring": "neutral",
               "No single target date": "neutral", "Done": "success"}
STATUS_ORDER = ["Overdue", "Due later", "Recurring", "No single target date", "Done"]


# ---------- data (cached, no network) ----------

@st.cache_data
def data() -> pd.DataFrame:
    return A.add_durations(A.load_a2())


@st.cache_data
def frame(affordable: bool) -> pd.DataFrame:
    """All projects, or only those that permitted deed-restricted affordable units."""
    df = data()
    return df[df["deed_restricted"]] if affordable else df


@st.cache_data
def sources() -> dict:
    return json.loads((A.DATA_DIR / "SOURCES.json").read_text())


@st.cache_data
def programs(today: dt.date) -> pd.DataFrame:
    # today is an argument so the cache key changes each day; otherwise a long-running app
    # would keep counting "overdue" against the date it first loaded.
    return A.add_overdue(A.load_programs(), today)


@st.cache_data
def handcheck() -> dict:
    return A.handcheck_accuracy()


@st.cache_data
def mc(city: str, unit_cat, affordable: bool, start: str) -> dict:
    # monthly_cost=1, so r["cost"] holds months from approval to move-in; dollars are applied
    # on screen, which keeps the cache warm when the user edits the cost calculator.
    return A.monte_carlo(frame(affordable), city, unit_cat, start, 1.0)


@st.cache_data
def stage_summary(city: str, unit_cat, affordable: bool, stage: str) -> dict:
    return A.summary(frame(affordable), city, unit_cat, stage)


@st.cache_data
def best_q(stage: str):
    return A.best_quartile(A.peer_medians(data(), None, stage))


@st.cache_data
def yearly(city: str | None, affordable: bool, stage: str) -> pd.DataFrame:
    return A.yearly_medians(frame(affordable), city, stage)


@st.cache_data
def rank_table(unit_cat, affordable: bool, start: str, path: str) -> pd.DataFrame:
    """One row per OC jurisdiction: likely and plan-for months on the chosen path, with n.

    likely/plan are None where the city has fewer than MIN_N usable records (ASSUMPTION).
    """
    rows = []
    for c in cities:
        if path == "total":
            r = mc(c, unit_cat, affordable, start)
            known = r["co_date"]["P50"] != U
            rows.append({"city": c, "likely": r["cost"]["P50"] if known else None,
                         "plan": r["cost"]["P80"] if known else None,
                         "n": f"{r['n']['ent_to_permit']} approval→permit and "
                              f"{r['n']['permit_to_co']} permit→move-in records",
                         "n_short": f"n={min(r['n'].values())}",
                         "likely_date": r["co_date"]["P50"] if known else None,
                         "plan_date": r["co_date"]["P80"] if known else None,
                         "rough": known and r["method"] != "paired"})
        else:
            sm = stage_summary(c, unit_cat, affordable, path)
            known = sm["P50"] != U
            rows.append({"city": c, "likely": sm["P50"] if known else None,
                         "plan": sm["P80"] if known else None, "n": f"{sm['n']} records",
                         "n_short": f"n={sm['n']}", "likely_date": None, "plan_date": None,
                         "rough": False})
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
    """Dollars to the nearest $100."""
    return f"${round(x, -2):,.0f}"


def usd_md(x) -> str:
    """Dollars for st.markdown, where a bare $ starts a math block."""
    return usd(x).replace("$", "\\$")


def date(x) -> str:
    if x is None or (isinstance(x, str) and x == U) or pd.isna(x):
        return NOT_ENOUGH
    return pd.Timestamp(x).strftime("%b %Y")


def title(city: str) -> str:
    return city.title()


def month_gap(a, b) -> int:
    """Whole months between two shown dates (same arithmetic as the labels on screen)."""
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    return (a.year - b.year) * 12 + a.month - b.month


def ms(a, b) -> float:
    """Milliseconds from a to b, for Plotly bars on a date axis."""
    return (pd.Timestamp(b) - pd.Timestamp(a)).total_seconds() * 1000


def scope_phrase(unit_cat, affordable: bool) -> str:
    unit = "all unit types" if unit_cat is None else UNIT_LABELS[unit_cat]
    return unit + (", deed-restricted affordable projects only" if affordable else "")


# ---------- charts ----------

def rank_chart(tbl: pd.DataFrame, highlight: dict[str, str], path: str) -> go.Figure | None:
    """Horizontal bars: solid = likely months, faded extension = plan-for. Fastest at the top.
    Cities without enough data are listed at the bottom as labelled empty rows."""
    known = tbl.dropna(subset=["likely"]).sort_values("likely", ascending=False)
    unknown = tbl[tbl["likely"].isna()].sort_values("city", ascending=False)
    if known.empty:
        return None
    names = [title(c) + (" *" if r else "") for c, r in zip(known["city"], known["rough"])]
    colors = [highlight.get(c, ui.TOKENS["grey_bar"]) for c in known["city"]]
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
    u_names = [title(c) for c in unknown["city"]]
    if u_names:
        fig.add_scatter(y=u_names, x=[0] * len(u_names), mode="text",
                        text=[f"{NOT_ENOUGH.lower()} ({n})" for n in unknown["n_short"]],
                        textposition="middle right",
                        textfont=dict(color=ui.TOKENS["muted"], size=12),
                        hoverinfo="skip", showlegend=False)
    fig.add_bar(y=names, x=[half(v) for v in known["likely"]], orientation="h", name="Likely",
                marker_color=colors, customdata=custom, hovertemplate=hover)
    fig.add_bar(y=names, x=[half(p) - half(l) for p, l in zip(known["plan"], known["likely"])],
                orientation="h", name="Plan for (extra)", marker_color=colors,
                marker_opacity=0.35, customdata=custom, hovertemplate=hover)
    ui.chart(fig, 60 + 23 * (len(known) + len(unknown)))
    fig.update_layout(barmode="stack", showlegend=False, xaxis_title="Months")
    fig.update_yaxes(categoryorder="array", categoryarray=u_names + names,
                     tickvals=u_names + names,
                     ticktext=[f"<span style='color:{ui.TOKENS['muted']}'>{n}</span>"
                               for n in u_names] + names)
    return fig


def timeline_chart(sel: list[str], res: dict[str, dict], start: dt.date) -> go.Figure | None:
    """Calendar bars per chosen city: approval → permit → move-in (likely), then plan-for."""
    fig, any_bar = go.Figure(), False
    for i, c in enumerate(sel):
        r, color, name = res[c], ui.SERIES[i % 3], title(c)
        p50 = r["permit_date"]["P50"]
        if p50 == U:
            fig.add_annotation(y=name, x=pd.Timestamp(start), text=NOT_ENOUGH, showarrow=False,
                               xanchor="left", font=dict(color=ui.TOKENS["muted"]))
            continue
        any_bar = True
        fig.add_bar(y=[name], base=[pd.Timestamp(start)], x=[ms(start, p50)], orientation="h",
                    marker_color=color, name="Approval → permit", showlegend=(i == 0),
                    legendgroup="s1", hovertemplate=f"{name}<br>Permit likely {date(p50)}"
                    "<extra></extra>")
        co50, co80 = r["co_date"]["P50"], r["co_date"]["P80"]
        if co50 == U:
            fig.add_annotation(y=name, x=p50, text=f" permit → move-in: {NOT_ENOUGH.lower()}",
                               showarrow=False, xanchor="left",
                               font=dict(color=ui.TOKENS["muted"]))
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
    fig.add_vline(x=pd.Timestamp(start).timestamp() * 1000, line_dash="dot",
                  line_color=ui.TOKENS["muted"])
    ui.chart(fig, 110 + 56 * len(sel))
    fig.update_layout(barmode="stack", xaxis=dict(type="date", title=""),
                      yaxis=dict(autorange="reversed"), margin=dict(t=40),
                      legend=dict(y=1.0, yanchor="bottom"))
    return fig


def trend_chart(sel: list[str], affordable: bool, stage: str) -> go.Figure:
    fig = go.Figure()
    oc = yearly(None, affordable, stage)
    fig.add_scatter(x=oc["YEAR"], y=[half(v) if pd.notna(v) else None for v in oc["P50"]],
                    mode="lines+markers", name="All of Orange County",
                    line=dict(color=ui.TOKENS["grey_bar"], width=3), customdata=oc["n"],
                    hovertemplate="%{x}: %{y} months (n=%{customdata})<extra>All OC</extra>")
    for i, c in enumerate(sel):
        y = yearly(c, affordable, stage)
        if y["P50"].notna().sum() == 0:
            continue
        fig.add_scatter(x=y["YEAR"], y=[half(v) if pd.notna(v) else None for v in y["P50"]],
                        mode="lines+markers", name=title(c), line=dict(color=ui.SERIES[i % 3]),
                        connectgaps=False, customdata=y["n"],
                        hovertemplate="%{x}: %{y} months (n=%{customdata})<extra>" + title(c)
                        + "</extra>")
    ui.chart(fig, 280)
    fig.update_layout(yaxis_title="Typical months", xaxis_title="Report year")
    return fig


# ---------- plain-language notes ----------

def city_notes(city: str, unit_cat, affordable: bool, r: dict) -> list[str]:
    """Every caveat that applies to one city's forecast, in plain words, labels included."""
    notes = [f"Based on {r['n']['ent_to_permit']} approval → permit and "
             f"{r['n']['permit_to_co']} permit → move-in records that {title(city)} reported "
             f"for {scope_phrase(unit_cat, affordable)}, 2018–2025."]
    for s, label in STAGE_LABELS.items():
        if r["n"][s] < A.MIN_N:
            notes.append(f"{label}: fewer than {A.MIN_N} usable records (ASSUMPTION: minimum "
                         f"{A.MIN_N}), so it is shown as \"{NOT_ENOUGH.lower()}\". Try "
                         "\"All types\", all projects, or another city.")
    if r["co_date"]["P50"] != U and r["method"] != "paired":
        notes.append(f"Only {r['n_paired']} records show both stages for the same project, so "
                     "the two stages were combined as if independent (ASSUMPTION). Treat the "
                     "plan-for date as rough.")
    sd = stage_summary(city, unit_cat, affordable, "ent_to_permit")["same_day_pct"]
    if isinstance(sd, (int, float)) and sd >= SAME_DAY_FLAG_PCT:
        notes.append(f"Caution: {sd:.0f}% of its approval → permit records give the same date "
                     "for both steps. That is probably how the city reports (INFERRED), not "
                     "real speed, so its approval → permit time is likely understated.")
    notes.append("Durations come from records that report both dates in the same row, so a "
                 "project that took several report years to permit can be missed. This leans "
                 "the figures toward faster projects.")
    return notes


def verdict(sel: list[str], res: dict[str, dict], cost: float | None) -> str:
    """One short paragraph: who is fastest, by how much, and what the extra wait costs."""
    known = [c for c in sel if res[c]["co_date"]["P50"] != U]
    if not known:
        return (f"None of the chosen cities reported enough projects to forecast "
                f"({NOT_ENOUGH.lower()}). Try \"All types\", all projects, or pick a city from "
                "the chart above.")
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
        parts.append(f"At {usd_md(cost)} a month, set aside "
                     f"**{usd_md((c0['P80'] - c0['P50']) * cost)}** in case {title(first)} runs "
                     "to its plan-for date.")
        for c in known[1:]:
            extra = (res[c]["cost"]["P50"] - c0["P50"]) * cost
            if extra >= 50:
                parts.append(f"The extra wait in {title(c)} costs about **{usd_md(extra)}** "
                             f"more than {title(first)}.")
    return " ".join(parts).replace(" \n\n ", "\n\n")


# ---------- app ----------

df = data()
cities = sorted(df["JURIS_NAME"].dropna().unique())
today = dt.date.today()

with st.sidebar:
    st.title("Permit Clock")
    st.caption("What Orange County cities promised about permitting, and how long permits "
               "really take. From the state's own housing reports.")
    page = st.radio("I want to know…", [PAGE_PROMISES, PAGE_TIMING], label_visibility="collapsed")
    st.divider()

# =====================================================================================
if page == PAGE_PROMISES:
    prog_all = programs(today)
    b_cities = sorted(set(prog_all["JURIS_NAME"]) | set(cities))
    with st.sidebar:
        city = st.selectbox("City", b_cities, index=b_cities.index("TUSTIN"), format_func=title)
    prog = prog_all[prog_all["JURIS_NAME"] == city]
    n_prog = len(prog)

    st.title(f"What did {title(city)} promise about permitting?")
    ui.lead(f"The permitting-related programs in {title(city)}'s 2025 housing element annual "
            "report, what the city said about each, and which are past the dates it set. "
            "From the state's own Table D; nothing here is sent to the city.")

    if not n_prog:
        st.info(f"No permitting-related programs found for {title(city)} in the 2025 Table D "
                "extract. Try another city.")
    else:
        status_word = prog["overdue"].map(STATUS_WORD)
        status_word[prog["status_bucket"] == "completed"] = "Done"
        counts = status_word.value_counts()
        n_over = int(counts.get("Overdue", 0))
        n_rec = int(counts.get("Recurring", 0))
        n_und = int(counts.get("No single target date", 0))
        hc = handcheck()

        # 1. Three tiles.
        t1, t2, t3 = st.columns(3)
        with t1, st.container(border=True):
            ui.stat("Promises overdue", f"{n_over} of {n_prog}",
                    "past the date the city set, not reported done" if n_over
                    else "none past the dates the city set",
                    tone="danger" if n_over else "success")
        with t2, st.container(border=True):
            ui.stat("Recurring or undated", f"{n_rec + n_und}",
                    f"{n_rec} annual or ongoing activities, {n_und} with no single target date")
        with t3, st.container(border=True):
            ui.stat("Reported done", f"{int(counts.get('Done', 0))}",
                    "completed, in the city's own words", tone="success")

        # Where it sits on permit times: one sentence, details on the other page.
        bits = []
        for s, label in STAGE_LABELS.items():
            sm, bq = stage_summary(city, None, False, s), best_q(s)
            if sm["P50"] == U:
                bits.append(f"{label.lower()}: {NOT_ENOUGH.lower()}")
            elif sm["P50"] == 0:
                bits.append(f"{label.lower()}: same-day reporting (not comparable)")
            elif bq == U:
                bits.append(f"{label.lower()}: typically {months(sm['P50'])}")
            else:
                gap = half(sm["P50"]) - half(bq)
                bits.append(f"{label.lower()}: typically {months(sm['P50'])}, "
                            + (f"{months(gap)} behind" if gap >= 0.25 else "at or ahead of")
                            + " the fastest quarter of OC cities")
        st.markdown(f"<p class='pc-note'>On permit times, {title(city)} reports {bits[0]}; "
                    f"{bits[1]}. All unit types, 2018–2025. Details on the "
                    f"\"{PAGE_TIMING}\" page.</p>", unsafe_allow_html=True)

        # 2. The promises, grouped by program.
        st.header("The promises")
        order = [s for s in STATUS_ORDER if s in counts.index]
        choice = st.radio("Show", ["All"] + [f"{s} ({counts[s]})" for s in order],
                          horizontal=True, label_visibility="collapsed", key="prog_filter")
        keep = pd.Series(True, index=prog.index) if choice == "All" else \
            status_word == choice.rsplit(" (", 1)[0]
        show = prog[keep]
        groups = A.program_groups(prog)
        method = prog["method"].iloc[0]
        if hc["n_checked"]:
            acc = (f"Of {hc['n_checked']} hand-checked labels, {hc['n_correct']} were right "
                   f"({100 * hc['n_correct'] / hc['n_checked']:.0f}%).")
        else:
            acc = (f"They are unverified: none of the {hc['n_rows']} sample rows in "
                   "data/tableD_handcheck.csv has been hand-checked yet.")
        st.caption("Grouped by program, most overdue first. Status and type labels were read "
                   "from the city's own text by "
                   + ("Claude Haiku (claude-haiku-5-5)" if method.startswith("claude")
                      else "a keyword match") + f". {acc} Target dates come from the city's "
                   "own wording where it gives one, otherwise from the report's date field; "
                   "annual or ongoing activities are never marked overdue.")
        RANK = {s: i for i, s in enumerate(STATUS_ORDER)}
        g_all = groups["group"]
        g_over = status_word.eq("Overdue").groupby(g_all).sum()
        g_first = prog["target"].groupby(g_all).min()
        g_rank = status_word.map(RANK).groupby(g_all).min()

        def target_text(i) -> str:
            t = prog.at[i, "target"]
            if pd.isna(t):
                return ("no single deadline" if prog.at[i, "overdue"] == "recurring"
                        else "no single date")
            src = " (city's own wording)" if prog.at[i, "target_source"] == "objective text" \
                else ""
            return f"target {date(t)}{src}"

        def row_html(i) -> str:
            word = status_word[i]
            return ui.row(ui.esc(A._clip(groups.at[i, "item"], 140)),
                          f"{word.lower()} · {target_text(i)} · city reports "
                          f"“{ui.esc(prog.at[i, 'status_bucket'])}”",
                          STATUS_TONE[word], done=(word == "Done"))

        if show.empty:
            st.info("No promises match this filter.")
        shown_groups = sorted(set(g_all[show.index]),
                              key=lambda g: (g_rank[g], -g_over[g],
                                             g_first[g] if pd.notna(g_first[g])
                                             else pd.Timestamp.max))
        for g in shown_groups:
            idx = sorted([i for i in show.index if g_all[i] == g],
                         key=lambda i: (RANK[status_word[i]], str(prog.at[i, "target"])))
            n_g = int((g_all == g).sum())
            count_text = (f"{n_g} promise{'s' if n_g > 1 else ''}"
                          + (f", {int(g_over[g])} overdue" if g_over[g] else ""))
            with st.container(border=True):
                st.markdown(ui.card_title(g, count_text) + "".join(row_html(i) for i in idx),
                            unsafe_allow_html=True)

        # 3. Look closer at one, then ask the city about it (never sent).
        st.header("Look closer at one")
        opts = list(show.index) if not show.empty else list(prog.index)
        opts.sort(key=lambda i: RANK[status_word[i]])  # overdue first, done last
        pick = st.selectbox("Promise", opts, key="draft_prog", label_visibility="collapsed",
                            format_func=lambda i: f"{status_word[i]} · "
                            f"{A._clip(groups.at[i, 'item'], 80)} ({A._clip(g_all[i], 50)})")
        p = prog.loc[pick]
        with st.container(border=True):
            st.markdown(ui.card_title(g_all[pick])
                        + ui.pill(status_word[pick], STATUS_TONE[status_word[pick]]) + " "
                        + ui.meta(ui.esc(target_text(pick)) + " · type "
                                  + ui.esc(p["category"][:1].upper() + p["category"][1:])
                                  + " · label unverified"), unsafe_allow_html=True)
            st.markdown(f"**The city's objective:** {p['PROGRAM_OBJECTIVE']}")
            st.markdown(f"**Status reported by the city:** {p['PROGRAM_STATUS']}")
            st.caption("Full program name: " + " ".join(str(p["PROGRAM_NAME"]).split())
                       + f" · status label \"{p['status_bucket']}\""
                       + (f" · report date field {p['ACCOMPLISHED_DT']}"
                          if isinstance(p["ACCOMPLISHED_DT"], str) else ""))

        open_cats = sorted(set(prog.loc[prog["status_bucket"] != "completed", "category"])
                           - {"other"})
        lines = []
        for c in open_cats:
            peers = A.peers_completed(prog_all, city, c)
            label = c[:1].upper() + c[1:]  # display only: "fees" -> "Fees"
            lines.append(f"- **{label}:** " + (", ".join(title(x) for x in peers) if peers
                                                else "none reported completed"))
        if lines:
            with st.expander("Other OC cities that report finishing the same kind of promise"):
                st.markdown("\n".join(lines))
                st.caption("Self-reported by each city. Finishing a program does not show it "
                           "made that city faster.")

        st.subheader("Ask the city about it")
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

    with st.expander("Sources and method"):
        src = sources()
        td = src["tables"]["oc_apr_tableD.csv"]
        st.markdown(
            f"- **Promises:** {td['name']}, {src['publisher']}. Resource `{td['resource_id']}`, "
            f"2025 report year, keyword-filtered to permitting topics, pulled "
            f"{src['pulled_at_utc'][:10]}. [API link]({td['url']})\n"
            "- **Target date:** a date the city wrote into its own objective (\"no later than "
            "October 2024\" → Oct 2024) comes first. Otherwise the report's date field is "
            "used when it is a specific date. A date in 2029 or later is taken as the end of "
            "the housing-element cycle, and the report year's December 31 as a report date, "
            "not a promise (ASSUMPTION): those show \"no single target date\".\n"
            "- **Recurring:** objectives that describe a repeating activity (\"annually\", "
            "\"per year\", \"ongoing\", \"continue to\") have no single deadline and are never "
            "marked overdue.\n"
            "- **Overdue** = target before today and status not \"completed\". Status and type "
            "labels can be wrong: the city's own words are shown for every promise.\n"
            f"- **Permit times:** APR Table A2 (see \"{PAGE_TIMING}\"). Fastest quarter = 25th "
            f"percentile of city medians among cities with n ≥ {A.MIN_N}, leaving out same-day "
            "cities (ASSUMPTION).")
        st.caption("Association, not cause: a promise's status does not show it made a city "
                   "faster or slower. Nothing here says a city broke a law.")

# =====================================================================================
else:
    with st.sidebar:
        unit_cat = st.selectbox("Unit type", list(UNIT_LABELS), format_func=UNIT_LABELS.get)
        affordable = st.radio("Projects", ["All projects", "Deed-restricted affordable only"],
                              help="Deed-restricted = the permit row reports units restricted "
                                   "to very-low, low or moderate incomes. Few cities report "
                                   "enough of these, so most cells will say not enough data.") \
            == "Deed-restricted affordable only"
        start = st.date_input("Planning approval date", value=today,
                              help="The day the city approves the project (the entitlement). "
                                   "The forecast starts here.")
        deadline = st.date_input("A deadline at risk (optional)", value=None,
                                 help="A funding expenditure deadline, an award expiry, a rate "
                                      "lock. Each city's dates are checked against it.")
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

    st.title(PAGE_TIMING)
    ui.lead(f"For {scope_phrase(unit_cat, affordable)}, approved on {start:%b %d, %Y}: the time "
            "cities reported from planning approval to the building permit and on to move-in. "
            "It does not include rezoning or the entitlement process itself, which are often "
            "the longest part. Hover a bar for dates and sample size.")

    # 1. Every city, ranked.
    path = st.radio("Show", list(PATH_LABELS), format_func=PATH_LABELS.get, horizontal=True,
                    label_visibility="collapsed")
    tbl = rank_table(unit_cat, affordable, start.isoformat(), path)
    highlight = {c: ui.SERIES[i % 3] for i, c in enumerate(sel)}
    fig = rank_chart(tbl, highlight, path)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        rough = tbl[tbl["rough"] & tbl["likely"].notna()]
        st.caption("Solid bar = likely (half of past projects done by then). Faded bar = plan "
                   f"for (8 in 10 done by then). Cities with fewer than {A.MIN_N} usable "
                   "records (ASSUMPTION) are listed without a bar."
                   + (" * = stages combined as if independent because few records show both "
                      "(ASSUMPTION); treat as rough." if len(rough) else ""), help=LIKELY_HELP)
    else:
        st.info(f"No city reported {A.MIN_N} or more projects on this path for "
                f"{scope_phrase(unit_cat, affordable)}. Try \"All types\" or all projects.")

    # 2. The shortlist.
    st.header("Your shortlist")
    if not sel:
        st.info("Pick up to three cities in the sidebar to compare them side by side.")
    else:
        res = {c: mc(c, unit_cat, affordable, start.isoformat()) for c in sel}
        st.markdown(verdict(sel, res, cost))
        tl = timeline_chart(sel, res, start)
        if tl is not None:
            st.plotly_chart(tl, use_container_width=True)
        known = [c for c in sel if res[c]["co_date"]["P50"] != U]
        fastest = min(known, key=lambda c: res[c]["co_date"]["P50"]) if known else None
        cols = st.columns(len(sel))
        for i, c in enumerate(sel):
            r = res[c]
            with cols[i], st.container(border=True):
                st.markdown(f"<div class='pc-card-title'><span class='pc-dot' "
                            f"style='background:{ui.SERIES[i % 3]}'></span>{title(c)}</div>",
                            unsafe_allow_html=True)
                unknown = r["co_date"]["P50"] == U
                ui.stat("Move-in, likely", date(r["co_date"]["P50"]), unknown=unknown)
                ui.stat("Move-in, plan for", date(r["co_date"]["P80"]), unknown=unknown)
                if deadline and not unknown:
                    p50 = pd.Timestamp(r["co_date"]["P50"])
                    p80 = pd.Timestamp(r["co_date"]["P80"])
                    dl = pd.Timestamp(deadline)
                    if p50 > dl:
                        ui.stat("Your deadline", f"{deadline:%b %Y}",
                                "even the likely move-in date is after it", tone="danger")
                    elif p80 > dl:
                        ui.stat("Your deadline", f"{deadline:%b %Y}",
                                "likely date is before it; plan-for date is not",
                                tone="warning")
                    else:
                        ui.stat("Your deadline", f"{deadline:%b %Y}",
                                "both dates are before it", tone="success")
                if cost and not unknown:
                    ui.stat("Contingency to set aside",
                            usd((r["cost"]["P80"] - r["cost"]["P50"]) * cost),
                            "extra cost if it runs to the plan-for date")
                    if fastest and c != fastest:
                        extra = (r["cost"]["P50"] - res[fastest]["cost"]["P50"]) * cost
                        ui.stat(f"Extra wait vs {title(fastest)}", usd(extra),
                                "at the likely dates", tone="danger" if extra >= 50 else None)
                for s, label in STAGE_LABELS.items():
                    sm = stage_summary(c, unit_cat, affordable, s)
                    st.caption(f"{label}: likely {months(sm['P50'])}"
                               + (f", plan for {months(sm['P80'])} (n={sm['n']})"
                                  if sm["P50"] != U else f" (n={sm['n']})"))
                with st.expander("How we got this"):
                    for note in city_notes(c, unit_cat, affordable, r):
                        st.markdown(f"- {note}")
        if start < today:
            st.caption("Your approval date is in the past; dates are still counted from it.")

        with st.expander("Go deeper: is it getting faster?"):
            stage_t = st.radio("Stage", list(STAGE_LABELS), format_func=STAGE_LABELS.get,
                               horizontal=True, label_visibility="collapsed", key="trend_stage",
                               index=1)
            st.plotly_chart(trend_chart(sel, affordable, stage_t), use_container_width=True)
            st.caption("Typical (median) months by the year the project was reported. A city's "
                       f"line has a gap where it reported fewer than {A.MIN_N} projects that "
                       "year (ASSUMPTION). Reports, not reality: cities that report approval "
                       "and permit on the same day look fast.")

    with st.expander("Sources and method"):
        src = sources()
        t = src["tables"]["oc_apr_a2.csv"]
        st.markdown(
            f"- **Data:** {t['name']}, {src['publisher']}. Resource `{t['resource_id']}`, "
            f"filter {t['filter']}, {t['rows']:,} rows, pulled {src['pulled_at_utc'][:10]}. "
            f"[API link]({t['url']}). Addresses, names and coordinates were dropped.\n"
            f"- {TERMS}\n"
            "- Durations use only records that report both dates in the same row. A project "
            "that took several report years to permit can be missed, which leans every figure "
            "toward faster projects. Cities with fewer than "
            f"{A.MIN_N} such records show \"{NOT_ENOUGH.lower()}\" (ASSUMPTION).\n"
            "- Deed-restricted affordable = the permit row reports units in the BP_*_DR "
            "columns (very-low, low or moderate income, deed-restricted).\n"
            f"- Forecast: {A.N_DRAWS:,} random draws from that city's past projects, starting "
            f"from your approval date. Where fewer than {A.MIN_N} records hold both stages, "
            "the stages are drawn separately (ASSUMPTION: independent) and marked *.\n"
            "- Likely = the middle outcome (50th percentile). Plan for = the 80th percentile.")
        ana = stage_summary("ANAHEIM", None, False, "ent_to_permit")
        ful = stage_summary("FULLERTON", None, False, "ent_to_permit")
        hb = stage_summary("HUNTINGTON BEACH", None, False, "permit_to_co")
        org = stage_summary("ORANGE", "ADU", False, "permit_to_co")
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
            "source. Dollar defaults are a made-up example (ASSUMPTION). Costs shown are "
            "differences (plan-for minus likely; this city minus the fastest on your list), "
            "not the whole carrying cost of a project.")
        st.caption("Association, not cause: these numbers describe past reports and do not "
                   "explain why a city is faster or slower.")

st.caption("Prototype. Not legal, financial or lending advice. Check decisions with a professional.")
