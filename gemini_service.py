import os
import json
import random
import time
from typing import Any, Dict, Optional

try:
    import google.generativeai as genai
except Exception:
    genai = None


class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash", timeout: float = 15.0):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name
        self.timeout = timeout
        self._client_ready = False
        self.model = None
        self.safety_settings = self._get_safety_settings()
        self._init_client()

    def _get_safety_settings(self) -> list:
        """Configure safety settings for Gemini API."""
        if genai is None:
            return []
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            return [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                }
            ]
        except Exception:
            return []

    def _init_client(self) -> None:
        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(
                    self.model_name,
                    generation_config={
                        "temperature": 0.7,
                        "response_mime_type": "application/json",
                    },
                    safety_settings=self.safety_settings
                )
                self._client_ready = True
            except Exception:
                self._client_ready = False
        else:
            self._client_ready = False

    def healthy(self) -> bool:
        return self._client_ready

    def _extract_json(self, text: str) -> Optional[str]:
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return m.group(0) if m else None

    def _call_json(self, prompt: str, temperature: float = 0.7, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        if not self._client_ready:
            return None
        p = prompt
        for i in range(max_retries + 1):
            try:
                resp = self.model.generate_content(
                    p,
                    generation_config={
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                    },
                    safety_settings=self.safety_settings
                )
                text = getattr(resp, "text", None)
                if not text and hasattr(resp, "candidates"):
                    try:
                        text = resp.candidates[0].content.parts[0].text
                    except Exception:
                        text = None
                if text:
                    try:
                        return json.loads(text)
                    except Exception:
                        j = self._extract_json(text)
                        if j:
                            try:
                                return json.loads(j)
                            except Exception:
                                pass
                p = prompt + "\nReturn only strict minified JSON. No prose, no code fences, no comments."
            except Exception:
                time.sleep(0.5 * (i + 1))
        return None

    def generate_track(self, difficulty: str, environment: str) -> Dict[str, Any]:
        schema = (
            '{"segments": ['
            '{"type": "straight", "length": 80}, '
            '{"type": "curve", "difficulty": 0.5}, '
            '{"type": "obstacle", "severity": 0.5}'
            ']}'
        )
        guidelines = (
            f"Design a step-based bike racing track in a {environment} setting for a {difficulty} difficulty race.\n"
            "Constraints:\n"
            "- Use only these segment types: straight, curve, obstacle.\n"
            "- For straight, include integer 'length' between 40 and 150.\n"
            "- For curve, include float 'difficulty' between 0 and 1 (higher is sharper).\n"
            "- For obstacle, include float 'severity' between 0 and 1 (higher is more dangerous).\n"
            "- Generate between 12 and 20 segments.\n"
            "- Balance segments to fit difficulty (hard: more curves/obstacles and shorter straights; easy: opposite).\n"
            "Return ONLY JSON conforming to the schema example below; no extra text.\n"
            f"Schema example: {schema}"
        )
        data = self._call_json(guidelines, temperature=0.5, max_retries=2)
        if not data or "segments" not in data or not isinstance(data["segments"], list):
            return self._fallback_track(difficulty)
        clean = []
        for seg in data["segments"]:
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

    def decide_action(self, current_speed: float, segment_type: str, difficulty: str, opponent_proximity: float) -> Dict[str, Any]:
        schema = '{"action":"accelerate|brake|overtake|maintain","reason":"string"}'
        prompt = (
            "You are the rider's decision engine in a step-based bike race. Decide the next action.\n"
            f"Inputs:\n- current_speed_kmh: {round(float(current_speed), 1)}\n"
            f"- segment_type: {segment_type}\n"
            f"- difficulty: {difficulty}\n"
            f"- opponent_proximity_units: {round(float(opponent_proximity), 1)} (smaller means closer; <=5 is side-by-side)\n"
            "Rules of thumb:\n"
            "- On sharp curves or severe obstacles, prefer braking if speed seems high.\n"
            "- Overtake only when proximity <= 8 and speed is stable; it increases risk slightly.\n"
            "- Accelerate on straights when safe.\n"
            "- Maintain when unsure.\n"
            f"Return ONLY JSON matching: {schema}."
        )
        data = self._call_json(prompt, temperature=0.7, max_retries=2)
        if not data:
            return self._offline_decision(current_speed, segment_type, difficulty, opponent_proximity)
        action = str(data.get("action", "maintain")).lower()
        if action not in {"accelerate", "brake", "overtake", "maintain"}:
            action = "maintain"
        reason = data.get("reason", "Default strategy.")
        return {"action": action, "reason": reason}

    def adapt_track(self, performance_summary: str, base_difficulty: str, environment: str) -> Dict[str, Any]:
        schema = '{"segments":[{"type":"straight","length":80},{"type":"curve","difficulty":0.5},{"type":"obstacle","severity":0.5}]}'
        prompt = (
            "Adapt a racing track based on player performance.\n"
            f"Environment: {environment}\n"
            f"Base difficulty: {base_difficulty}\n"
            f"Performance summary: {performance_summary}\n"
            "Make the next track slightly easier if the player crashed often or had low average speed; slightly harder if they dominated.\n"
            "Prefer 12-18 segments.\n"
            f"Return ONLY JSON matching: {schema}."
        )
        data = self._call_json(prompt, temperature=0.4, max_retries=2)
        if not data or "segments" not in data or not isinstance(data["segments"], list):
            return self._fallback_track(base_difficulty)
        clean = []
        for seg in data["segments"]:
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
            return self._fallback_track(base_difficulty)
        return {"segments": clean}

    def _fallback_track(self, difficulty: str) -> Dict[str, Any]:
        random.seed(hash(difficulty) % (2**32))
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
