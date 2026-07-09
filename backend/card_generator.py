"""
Server-side verdict card generator — produces SVG share cards.
Zero external dependencies: pure string-based SVG generation.
"""
import html
import textwrap


def _truncate(text: str, max_len: int = 120) -> str:
    """Truncate text to max_len characters with ellipsis."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rsplit(" ", 1)[0] + "…"


def generate_verdict_card(
    claim_text: str,
    verdict: str,
    confidence: float,
    analysis: str = "",
) -> str:
    """Generate an SVG verdict card for social sharing.
    
    Returns SVG string (Content-Type: image/svg+xml).
    Card dimensions: 1200×630 (standard OG image size).
    """
    # Determine colors based on verdict
    if verdict == "LIKELY_FALSE":
        accent = "#EF4444"       # red
        accent_bg = "#3B1111"
        verdict_label = "LIKELY FALSE"
        icon_path = "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z M12 15.75h.007v.008H12v-.008z"
    elif verdict == "LIKELY_TRUE":
        accent = "#4ADE80"       # green
        accent_bg = "#0D2818"
        verdict_label = "LIKELY TRUE"
        icon_path = "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    else:
        accent = "#F59E0B"       # amber
        accent_bg = "#2D1F04"
        verdict_label = verdict.replace("_", " ") if verdict else "MIXED"
        icon_path = "M12 9v3.75m9.303 3.376c-.866 1.5-2.217 3.374-3.948 3.374H6.645c-1.73 0-2.813-1.874-1.948-3.374L10.051 3.378c.866-1.5 3.032-1.5 3.898 0l5.354 9.748z M12 15.75h.007v.008H12v-.008z"

    # Safe text for SVG
    safe_claim = html.escape(_truncate(claim_text, 140))
    safe_analysis = html.escape(_truncate(analysis, 200))
    conf_str = f"{confidence:.0f}"
    
    # Wrap claim text into lines
    claim_lines = textwrap.wrap(safe_claim, width=55)[:3]
    claim_svg = ""
    for i, line in enumerate(claim_lines):
        y = 340 + i * 32
        claim_svg += f'<text x="80" y="{y}" fill="#D1D5DB" font-size="22" font-family="system-ui, -apple-system, sans-serif" font-style="italic">"{line}"</text>\n'
    
    # Wrap analysis into lines
    analysis_lines = textwrap.wrap(safe_analysis, width=70)[:3]
    analysis_svg = ""
    for i, line in enumerate(analysis_lines):
        y = 460 + i * 26
        analysis_svg += f'<text x="80" y="{y}" fill="#9CA3AF" font-size="17" font-family="system-ui, -apple-system, sans-serif">{line}</text>\n'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <!-- Background -->
  <rect width="1200" height="630" fill="#0B0E15" rx="0"/>
  
  <!-- Top accent bar -->
  <rect x="0" y="0" width="1200" height="5" fill="{accent}"/>
  
  <!-- Logo area -->
  <rect x="60" y="40" width="44" height="44" rx="10" fill="#7C3AED"/>
  <text x="72" y="72" fill="white" font-size="22" font-weight="bold" font-family="system-ui, sans-serif">V</text>
  <text x="120" y="72" fill="white" font-size="26" font-weight="800" font-family="system-ui, sans-serif" letter-spacing="1">VERIF<tspan fill="#7C3AED">AI</tspan></text>
  
  <!-- Divider -->
  <line x1="60" y1="110" x2="1140" y2="110" stroke="#1F2937" stroke-width="1"/>
  
  <!-- Verdict section -->
  <rect x="60" y="140" width="1080" height="120" rx="16" fill="{accent_bg}" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.4"/>
  
  <!-- Verdict icon circle -->
  <circle cx="130" cy="200" r="30" fill="{accent}" fill-opacity="0.15" stroke="{accent}" stroke-width="2"/>
  <text x="118" y="208" fill="{accent}" font-size="24" font-weight="bold" font-family="system-ui, sans-serif">{conf_str}</text>
  
  <!-- Verdict text -->
  <text x="180" y="190" fill="{accent}" font-size="36" font-weight="800" font-family="system-ui, sans-serif" letter-spacing="2">{verdict_label}</text>
  <text x="180" y="225" fill="#9CA3AF" font-size="18" font-family="system-ui, sans-serif">{conf_str}% confidence · AI-powered fact check</text>
  
  <!-- Claim text -->
  <text x="80" y="310" fill="#6B7280" font-size="14" font-weight="600" font-family="system-ui, sans-serif" letter-spacing="2">THE CLAIM</text>
  {claim_svg}
  
  <!-- Analysis -->
  <text x="80" y="435" fill="#6B7280" font-size="14" font-weight="600" font-family="system-ui, sans-serif" letter-spacing="2">AI ANALYSIS</text>
  {analysis_svg}
  
  <!-- Bottom bar -->
  <rect x="0" y="570" width="1200" height="60" fill="#111827"/>
  <text x="80" y="608" fill="#6B7280" font-size="16" font-family="system-ui, sans-serif">Verified by VerifAI · fake-news-detector-8djq.onrender.com</text>
  <text x="1020" y="608" fill="{accent}" font-size="16" font-weight="600" font-family="system-ui, sans-serif">Check Now →</text>
</svg>'''
    
    return svg
