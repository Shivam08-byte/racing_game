import random
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_NON_STRAIGHT_UNITS = 60
MAX_SPEED = 240.0
STEP_DISTANCE_DIVISOR = 10.0


def segment_units(seg: Dict[str, Any]) -> int:
    if "units" in seg:
        return int(seg["units"])
    t = seg.get("type")
    if t == "straight":
        return int(max(5, min(200, int(seg.get("length", 80)))))
    return DEFAULT_NON_STRAIGHT_UNITS


def total_units(track: Dict[str, Any]) -> int:
    return sum(segment_units(s) for s in track.get("segments", []))


def cumulative_boundaries(track: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    c = []
    pos = 0
    for seg in track.get("segments", []):
        u = segment_units(seg)
        c.append((pos + u, seg))
        pos += u
    return c


def find_segment_at_position(track_bounds: List[Tuple[int, Dict[str, Any]]], pos_units: float) -> Dict[str, Any]:
    for b, seg in track_bounds:
        if pos_units < b:
            return seg
    return track_bounds[-1][1]


class RaceSimulation:
    def __init__(self, track: Dict[str, Any], difficulty: str, gemini_service: Any, second_ai: bool = True, seed: Optional[int] = None):
        self.track = track
        self.difficulty = difficulty
        self.gemini = gemini_service
        self.random = random.Random(seed)
        self.total = total_units(track)
        self.bounds = cumulative_boundaries(track)
        self.players: List[Dict[str, Any]] = []
        self.players.append(self._new_racer("You", is_human=True))
        self.players.append(self._new_racer("AI-1", is_human=False))
        if second_ai:
            self.players.append(self._new_racer("AI-2", is_human=False))
        self.logs: List[str] = []
        self.step_count = 0
        self.running = False
        self.finished_race = False

    def _new_racer(self, name: str, is_human: bool) -> Dict[str, Any]:
        return {
            "name": name,
            "is_human": is_human,
            "speed": 0.0,
            "pos": 0.0,
            "crashes": 0,
            "finished": False,
            "sum_speed": 0.0,
            "last_action": "",
            "last_reason": "",
        }

    def reset_runtime(self) -> None:
        for p in self.players:
            p["speed"] = 0.0
            p["pos"] = 0.0
            p["crashes"] = 0
            p["finished"] = False
            p["sum_speed"] = 0.0
            p["last_action"] = ""
            p["last_reason"] = ""
        self.logs.clear()
        self.step_count = 0
        self.running = True
        self.finished_race = False

    def _df(self) -> float:
        return {"easy": 0.8, "medium": 1.0, "hard": 1.2}.get(self.difficulty, 1.0)

    def _nearest_proximity(self, who: Dict[str, Any]) -> float:
        nearest = float("inf")
        for p in self.players:
            if p is who or p.get("finished"):
                continue
            d = abs(p["pos"] - who["pos"])
            if d < nearest:
                nearest = d
        if nearest == float("inf"):
            return 9999.0
        return nearest

    def _segment_and_params(self, pos_units: float) -> Tuple[str, Dict[str, Any]]:
        seg = find_segment_at_position(self.bounds, pos_units)
        t = seg.get("type", "straight")
        return t, seg

    def _heuristic_decision(self, speed: float, seg_type: str, seg: Dict[str, Any]) -> Dict[str, str]:
        df = self._df()
        if seg_type == "curve":
            lim = 120 - 70 * float(seg.get("difficulty", 0.5)) * df
            if speed > lim:
                return {"action": "brake", "reason": "Curve control."}
        if seg_type == "obstacle":
            lim = 110 - 60 * float(seg.get("severity", 0.5)) * df
            if speed > lim:
                return {"action": "brake", "reason": "Obstacle caution."}
        if speed < 140:
            return {"action": "accelerate", "reason": "Gain speed."}
        return {"action": "maintain", "reason": "Stable pace."}

    def _apply_action(self, p: Dict[str, Any], action: str) -> None:
        if action == "accelerate":
            delta = {"easy": 18.0, "medium": 14.0, "hard": 12.0}.get(self.difficulty, 14.0)
            p["speed"] += delta
        elif action == "brake":
            p["speed"] -= 18.0
        elif action == "overtake":
            p["speed"] += 8.0
        else:
            p["speed"] -= 2.0
        if p["speed"] < 0:
            p["speed"] = 0.0
        if p["speed"] > MAX_SPEED:
            p["speed"] = MAX_SPEED

    def _crash_probability(self, p: Dict[str, Any], action: str, seg_type: str, seg: Dict[str, Any], proximity: float) -> float:
        df = self._df()
        sp = p["speed"]
        prob = 0.01
        if seg_type == "straight":
            safe = 220
            if sp > safe:
                prob += (sp - safe) / 400.0
        elif seg_type == "curve":
            lim = 120 - 70 * float(seg.get("difficulty", 0.5)) * df
            if sp > lim:
                prob += (sp - lim) / 200.0
        elif seg_type == "obstacle":
            lim = 110 - 60 * float(seg.get("severity", 0.5)) * df
            if sp > lim:
                prob += (sp - lim) / 180.0
        if action == "overtake" and proximity <= 8:
            prob += 0.08
        return max(0.0, min(0.6, prob))

    def _advance_position(self, p: Dict[str, Any]) -> float:
        dist = p["speed"] / STEP_DISTANCE_DIVISOR
        if dist < 0:
            dist = 0.0
        p["pos"] += dist
        if p["pos"] >= self.total:
            p["pos"] = float(self.total)
            p["finished"] = True
        return dist

    def step(self) -> Dict[str, Any]:
        if self.finished_race:
            return {"finished": True}
        decisions: Dict[str, Dict[str, str]] = {}
        events: List[str] = []
        for p in self.players:
            if p.get("finished"):
                decisions[p["name"]] = {"action": "finish", "reason": "Finished"}
                continue
            seg_type, seg = self._segment_and_params(p["pos"])
            proximity = self._nearest_proximity(p)
            if p.get("is_human"):
                d = self.gemini.decide_action(p["speed"], seg_type, self.difficulty, proximity)
            else:
                d = self._heuristic_decision(p["speed"], seg_type, seg)
            action = d.get("action", "maintain").lower()
            reason = d.get("reason", "")
            self._apply_action(p, action)
            crash_p = self._crash_probability(p, action, seg_type, seg, proximity)
            crashed = self.random.random() < crash_p
            if crashed:
                p["crashes"] += 1
                p["speed"] = max(20.0, p["speed"] * 0.3)
                reason = f"Crash on {seg_type}."
                events.append(f"{p['name']} crashed on {seg_type}.")
            dist = self._advance_position(p)
            p["sum_speed"] += p["speed"]
            p["last_action"] = action
            p["last_reason"] = reason
            decisions[p["name"]] = {"action": action, "reason": reason, "segment": seg_type, "distance": round(dist, 2)}
        self.step_count += 1
        self.logs.append(
            f"Step {self.step_count}: "
            + "; ".join([f"{p['name']} spd={p['speed']:.0f} pos={p['pos']:.0f} crashes={p['crashes']}" for p in self.players])
            + ("; " + " ".join(events) if events else "")
        )
        if self.players[0]["finished"]:
            self.finished_race = True
            self.running = False
        return {"decisions": decisions, "finished": self.finished_race}

    def player_state(self) -> Dict[str, Any]:
        p = self.players[0]
        return {
            "speed": p["speed"],
            "pos": p["pos"],
            "crashes": p["crashes"],
            "progress": p["pos"] / self.total if self.total else 0.0,
            "last_action": p["last_action"],
            "last_reason": p["last_reason"],
            "finished": p["finished"],
        }

    def positions(self) -> Dict[str, float]:
        return {p["name"]: p["pos"] for p in self.players}

    def performance_summary(self) -> str:
        p = self.players[0]
        avg_speed = (p["sum_speed"] / max(1, self.step_count)) if self.step_count else 0.0
        return f"crashes={p['crashes']}, avg_speed_kmh={avg_speed:.1f}, steps={self.step_count}"

    def rank_order(self) -> List[str]:
        return [p["name"] for p in sorted(self.players, key=lambda x: (-x["finished"], -x["pos"]))]
