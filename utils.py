from typing import Any, Dict, List, Tuple, Optional
import math
import random
import matplotlib.pyplot as plt
from matplotlib import patches

DEFAULT_NON_STRAIGHT_UNITS = 60


def _segment_units(seg: Dict[str, Any]) -> int:
    if "units" in seg:
        return int(seg["units"])
    t = seg.get("type")
    if t == "straight":
        return int(max(5, min(200, int(seg.get("length", 80)))))
    return DEFAULT_NON_STRAIGHT_UNITS


def track_total_units(track: Dict[str, Any]) -> int:
    return sum(_segment_units(s) for s in track.get("segments", []))


def get_current_segment_index(position: float, track: Dict[str, Any]) -> int:
    segs = track.get("segments", [])
    cumulative = 0
    for i, seg in enumerate(segs):
        cumulative += _segment_units(seg)
        if position < cumulative:
            return i
    return max(0, len(segs) - 1)


def calculate_progress(position: float, track: Dict[str, Any]) -> float:
    total = track_total_units(track)
    if total == 0:
        return 0.0
    return min(1.0, position / total)


def plot_track(track: Dict[str, Any], positions: Dict[str, float], current_segment_idx: Optional[int] = None) -> plt.Figure:
    total = max(1, track_total_units(track))
    fig_w = min(14, max(8, total / 60))
    fig, ax = plt.subplots(figsize=(fig_w, 2.6))
    x = 0
    colors = {"straight": "#4caf50", "curve": "#ff9800", "obstacle": "#f44336"}
    for i, seg in enumerate(track.get("segments", [])):
        t = seg.get("type", "straight")
        w = _segment_units(seg)
        base_color = colors.get(t, "#90a4ae")
        if current_segment_idx is not None:
            if i == current_segment_idx:
                alpha = 1.0
            elif i < current_segment_idx:
                alpha = 0.3
            else:
                alpha = 0.6
        else:
            alpha = 0.8
        ax.add_patch(patches.Rectangle((x, 0.2), w, 0.8, color=base_color, alpha=alpha))
        x += w
    ax.set_xlim(0, total)
    ax.set_ylim(0, 1.2)
    ax.set_yticks([])
    ax.set_xlabel("Track units")
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    marker_styles = {"You": ("#1e88e5", "o"), "AI-1": ("#8e24aa", "^"), "AI-2": ("#607d8b", "s")}
    names = list(positions.keys())
    for i, name in enumerate(names):
        pos = max(0.0, min(float(positions[name]), float(total)))
        c, m = marker_styles.get(name, ("#000000", "o"))
        y = 0.6 + (i - (len(names)-1)/2.0) * 0.12
        ax.scatter([pos], [y], c=c, marker=m, s=80, edgecolors="white", linewidths=0.8, zorder=5)
        ax.text(pos, y + 0.12, name, color=c, ha="center", va="bottom", fontsize=9)
    return fig

def scale_track(track: Dict[str, Any], desired_total: int) -> Dict[str, Any]:
    """Scale straight segment lengths so that total units ~= desired_total."""
    segs = track.get("segments", [])
    if not segs:
        return track
    current_total = track_total_units(track)
    if current_total == 0 or desired_total <= 0:
        return track
    factor = desired_total / current_total
    new_segs: List[Dict[str, Any]] = []
    for seg in segs:
        units = _segment_units(seg)
        scaled = max(3, round(units * factor))
        new_segs.append({**seg, "units": scaled})
    return {"segments": new_segs}


def generate_track_indicator(track: Dict[str, Any], current_idx: int, window: int = 5) -> str:
    segs = track.get("segments", [])
    if not segs or current_idx < 0:
        return ""
    
    emojis = {"straight": "🛣️", "curve": "🌀", "obstacle": "🚧"}
    parts = []
    
    start = max(0, current_idx - 1)
    end = min(len(segs), current_idx + window)
    
    for i in range(start, end):
        seg_type = segs[i].get("type", "straight")
        emoji = emojis.get(seg_type, "➖")
        
        if i == current_idx:
            parts.append(f"👉 🏍️ **{seg_type.upper()}** {emoji}")
        elif i < current_idx:
            parts.append(f"~~{seg_type}~~")
        else:
            parts.append(f"{seg_type} {emoji}")
    
    return " → ".join(parts)


def generate_commentary(action: str, segment_type: str, speed: float, crashed: bool = False) -> str:
    if crashed:
        crash_msgs = [
            "❌ Crash! The rider loses control!",
            "💥 Wipeout! Speed was too high!",
            "⚠️ The bike skids out!"
        ]
        return random.choice(crash_msgs)
    
    if action == "accelerate":
        if segment_type == "straight":
            return "🏍️ Full throttle on the straight! Building speed!"
        elif segment_type == "curve":
            return "⚡ Risky acceleration through the curve!"
        else:
            return "💨 Pushing through the obstacle zone!"
    
    elif action == "brake":
        if segment_type == "curve":
            return "🛑 Smart braking into the tight turn!"
        elif segment_type == "obstacle":
            return "🚧 Slowing down to navigate obstacles carefully!"
        else:
            return "⬇️ Reducing speed for safety."
    
    elif action == "overtake":
        return "🔥 Bold overtaking maneuver! Perfect opportunity!"
    
    elif action == "maintain":
        if speed > 150:
            return "🎯 Maintaining high speed, steady control!"
        else:
            return "✅ Holding steady pace."
    
    return f"🏁 {action.capitalize()} on {segment_type}."


def generate_race_event(action: str, segment_type: str, speed: float, crashed: bool = False) -> Optional[str]:
    if crashed:
        return None
    
    if segment_type == "curve" and speed > 140:
        if random.random() < 0.3:
            return "⚠️ Skid on curve!"
    
    if segment_type == "obstacle" and action == "accelerate":
        if random.random() < 0.4:
            return "🚧 Jumped obstacle!"
    
    if action == "accelerate" and segment_type == "straight" and speed > 180:
        if random.random() < 0.2:
            return "💨 Speed boost activated!"
    
    if action == "overtake":
        return "🏁 Overtake successful!"
    
    return None
