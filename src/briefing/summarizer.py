import os
from typing import Dict, Any, List


def generate_brief(signals: List[Dict[str, Any]], news: List[Dict[str, Any]]) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        return _template_brief(signals, news)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = _build_prompt(signals, news)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        if response.text:
            return response.text
        return _template_brief(signals, news)
    except Exception as e:
        print(f"Gemini error: {e}. Falling back to template.")
        return _template_brief(signals, news)


def _build_prompt(signals: List[Dict[str, Any]], news: List[Dict[str, Any]]) -> str:
    lines = ["You are a professional market intelligence analyst for a swing trader.", ""]

    lines.append("Trading signals:")
    for s in signals:
        lines.append(f"- {s['symbol']}: {s['signal']} ({s['rationale']})")

    lines.append("")
    lines.append("Latest market news headlines:")
    for n in news[:15]:
        lines.append(f"- [{n.get('source', 'unknown')}] {n.get('title', '')}")

    lines.append("")
    lines.append(
        "Generate a concise, trader-focused market brief. "
        "Highlight key catalysts, sentiment, and actionable takeaways. "
        "Keep it under 300 words. Format in Markdown."
    )
    return "\n".join(lines)


def _template_brief(signals: List[Dict[str, Any]], news: List[Dict[str, Any]]) -> str:
    lines = ["### Market Briefing", "", "**Signals:**"]
    for s in signals:
        lines.append(f"- {s['symbol']}: {s['signal']} ({s['rationale']})")

    if news:
        lines.append("")
        lines.append("**Top Headlines:**")
        for n in news[:10]:
            lines.append(f"- {n.get('title', '')} *{n.get('source', '')}*")

    return "\n".join(lines)
