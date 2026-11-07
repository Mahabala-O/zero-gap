"""Drafted (never sent) requests that quote a city's own Table D program text.

Prototype only. Nothing here sends anything. The live draft calls claude-haiku-5-5 only when a
person clicks a button and an API key is set; otherwise the static template is used.
"""
from __future__ import annotations

MODEL = "claude-haiku-5-5"
UNKNOWN = "unknown"

SYSTEM = (
    "You draft short, polite notes from a housing nonprofit or resident to city housing staff. "
    "Use only the program text given. Quote the program name, objective, target date and the "
    "city's own status text exactly. Do not add any number, date, fee, law, statute or name "
    "that is not in the text. Do not say the city violated a law or caused a delay. Ask what "
    "the current status and next step are, and whether there is an updated timeline. "
    "Under 170 words. Leave [Your name] and [Organization] as placeholders. No subject line."
)


def _field(row: dict, key: str) -> str:
    v = row.get(key)
    if v is None or (isinstance(v, float) and v != v) or str(v).strip() == "":
        return UNKNOWN
    # Same words, one line: line breaks and runs of spaces in the city's text split the
    # quoted bullet over several lines in the draft (e.g. Tustin's "6th HE Cycle  1.7 ...\n\na.").
    return " ".join(str(v).split())


def program_text(city: str, row: dict) -> str:
    """The only facts a draft may use, taken from the city's 2025 APR Table D row."""
    return (f"City: {city}\n"
            f"Program name: {_field(row, 'PROGRAM_NAME')}\n"
            f"Objective: {_field(row, 'PROGRAM_OBJECTIVE')}\n"
            f"Target date (as reported): {_field(row, 'ACCOMPLISHED_DT')}\n"
            f"City's own status text (2025 annual progress report): "
            f"{_field(row, 'PROGRAM_STATUS')}")


def static_template(city: str, row: dict) -> str:
    """Draft with no API call. Every fact is quoted from the row; missing ones say unknown."""
    return (
        f"Dear {city} housing staff,\n\n"
        "Thank you for your work on the housing element. In the city's 2025 annual progress "
        "report (HCD APR Table D), the city lists this program:\n\n"
        f"- Program: \"{_field(row, 'PROGRAM_NAME')}\"\n"
        f"- Objective: \"{_field(row, 'PROGRAM_OBJECTIVE')}\"\n"
        f"- Target date: {_field(row, 'ACCOMPLISHED_DT')}\n"
        f"- Status reported by the city: \"{_field(row, 'PROGRAM_STATUS')}\"\n\n"
        "Could you share the current status, the next step, and whether there is an updated "
        "timeline? It would help us plan affordable homes in the city.\n\n"
        "Thank you,\n[Your name]\n[Organization]"
    )


def claude_draft(city: str, row: dict, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL, max_tokens=600, system=SYSTEM,
        messages=[{"role": "user", "content": program_text(city, row)}])
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
