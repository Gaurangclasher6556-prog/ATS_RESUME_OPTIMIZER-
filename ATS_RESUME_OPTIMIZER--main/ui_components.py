"""
ui_components.py — Reusable visual components for the Career Forge UI.

All components are pure HTML/SVG strings rendered via st.markdown(..., unsafe_allow_html=True),
so they add zero dependencies and theme consistently with the app's design system.
"""

from __future__ import annotations

import html
from typing import List

# Brand palette
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"
SLATE = "#475569"


def _color_for(score: float) -> str:
    if score >= 75:
        return GREEN
    if score >= 55:
        return AMBER
    return RED


def score_gauge(score: int, grade: str = "") -> str:
    """Return an SVG semicircular gauge for an overall 0–100 ATS score."""
    score = max(0, min(100, int(score)))
    color = _color_for(score)
    # Semicircle arc: radius 90, circumference of half = pi*r ≈ 282.74
    import math
    r = 90
    circ = math.pi * r
    dash = circ * (score / 100.0)
    return f"""
<div style="text-align:center;padding:0.5rem 0 0.25rem;">
  <svg width="240" height="140" viewBox="0 0 240 140">
    <path d="M20,120 A100,100 0 0,1 220,120" fill="none"
          stroke="#e2e8f0" stroke-width="18" stroke-linecap="round"
          transform="translate(0,0)"/>
    <path d="M20,120 A100,100 0 0,1 220,120" fill="none"
          stroke="{color}" stroke-width="18" stroke-linecap="round"
          stroke-dasharray="{dash:.1f} 999"/>
    <text x="120" y="105" text-anchor="middle" font-size="44"
          font-weight="700" fill="{color}" font-family="Inter,sans-serif">{score}</text>
    <text x="120" y="128" text-anchor="middle" font-size="13"
          fill="#64748b" font-family="Inter,sans-serif">ATS Match Score</text>
  </svg>
  <div style="color:{color};font-weight:600;font-size:0.95rem;margin-top:-6px;">{html.escape(grade)}</div>
</div>
"""


def component_bars(components: list) -> str:
    """Render a horizontal bar for each scoring component."""
    def field(c, key, default=""):
        return c.get(key, default) if isinstance(c, dict) else getattr(c, key, default)

    rows = []
    for c in components:
        name = field(c, "name")
        weight = field(c, "weight", 0)
        detail = field(c, "detail")
        score = float(field(c, "score", 0))
        color = _color_for(score)
        rows.append(f"""
        <div style="margin-bottom:0.85rem;">
          <div style="display:flex;justify-content:space-between;font-size:0.85rem;
                      margin-bottom:3px;">
            <span style="font-weight:600;color:#1e293b;">{html.escape(name)}
              <span style="color:#94a3b8;font-weight:400;">· {int(weight*100)}% weight</span></span>
            <span style="font-weight:700;color:{color};">{score:.0f}</span>
          </div>
          <div style="background:#eef2f7;border-radius:6px;height:9px;overflow:hidden;">
            <div style="width:{score:.0f}%;height:100%;background:{color};border-radius:6px;"></div>
          </div>
          <div style="font-size:0.76rem;color:#64748b;margin-top:3px;">{html.escape(detail)}</div>
        </div>
        """)
    return f'<div style="padding:0.5rem 0;">{"".join(rows)}</div>'


def keyword_chips(matched: List[str], missing: List[str], limit: int = 18) -> str:
    """Render matched (green) and missing (red) keyword chips."""
    def chips(items, bg, fg, border):
        return "".join(
            f'<span style="display:inline-block;background:{bg};color:{fg};'
            f'border:1px solid {border};border-radius:14px;padding:3px 10px;'
            f'font-size:0.78rem;margin:3px 4px 3px 0;">{html.escape(str(i))}</span>'
            for i in items[:limit]
        )
    out = []
    if matched:
        out.append('<div style="margin-bottom:0.6rem;"><b style="font-size:0.85rem;color:#166534;">'
                   f'✅ Matched ({len(matched)})</b><br>'
                   + chips(matched, "rgba(22,163,74,0.10)", "#166534", "rgba(22,163,74,0.3)")
                   + '</div>')
    if missing:
        out.append('<div><b style="font-size:0.85rem;color:#991b1b;">'
                   f'❌ Missing ({len(missing)})</b><br>'
                   + chips(missing, "rgba(220,38,38,0.08)", "#991b1b", "rgba(220,38,38,0.25)")
                   + '</div>')
    return "".join(out)


def delta_badge(before: int, after: int) -> str:
    """Render a before → after score delta badge."""
    delta = after - before
    sign = "+" if delta >= 0 else ""
    color = GREEN if delta > 0 else (SLATE if delta == 0 else RED)
    return f"""
<div style="display:flex;align-items:center;gap:1rem;justify-content:center;
            background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
            padding:0.9rem 1.2rem;margin:0.5rem 0;">
  <div style="text-align:center;">
    <div style="font-size:1.6rem;font-weight:700;color:#64748b;">{before}</div>
    <div style="font-size:0.72rem;color:#94a3b8;">BEFORE</div>
  </div>
  <div style="font-size:1.4rem;color:{color};">→</div>
  <div style="text-align:center;">
    <div style="font-size:1.6rem;font-weight:700;color:{_color_for(after)};">{after}</div>
    <div style="font-size:0.72rem;color:#94a3b8;">AFTER</div>
  </div>
  <div style="background:{color};color:white;border-radius:20px;padding:5px 14px;
              font-weight:700;font-size:0.95rem;">{sign}{delta} pts</div>
</div>
"""
