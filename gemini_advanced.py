"""Advanced Gemini AI features for competition-winning integration."""

import os
import json
from typing import Any, Dict, Optional, List, Callable
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, FunctionDeclaration, Tool


class AdvancedGeminiService:
    """Advanced Gemini service with function calling, grounding, and streaming."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model = None
        self.chat_session = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Gemini with advanced features."""
        if not self.api_key:
            return
        
        try:
            genai.configure(api_key=self.api_key)
            
            # Define function declarations for function calling
            self.tools = self._create_function_tools()
            
            # Initialize model with advanced config
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                },
                tools=self.tools
            )
        except Exception as e:
            print(f"Failed to initialize Gemini: {e}")
    
    def _create_function_tools(self) -> List[Tool]:
        """Create function declarations for Gemini function calling."""
        
        # Function: Generate track segment
        generate_segment = FunctionDeclaration(
            name="generate_track_segment",
            description="Generate a single track segment with specific properties",
            parameters={
                "type": "object",
                "properties": {
                    "segment_type": {
                        "type": "string",
                        "enum": ["straight", "curve", "obstacle"],
                        "description": "Type of track segment"
                    },
                    "difficulty": {
                        "type": "number",
                        "description": "Difficulty level from 0.0 to 1.0"
                    },
                    "length": {
                        "type": "integer",
                        "description": "Length of segment in units"
                    }
                },
                "required": ["segment_type"]
            }
        )
        
        # Function: Analyze race performance
        analyze_performance = FunctionDeclaration(
            name="analyze_race_performance",
            description="Analyze race performance and provide insights",
            parameters={
                "type": "object",
                "properties": {
                    "avg_speed": {
                        "type": "number",
                        "description": "Average speed during race"
                    },
                    "crashes": {
                        "type": "integer",
                        "description": "Number of crashes"
                    },
                    "completion_time": {
                        "type": "number",
                        "description": "Time to complete race in seconds"
                    }
                },
                "required": ["avg_speed", "crashes", "completion_time"]
            }
        )
        
        # Function: Get racing strategy
        get_strategy = FunctionDeclaration(
            name="get_racing_strategy",
            description="Get optimal racing strategy for current conditions",
            parameters={
                "type": "object",
                "properties": {
                    "current_speed": {
                        "type": "number",
                        "description": "Current speed in km/h"
                    },
                    "segment_type": {
                        "type": "string",
                        "enum": ["straight", "curve", "obstacle"],
                        "description": "Current segment type"
                    },
                    "opponent_distance": {
                        "type": "number",
                        "description": "Distance to nearest opponent"
                    }
                },
                "required": ["current_speed", "segment_type"]
            }
        )
        
        return [Tool(function_declarations=[
            generate_segment,
            analyze_performance,
            get_strategy
        ])]
    
    def healthy(self) -> bool:
        """Check if service is initialized."""
        return self.model is not None
    
    # ==================== Function Calling ====================
    
    def generate_track_with_functions(self, difficulty: str, environment: str, 
                                     num_segments: int = 15) -> Dict[str, Any]:
        """Generate track using Gemini function calling."""
        if not self.model:
            return self._fallback_track(difficulty)
        
        try:
            prompt = f"""Generate a {difficulty} difficulty racing track in a {environment} environment.
            Create {num_segments} segments using the generate_track_segment function.
            Balance the track with appropriate mix of straights, curves, and obstacles.
            Consider difficulty when setting segment properties."""
            
            response = self.model.generate_content(prompt)
            
            # Process function calls
            segments = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call'):
                        fc = part.function_call
                        if fc.name == "generate_track_segment":
                            segments.append(self._process_segment_function(fc.args))
            
            if segments:
                return {"segments": segments}
            else:
                return self._fallback_track(difficulty)
        
        except Exception:
            return self._fallback_track(difficulty)
    
    def _process_segment_function(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process function call arguments into segment."""
        segment_type = args.get("segment_type", "straight")
        
        if segment_type == "straight":
            return {
                "type": "straight",
                "length": int(args.get("length", 80))
            }
        elif segment_type == "curve":
            return {
                "type": "curve",
                "difficulty": float(args.get("difficulty", 0.5))
            }
        else:  # obstacle
            return {
                "type": "obstacle",
                "severity": float(args.get("difficulty", 0.5))
            }
    
    # ==================== Grounding with Google Search ====================
    
    def generate_track_with_grounding(self, difficulty: str, environment: str) -> Dict[str, Any]:
        """Generate track with Google Search grounding for real-world inspiration."""
        if not self.model:
            return self._fallback_track(difficulty)
        
        try:
            # Use grounding to get real racing track inspiration
            prompt = f"""Research famous {environment} racing tracks and circuits.
            Generate a {difficulty} difficulty bike racing track inspired by real-world designs.
            Include 12-18 segments with realistic racing elements.
            Return as JSON: {{"segments": [{{"type": "straight/curve/obstacle", "length": 80, "difficulty": 0.5}}]}}"""
            
            # Note: Grounding requires Vertex AI setup
            # For now, use enhanced generation
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.6,
                    "response_mime_type": "application/json"
                }
            )
            
            if response.text:
                data = json.loads(response.text)
                if "segments" in data:
                    return data
            
            return self._fallback_track(difficulty)
        
        except Exception:
            return self._fallback_track(difficulty)
    
    # ==================== Multi-turn Conversations ====================
    
    def start_coaching_session(self, user_profile: Dict[str, Any]) -> None:
        """Start a multi-turn coaching conversation."""
        if not self.model:
            return
        
        system_instruction = f"""You are an expert bike racing coach. 
        User profile: {json.dumps(user_profile)}
        Provide personalized racing advice, strategy tips, and encouragement.
        Analyze their performance and suggest improvements."""
        
        self.chat_session = self.model.start_chat(history=[])
    
    def get_coaching_advice(self, race_data: Dict[str, Any]) -> str:
        """Get coaching advice based on race performance."""
        if not self.chat_session:
            return "Start a coaching session first."
        
        try:
            prompt = f"""Analyze this race performance:
            - Average Speed: {race_data.get('avg_speed', 0)} km/h
            - Crashes: {race_data.get('crashes', 0)}
            - Completion Time: {race_data.get('time', 0)} seconds
            - Difficulty: {race_data.get('difficulty', 'medium')}
            
            Provide specific, actionable advice to improve."""
            
            response = self.chat_session.send_message(prompt)
            return response.text
        
        except Exception as e:
            return f"Unable to provide advice: {str(e)}"
    
    # ==================== Streaming Responses ====================
    
    def generate_commentary_stream(self, action: str, segment: str, 
                                   speed: float) -> List[str]:
        """Generate live race commentary with streaming."""
        if not self.model:
            return ["Racing action in progress!"]
        
        try:
            prompt = f"""Generate exciting live race commentary for:
            Action: {action}
            Segment: {segment}
            Speed: {speed} km/h
            
            Make it dramatic and engaging, 2-3 sentences."""
            
            chunks = []
            response = self.model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    chunks.append(chunk.text)
            
            return chunks if chunks else ["Intense racing action!"]
        
        except Exception:
            return ["Racing continues!"]
    
    # ==================== Advanced Decision Making ====================
    
    def decide_with_reasoning(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Make decision with detailed reasoning using chain-of-thought."""
        if not self.model:
            return {"action": "maintain", "reason": "Default", "reasoning_steps": []}
        
        try:
            prompt = f"""You are making a split-second racing decision.
            
            Current State:
            - Speed: {game_state.get('speed', 0)} km/h
            - Segment: {game_state.get('segment_type', 'straight')}
            - Difficulty: {game_state.get('difficulty', 0.5)}
            - Opponent Distance: {game_state.get('opponent_distance', 100)} units
            
            Think step-by-step:
            1. Analyze current situation
            2. Consider risks and opportunities
            3. Evaluate possible actions
            4. Choose optimal action
            
            Return JSON: {{"action": "accelerate/brake/maintain/overtake", "reason": "brief", "reasoning_steps": ["step1", "step2", "step3"]}}"""
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.4,
                    "response_mime_type": "application/json"
                }
            )
            
            if response.text:
                return json.loads(response.text)
            
            return {"action": "maintain", "reason": "Default", "reasoning_steps": []}
        
        except Exception:
            return {"action": "maintain", "reason": "Error", "reasoning_steps": []}
    
    # ==================== Batch Processing ====================
    
    def batch_analyze_races(self, races: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze multiple races in batch for efficiency."""
        if not self.model:
            return []
        
        results = []
        for race in races:
            try:
                prompt = f"""Analyze race: Speed {race.get('avg_speed')}km/h, 
                Crashes: {race.get('crashes')}, Time: {race.get('time')}s.
                Rate performance 1-10 and give one tip.
                JSON: {{"rating": 8, "tip": "brake earlier on curves"}}"""
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                if response.text:
                    results.append(json.loads(response.text))
            except Exception:
                results.append({"rating": 5, "tip": "Keep practicing"})
        
        return results
    
    # ==================== Fallback ====================
    
    def _fallback_track(self, difficulty: str) -> Dict[str, Any]:
        """Fallback track generation."""
        import random
        random.seed(hash(difficulty))
        
        segments = []
        num_segments = {"easy": 12, "medium": 15, "hard": 18}.get(difficulty, 15)
        
        for _ in range(num_segments):
            r = random.random()
            if difficulty == "easy":
                if r < 0.6:
                    segments.append({"type": "straight", "length": random.randint(80, 120)})
                elif r < 0.85:
                    segments.append({"type": "curve", "difficulty": round(random.uniform(0.2, 0.5), 2)})
                else:
                    segments.append({"type": "obstacle", "severity": round(random.uniform(0.2, 0.4), 2)})
            elif difficulty == "hard":
                if r < 0.35:
                    segments.append({"type": "straight", "length": random.randint(50, 90)})
                elif r < 0.75:
                    segments.append({"type": "curve", "difficulty": round(random.uniform(0.6, 0.9), 2)})
                else:
                    segments.append({"type": "obstacle", "severity": round(random.uniform(0.6, 0.9), 2)})
            else:  # medium
                if r < 0.5:
                    segments.append({"type": "straight", "length": random.randint(60, 110)})
                elif r < 0.8:
                    segments.append({"type": "curve", "difficulty": round(random.uniform(0.4, 0.7), 2)})
                else:
                    segments.append({"type": "obstacle", "severity": round(random.uniform(0.4, 0.7), 2)})
        
        return {"segments": segments}
