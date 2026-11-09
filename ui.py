"""Permit Clock design system: tokens, CSS and small helpers. See docs/design-guidelines.md.

Everything visual goes through here so both pages look the same. Helpers return HTML strings
for st.markdown(..., unsafe_allow_html=True) or draw directly.
"""
from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

TOKENS = {
    "text": "#0A2540", "text2": "#425466", "muted": "#697386", "border": "#E3E8EE",
    "surface": "#F6F9FC", "accent": "#635BFF", "accent_soft": "#E0DEFF", "grey_bar": "#CFD7DF",
}
SERIES = ["#635BFF", "#0A2540", "#00A3BF"]  # compared items, in order, same everywhere
STATUS = {  # tone: (text color, soft background)
    "success": ("#228403", "#D7F7C2"),
    "warning": ("#BB5504", "#FCEDB9"),
    "danger": ("#CD3D64", "#FFE7F2"),
    "neutral": ("#545969", "#EBEEF1"),
}
FONT = ('-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", '
        'Arial, sans-serif')

_CSS = f"""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .stMarkdown,
[data-testid="stMarkdownContainer"] p, [data-testid="stWidgetLabel"] p, button, input, select {{
  font-family: {FONT};
  color: {TOKENS['text']};
}}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stSidebar"] {{
  background: {TOKENS['surface']}; border-right: 1px solid {TOKENS['border']};
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: {TOKENS['text2']}; }}
.block-container {{ padding-top: 2.5rem; max-width: 1100px; }}
h1, h2, h3 {{ color: {TOKENS['text']}; font-weight: 600; letter-spacing: -0.01em; }}
[data-testid="stHeadingWithActionElements"] h1 {{ font-size: 28px; padding-bottom: 4px; }}
[data-testid="stHeadingWithActionElements"] h2 {{ font-size: 20px; padding: 32px 0 8px; }}
[data-testid="stHeadingWithActionElements"] h3 {{ font-size: 16px; padding: 16px 0 4px; }}
[data-testid="stMarkdownContainer"] p {{ font-size: 15px; line-height: 1.5; }}
[data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] {{
  color: {TOKENS['muted']} !important; font-size: 13px !important; line-height: 1.45;
}}
/* Streamlit's bordered containers: recolor the border it draws, leave other blocks alone. */
[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {{
  border-color: {TOKENS['border']} !important; border-radius: 8px !important;
  padding: 16px 20px !important;
}}
[data-testid="stExpander"] details {{ border: 1px solid {TOKENS['border']}; border-radius: 8px; }}
[data-testid="stExpander"] summary p {{ color: {TOKENS['text2']}; font-size: 14px; }}
hr {{ border-color: {TOKENS['border']}; }}
[data-testid="stTextArea"] textarea {{ font-family: {FONT}; font-size: 14px; }}
.pc-lead {{ color: {TOKENS['text2']}; font-size: 16px; line-height: 1.5; margin: 0 0 20px; }}
.pc-eyebrow {{
  color: {TOKENS['muted']}; font-size: 12px; font-weight: 600; letter-spacing: .04em;
  text-transform: uppercase; margin-bottom: 4px;
}}
.pc-stat {{ padding: 4px 0 12px; }}
.pc-stat .pc-value {{
  font-size: 28px; font-weight: 600; line-height: 1.15; font-variant-numeric: tabular-nums;
}}
.pc-stat .pc-value.pc-unknown {{ color: {TOKENS['muted']}; font-size: 20px; }}
.pc-stat .pc-sub {{ font-size: 13px; margin-top: 6px; color: {TOKENS['muted']}; }}
.pc-card-title {{ font-size: 16px; font-weight: 600; margin-bottom: 6px; }}
.pc-card-title .pc-m {{ font-weight: 400; }}
.pc-row {{ padding: 3px 0 3px 14px; line-height: 1.5; font-size: 15px; }}
.pc-row.pc-done, .pc-row.pc-done .pc-m {{ color: {TOKENS['muted']}; }}
.pc-m {{ color: {TOKENS['muted']}; font-size: 13px; }}
.pc-pill {{
  display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px;
  font-weight: 600; vertical-align: middle;
}}
.pc-dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  margin-right: 6px; vertical-align: 0; }}
.pc-note {{ color: {TOKENS['muted']}; font-size: 13px; line-height: 1.45; margin: 6px 0 0; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def esc(t) -> str:
    return html.escape(str(t), quote=False)


def lead(text: str) -> None:
    """The one sentence under a page title: what the page shows and from what data."""
    st.markdown(f"<p class='pc-lead'>{text}</p>", unsafe_allow_html=True)


def eyebrow(text: str) -> str:
    return f"<div class='pc-eyebrow'>{esc(text)}</div>"


def stat(label: str, value: str, sub: str | None = None, tone: str | None = None,
         unknown: bool = False) -> None:
    """A stat tile: eyebrow label, big number, one muted or toned line below."""
    cls = "pc-value pc-unknown" if unknown else "pc-value"
    color = STATUS[tone][0] if tone else TOKENS["muted"]
    sub_html = f"<div class='pc-sub' style='color:{color}'>{esc(sub)}</div>" if sub else ""
    st.markdown(f"<div class='pc-stat'>{eyebrow(label)}<div class='{cls}'>{esc(value)}</div>"
                f"{sub_html}</div>", unsafe_allow_html=True)


def dot(tone: str) -> str:
    return f"<span class='pc-dot' style='background:{STATUS[tone][0]}'></span>"


def pill(text: str, tone: str) -> str:
    fg, bg = STATUS[tone]
    return f"<span class='pc-pill' style='color:{fg};background:{bg}'>{esc(text)}</span>"


def meta(text: str) -> str:
    return f"<span class='pc-m'>{text}</span>"


def card_title(title: str, count_text: str | None = None) -> str:
    extra = f" <span class='pc-m'>· {esc(count_text)}</span>" if count_text else ""
    return f"<div class='pc-card-title'>{esc(title)}{extra}</div>"


def row(body: str, metadata: str, tone: str, done: bool = False) -> str:
    cls = "pc-row pc-done" if done else "pc-row"
    return f"<div class='{cls}'>{dot(tone)}{body} {meta('· ' + metadata)}</div>"


def chart(fig: go.Figure, height: int) -> go.Figure:
    """Apply the chart style: transparent, horizontal gridlines only, muted axes."""
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TOKENS["text2"], size=13),
        margin=dict(l=8, r=8, t=8, b=8), hoverlabel=dict(font=dict(family=FONT)),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=12, color=TOKENS["muted"])),
    )
    fig.update_xaxes(showgrid=True, gridcolor=TOKENS["border"], zeroline=False,
                     linecolor=TOKENS["border"], tickfont=dict(color=TOKENS["muted"], size=12),
                     title_font=dict(size=12, color=TOKENS["muted"]))
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color=TOKENS["text2"],
                                                                   size=12),
                     title_font=dict(size=12, color=TOKENS["muted"]))
    return fig
