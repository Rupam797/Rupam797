#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime

PALETTE = [
    "#161b22",  # Level 0: none
    "#0e4429",  # Level 1: low
    "#006d32",  # Level 2: medium-low
    "#26a641",  # Level 3: medium
    "#39d353",  # Level 4: high
    "#69f0a0"   # Level 5: brightest / neon top end
]

def get_color(count):
    if count == 0:
        return PALETTE[0]
    elif count <= 2:
        return PALETTE[1]
    elif count <= 5:
        return PALETTE[2]
    elif count <= 9:
        return PALETTE[3]
    elif count <= 15:
        return PALETTE[4]
    else:
        return PALETTE[5]

def render_heatmap_svg(json_path=None, output_path=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not json_path:
        json_path = os.path.join(base_dir, "data", "contributions.json")
    if not output_path:
        output_path = os.path.join(base_dir, "contrib-heatmap.svg")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Contributions JSON not found at {json_path}. Run fetch_contributions.py first.")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    days = data.get("days", [])
    total_contributions = data.get("total_contributions", sum(d.get("count", 0) for d in days))

    # Group days into week columns (Sun=0 to Sat=6)
    weeks = []
    current_week = [None] * 7

    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        row = (dt.weekday() + 1) % 7  # Sunday=0, Monday=1, ..., Saturday=6

        if row == 0 and any(item is not None for item in current_week):
            weeks.append(current_week)
            current_week = [None] * 7

        current_week[row] = d

    if any(item is not None for item in current_week):
        weeks.append(current_week)

    # Keep exactly 53 weeks
    if len(weeks) > 53:
        weeks = weeks[-53:]

    start_x = 34
    start_y = 24
    box_size = 13
    step = 16
    width = 888
    height = 158

    # Collect Month Labels based on first day of each week column
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_labels = []
    last_month = -1

    for col_idx, week in enumerate(weeks):
        # Pick the first valid day in the week
        valid_day = next((d for d in week if d is not None), None)
        if valid_day:
            dt = datetime.strptime(valid_day["date"], "%Y-%m-%d")
            m = dt.month
            if m != last_month:
                x_pos = start_x + col_idx * step
                month_labels.append((month_names[m - 1], x_pos))
                last_month = m

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
    )
    svg_parts.append("""<style>
  text.lbl { fill:#7d8590; font-size:13px; font-weight:600; }
  text.total { fill:#e6edf3; font-size:15px; font-weight:700; }
  .c { transform-box:fill-box; transform-origin:center; opacity:0; animation:pop 0.55s ease-out both; }
  .g { animation:pop 0.55s ease-out both, flash 0.7000000000000001s ease-out both; }
  @keyframes pop { 0%{opacity:0;transform:scale(.2)} 60%{opacity:1;transform:scale(1.1)} 100%{opacity:1;transform:scale(1)} }
  @keyframes flash { 0%{filter:brightness(2.4)} 45%{filter:brightness(2.4)} 100%{filter:brightness(1)} }
  @media (prefers-reduced-motion: reduce) { .c { opacity:1 !important; animation:none !important; } }
</style>""")

    svg_parts.append(f'<rect width="{width}" height="{height}" fill="none"/>')

    # Month labels
    for name, x_pos in month_labels:
        svg_parts.append(f'<text class="lbl" x="{x_pos}" y="16">{name}</text>')

    # Day labels
    svg_parts.append('<text class="lbl" x="2" y="51">Mon</text>')
    svg_parts.append('<text class="lbl" x="2" y="83">Wed</text>')
    svg_parts.append('<text class="lbl" x="2" y="115">Fri</text>')

    # Day Grid
    for col_idx, week in enumerate(weeks):
        for row_idx, day in enumerate(week):
            if day is None:
                continue

            x = start_x + col_idx * step
            y = start_y + row_idx * step
            count = day.get("count", 0)
            date_str = day.get("date", "")
            color = get_color(count)

            cls = "c g" if count > 0 else "c e"
            delay = round(col_idx * 0.065 + row_idx * 0.035714, 3)

            tooltip = f'{count} contribution{"s" if count != 1 else ""} on {date_str}'

            svg_parts.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{box_size}" height="{box_size}" rx="2.5" '
                f'fill="{color}" style="animation-delay:{delay}s"><title>{tooltip}</title></rect>'
            )

    # Footer total text
    total_text = f"{total_contributions:,} contributions in the last year"
    svg_parts.append(f'<text class="total" x="34" y="152">{total_text}</text>')

    svg_parts.append('</svg>')

    svg_content = "".join(svg_parts)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    # Also save copy in data/contrib-heatmap.svg and portfolio1/public if available
    alt_data_path = os.path.join(base_dir, "data", "contrib-heatmap.svg")
    with open(alt_data_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    public_dir = os.path.join(base_dir, "portfolio1", "public")
    if os.path.exists(public_dir):
        pub_svg_path = os.path.join(public_dir, "contrib-heatmap.svg")
        with open(pub_svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    print(f"Successfully generated heatmap SVG at {output_path}")

if __name__ == "__main__":
    json_p = sys.argv[1] if len(sys.argv) > 1 else None
    out_p = sys.argv[2] if len(sys.argv) > 2 else None
    render_heatmap_svg(json_p, out_p)
