import os
import json
import time
import random
from typing import Any, Dict, Optional

try:
    import requests
except Exception:
    requests = None


class OllamaService:
    """Local Ollama service wrapper mimicking GeminiService's public interface."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None, timeout: float = 15.0):
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3")
        self.timeout = timeout
        self._healthy_cached: Optional[bool] = None

    # ---------------- Core helpers ---------------- #

    def _post_generate(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        if requests is None:
            return None
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
            },
            "stream": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response")
        except Exception:
            pass
        return None

    def healthy(self) -> bool:
        if self._healthy_cached is not None:
            return self._healthy_cached
        if requests is None:
            self._healthy_cached = False
            return False
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=3)
            self._healthy_cached = r.status_code == 200
        except Exception:
            self._healthy_cached = False
        return self._healthy_cached

    # ---------------- JSON prompt runner ---------------- #

    def _extract_json(self, text: str) -> Optional[str]:
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return m.group(0) if m else None

    def _call_json(self, prompt: str, temperature: float = 0.7, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        if not self.healthy():
            return None
        p = prompt + "\nReturn ONLY minified JSON; no prose, no code fences."
        for i in range(max_retries + 1):
            txt = self._post_generate(p, temperature=temperature)
            if not txt:
                time.sleep(0.4 * (i + 1))
                continue
            try:
                return json.loads(txt)
            except Exception:
                j = self._extract_json(txt)
                if j:
                    try:
                        return json.loads(j)
                    except Exception:
                        pass
            # tighten prompt
            p += "\nEnsure response is STRICT valid JSON only."
        return None

    # ---------------- Public API (mirrors GeminiService) ---------------- #

    def generate_track(self, difficulty: str, environment: str) -> Dict[str, Any]:
        schema = '{"segments":[{"type":"straight","length":80},{"type":"curve","difficulty":0.5},{"type":"obstacle","severity":0.5}]}'
        prompt = (
            f"Design a step-based bike racing track in a {environment} setting for a {difficulty} difficulty race.\n"
            "Constraints:\n"
            "- Use only segment types straight, curve, obstacle.\n"
            "- For straight, include integer 'length' 40-150.\n"
            "- For curve, float 'difficulty' 0-1.\n"
            "- For obstacle, float 'severity' 0-1.\n"
            "- Generate 12-20 segments appropriate to difficulty.\n"
            f"Return ONLY JSON matching: {schema}."
        )
        data = self._call_json(prompt, temperature=0.5)
        if not data or "segments" not in data:
            return self._fallback_track(difficulty)
        return self._clean_track(data, difficulty)

    def decide_action(self, current_speed: float, segment_type: str, difficulty: str, opponent_proximity: float) -> Dict[str, Any]:
        schema = '{"action":"accelerate|brake|overtake|maintain","reason":"string"}'
        prompt = (
            "You are the rider's decision engine in a step-based bike race. Decide the next action.\n"
            f"Inputs:\ncurrent_speed_kmh={current_speed:.1f}, segment_type={segment_type}, difficulty={difficulty}, opponent_proximity={opponent_proximity:.1f}.\n"
            "Rules: brake on dangerous curves/obstacles, accelerate on safe straights, overtake when very close and safe, maintain otherwise.\n"
            f"Return ONLY JSON like: {schema}."
        )
        data = self._call_json(prompt, temperature=0.7)
        if not data:
            return self._offline_decision(current_speed, segment_type, difficulty, opponent_proximity)
        action = str(data.get("action", "maintain")).lower()
        if action not in {"accelerate", "brake", "overtake", "maintain"}:
            action = "maintain"
        return {"action": action, "reason": data.get("reason", "")}

    def adapt_track(self, performance_summary: str, base_difficulty: str, environment: str) -> Dict[str, Any]:
        schema = '{"segments":[{"type":"straight","length":80},{"type":"curve","difficulty":0.5},{"type":"obstacle","severity":0.5}]}'
        prompt = (
            "Adapt a racing track for the next race based on player performance summary below.\n"
            f"Performance: {performance_summary}\nEnvironment: {environment}\nBase difficulty: {base_difficulty}\n"
            "Make easier if many crashes/slow speed, harder if dominant. 12-18 segments.\n"
            f"Return ONLY JSON matching: {schema}."
        )
        data = self._call_json(prompt, temperature=0.4)
        if not data or "segments" not in data:
            return self._fallback_track(base_difficulty)
        return self._clean_track(data, base_difficulty)

    # ---------------- Internal helpers ---------------- #

    def _clean_track(self, data: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
        clean = []
        for seg in data.get("segments", []):
            t = seg.get("type")
            if t == "straight":
                l = int(max(20, min(200, int(seg.get("length", 80)))))
                clean.append({"type": "straight", "length": l})
            elif t == "curve":
                d = float(max(0.0, min(1.0, float(seg.get("difficulty", 0.5)))))
                clean.append({"type": "curve", "difficulty": round(d, 2)})
            elif t == "obstacle":
                s = float(max(0.0, min(1.0, float(seg.get("severity", 0.5)))))
                clean.append({"type": "obstacle", "severity": round(s, 2)})
        if not clean:
            return self._fallback_track(difficulty)
        return {"segments": clean}

    def _fallback_track(self, difficulty: str) -> Dict[str, Any]:
        random.seed(hash("ollama" + difficulty) % (2**32))
        segs = []
        n = {"easy": 12, "medium": 16, "hard": 18}.get(difficulty, 14)
        for _ in range(n):
            r = random.random()
            if difficulty == "easy":
                if r < 0.6:
                    segs.append({"type": "straight", "length": random.randint(80, 140)})
                elif r < 0.85:
                    segs.append({"type": "curve", "difficulty": round(random.uniform(0.2, 0.5), 2)})
                else:
                    segs.append({"type": "obstacle", "severity": round(random.uniform(0.2, 0.5), 2)})
            elif difficulty == "hard":
                if r < 0.35:
                    segs.append({"type": "straight", "length": random.randint(50, 100)})
                elif r < 0.75:
                    segs.append({"type": "curve", "difficulty": round(random.uniform(0.5, 0.9), 2)})
                else:
                    segs.append({"type": "obstacle", "severity": round(random.uniform(0.5, 0.9), 2)})
            else:
                if r < 0.5:
                    segs.append({"type": "straight", "length": random.randint(60, 120)})
                elif r < 0.8:
                    segs.append({"type": "curve", "difficulty": round(random.uniform(0.3, 0.7), 2)})
                else:
                    segs.append({"type": "obstacle", "severity": round(random.uniform(0.3, 0.7), 2)})
        return {"segments": segs}

    def _offline_decision(self, current_speed: float, segment_type: str, difficulty: str, opponent_proximity: float) -> Dict[str, Any]:
        df = {"easy": 0.8, "medium": 1.0, "hard": 1.2}.get(difficulty, 1.0)
        if segment_type == "curve":
            limit = 120 - 60 * df
            if current_speed > limit:
                return {"action": "brake", "reason": "Curve ahead at above-safe speed."}
        if segment_type == "obstacle":
            if current_speed > 70:
                return {"action": "brake", "reason": "Obstacle requires reduced speed."}
        if opponent_proximity <= 6 and current_speed >= 60:
            return {"action": "overtake", "reason": "Close to opponent; attempting overtake."}
        if current_speed < 140:
            return {"action": "accelerate", "reason": "Building speed on current segment."}
        return {"action": "maintain", "reason": "Holding speed."}
