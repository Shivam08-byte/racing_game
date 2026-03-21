import os
import json
import pandas as pd
from dotenv import load_dotenv
import streamlit as st
from typing import Dict, Any

from gemini_service import GeminiService
from ollama_service import OllamaService
from simulation import RaceSimulation
from utils import (
    plot_track, scale_track, get_current_segment_index, 
    calculate_progress, generate_track_indicator, 
    generate_commentary, generate_race_event
)

load_dotenv()

st.set_page_config(page_title="AI Bike Racing Simulator 2026", layout="wide")

# Choose service based on env flags
if "service" not in st.session_state:
    ollama_on = os.getenv("OLLAMA_FLAG", "False").lower() in {"1", "true", "yes"}
    gemini_on = os.getenv("GEMINI_FLAG", "True").lower() in {"1", "true", "yes"}
    service = None
    if ollama_on:
        svc = OllamaService()
        if svc.healthy():
            service = svc
    if service is None and gemini_on:
        svc = GeminiService()
        if svc.healthy() or not ollama_on:
            service = svc
    # fallback
    if service is None:
        service = GeminiService()
    st.session_state.service = service
if "track" not in st.session_state:
    st.session_state.track = None
if "sim" not in st.session_state:
    st.session_state.sim = None
if "race_log" not in st.session_state:
    st.session_state.race_log = []
if "decisions" not in st.session_state:
    st.session_state.decisions = {}
if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = []
if "commentary" not in st.session_state:
    st.session_state.commentary = []
if "last_event" not in st.session_state:
    st.session_state.last_event = None
if "prev_speed" not in st.session_state:
    st.session_state.prev_speed = 0.0

st.title("🏍️ AI Bike Racing Simulator 2026")

with st.sidebar:
    st.header("⚙️ Setup")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
    environment = st.selectbox("Environment", ["city", "desert", "snow", "cyberpunk"], index=0)
    desired_units = int(st.number_input("Track length (units)", min_value=50, max_value=400, value=100, step=10))
    
    st.divider()
    st.header("🎮 Controls")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        gen_track = st.button("🔄 Generate", use_container_width=True)
    with c2:
        start_race = st.button("🏁 Start", use_container_width=True, type="primary")
    with c3:
        next_step = st.button("▶️ Step", use_container_width=True)
    
    st.divider()
    if st.session_state.service.healthy():
        st.success(f"{type(st.session_state.service).__name__.replace('Service','')} connected", icon="✅")
    else:
        st.info("Running with offline / heuristic engine.", icon="ℹ️")

if gen_track:
    raw_track = st.session_state.service.generate_track(difficulty, environment)
    st.session_state.track = scale_track(raw_track, desired_units)
    st.session_state.sim = None
    st.session_state.race_log = []
    st.session_state.decisions = {}
    st.session_state.commentary = []
    st.session_state.last_event = None
    st.rerun()

if start_race:
    if not st.session_state.track:
        raw_track = st.session_state.service.generate_track(difficulty, environment)
        st.session_state.track = scale_track(raw_track, desired_units)
    else:
        st.session_state.track = scale_track(st.session_state.track, desired_units)
    st.session_state.sim = RaceSimulation(st.session_state.track, difficulty, st.session_state.service, second_ai=True)
    st.session_state.sim.reset_runtime()
    st.session_state.race_log = []
    st.session_state.decisions = {}
    st.session_state.commentary = []
    st.session_state.last_event = None
    st.session_state.prev_speed = 0.0
    st.rerun()

if next_step:
    if st.session_state.sim is None:
        st.warning("Start the race first.")
    else:
        sim = st.session_state.sim
        res = sim.step()
        st.session_state.decisions = res.get("decisions", {})
        st.session_state.race_log = sim.logs[-200:]
        
        pstate = sim.player_state()
        you_dec = st.session_state.decisions.get("You", {})
        action = you_dec.get("action", "maintain")
        segment_type = you_dec.get("segment", "straight")
        speed = pstate["speed"]
        crashed = pstate["crashes"] > (st.session_state.get("prev_crashes", 0))
        
        commentary = generate_commentary(action, segment_type, speed, crashed)
        st.session_state.commentary.append(commentary)
        if len(st.session_state.commentary) > 10:
            st.session_state.commentary = st.session_state.commentary[-10:]
        
        event = generate_race_event(action, segment_type, speed, crashed)
        st.session_state.last_event = event
        st.session_state.prev_speed = speed
        st.session_state.prev_crashes = pstate["crashes"]
        
        if res.get("finished"):
            st.session_state.commentary.append("🏁 Race Complete! You crossed the finish line!")
            summary = sim.performance_summary()
            avg_speed = 0.0
            try:
                avg_speed = sim.players[0]["sum_speed"] / max(1, sim.step_count)
            except Exception:
                avg_speed = float(pstate.get("speed", 0.0))
            st.session_state.leaderboard.append({
                "difficulty": difficulty,
                "environment": environment,
                "crashes": pstate["crashes"],
                "avg_speed_kmh": float(avg_speed),
                "steps": int(sim.step_count),
                "rank": sim.rank_order().index("You") + 1,
                "summary": summary,
            })
        st.rerun()

if st.session_state.sim is not None:
    sim = st.session_state.sim
    pstate = sim.player_state()
    progress = calculate_progress(pstate["pos"], st.session_state.track)
    current_seg_idx = get_current_segment_index(pstate["pos"], st.session_state.track)
    
    st.subheader("🏁 Race Progress")
    st.progress(progress)
    st.caption(f"**{progress*100:.1f}% Complete** • Step {sim.step_count}")
    
    st.subheader("🛣️ Current Track Position")
    track_indicator = generate_track_indicator(st.session_state.track, current_seg_idx)
    st.markdown(track_indicator)
    
    if st.session_state.last_event:
        st.info(st.session_state.last_event, icon="⚡")
else:
    st.info("🎮 Generate a track and start the race to begin!", icon="ℹ️")

st.divider()

if st.session_state.track is not None:
    st.subheader("🗺️ Track Visualization")
    sim = st.session_state.sim
    positions = sim.positions() if sim else {"You": 0.0, "AI-1": 0.0, "AI-2": 0.0}
    current_seg_idx = get_current_segment_index(positions.get("You", 0.0), st.session_state.track) if sim else None
    fig = plot_track(st.session_state.track, positions, current_seg_idx)
    st.pyplot(fig, clear_figure=True)
else:
    st.write("Generate a track to begin.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Player Stats")
    if st.session_state.sim is not None:
        ps = st.session_state.sim.player_state()
        speed_delta = ps["speed"] - st.session_state.prev_speed
        
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Speed", f"{ps['speed']:.0f} km/h", delta=f"{speed_delta:+.0f}" if speed_delta != 0 else None)
            st.metric("Crashes", f"{ps['crashes']}")
        with m2:
            st.metric("Position", f"{ps['pos']:.0f} units")
            st.metric("Progress", f"{ps['progress']*100:.1f}%")
        
        if ps.get("finished"):
            st.success("🏆 Race Complete!")
            if st.button("🔄 Generate Adaptive Track", type="secondary"):
                summary = st.session_state.sim.performance_summary()
                st.session_state.track = st.session_state.service.adapt_track(summary, difficulty, environment)
                st.session_state.sim = None
                st.session_state.race_log = []
                st.session_state.decisions = {}
                st.session_state.commentary = []
                st.rerun()
    else:
        st.write("Start a race to view live stats.")

with col2:
    st.subheader("🤖 Opponent Comparison")
    if st.session_state.sim is not None:
        positions = st.session_state.sim.positions()
        you_pos = positions.get("You", 0.0)
        ai1_pos = positions.get("AI-1", 0.0)
        ai2_pos = positions.get("AI-2", 0.0)
        
        total = max(1, st.session_state.sim.total)
        you_prog = you_pos / total
        ai1_prog = ai1_pos / total
        ai2_prog = ai2_pos / total
        
        st.write("**🏍️ You**")
        st.progress(you_prog)
        st.caption(f"{you_prog*100:.1f}%")
        
        st.write("**🤖 AI-1**")
        st.progress(ai1_prog)
        st.caption(f"{ai1_prog*100:.1f}%")
        
        if "AI-2" in positions:
            st.write("**🤖 AI-2**")
            st.progress(ai2_prog)
            st.caption(f"{ai2_prog*100:.1f}%")
    else:
        st.write("Start a race to see opponent positions.")

st.divider()

st.subheader("💬 Live Race Commentary")
if st.session_state.commentary:
    for comment in reversed(st.session_state.commentary[-5:]):
        st.markdown(f"• {comment}")
else:
    st.write("Commentary will appear here during the race.")

with st.expander("🧠 AI Decision Explainability", expanded=False):
    dec = st.session_state.decisions
    if dec:
        you = dec.get("You") or {}
        st.markdown(f"**Your Action:** `{you.get('action', '-')}`")
        st.caption(f"💭 {you.get('reason', 'No reason provided.')}")
        st.divider()
        st.markdown("**Opponent Actions**")
        for name in [n for n in dec.keys() if n != "You"]:
            st.markdown(f"• **{name}**: `{dec[name].get('action', '-')}`")
            st.caption(f"💭 {dec[name].get('reason', '')}")
    else:
        st.write("AI decisions will appear here after each step.")

with st.expander("📋 Detailed Race Log", expanded=False):
    if st.session_state.race_log:
        st.code("\n".join(st.session_state.race_log[-50:]), language="text")
    else:
        st.write("No race events yet.")

st.subheader("Leaderboard (in-memory)")
if st.session_state.leaderboard:
    df = pd.DataFrame(st.session_state.leaderboard)
    st.dataframe(df.tail(20), use_container_width=True, hide_index=True)
else:
    st.caption("Complete a race to add a result.")
