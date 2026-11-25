# Minimal Streamlit app for the same Robot Builder MVP (web UI)
import streamlit as st
import json

PARTS_CATALOG = [
    {"id": "frame", "name": "Base Frame", "specs": {"mass":1.0, "power":0.0}},
    {"id": "gripper", "name": "Gripper", "specs": {"mass":0.5, "power":5.0}},
    {"id": "arm", "name": "Arm Actuator", "specs": {"mass":0.8, "power":7.0}},
    {"id": "vision", "name": "Vision Sensor", "specs": {"mass":0.2, "power":2.0}},
    {"id": "battery", "name": "Li-ion Battery", "specs": {"mass":0.6, "power":-1.0, "capacity":100}},
]
BLUEPRINT_DEFAULT = {"name": "Untitled Robot", "parts": [], "power_budget": 100, "state": "idle", "energy_used":0.0, "tasks_remaining":5}

def render_blueprint(bp):
    st.write("블루프린트:")
    st.write(f" 이름: {bp['name']}")
    st.write(" 부품:")
    if not bp['parts']:
        st.write("  (없음)")
    for i,p in enumerate(bp['parts']):
        st.write(f"  {i+1}. {p['name']} (mass={p['specs']['mass']}, power={p['specs']['power']})")
    st.write(f" 에너지 예산: {bp['power_budget']}")
    st.write(f" 상태: {bp['state']}")

def main():
    st.title("Custom Robot Builder - Web (MVP)")
    if 'blueprint' not in st.session_state:
        st.session_state.blueprint = json.loads(json.dumps(BLUEPRINT_DEFAULT))

    # 좌측: 부품 선택
    with st.sidebar:
        st.header("부품 카탈로그")
        for idx, part in enumerate(PARTS_CATALOG):
            if st.checkbox(part['name'], key=f"part_{idx}"):
                st.session_state.blueprint['parts'].append(part)
                st.success(f"추가: {part['name']}")
        if st.button("Export Blueprint"):
            pass
        if st.button("Reset Blueprint"):
            st.session_state.blueprint = json.loads(json.dumps(BLUEPRINT_DEFAULT))

    bp = st.session_state.blueprint
    render_blueprint(bp)

    # 메인: 간단 시뮬레이션
    if st.button("Run Simulation"):
        energy = 0.0
        steps = 5
        st.write("시뮬레이션 시작...")
        for s in range(steps):
            energy += 2.0 + max(0, len(bp['parts']) - 1) * 0.5
            st.write(f"Step {s+1}: energy={energy:.1f}")
        st.write("시뮬레이션 끝")
        bp['state'] = 'idle'
        bp['energy_used'] = energy
        st.session_state.blueprint = bp

if __name__ == '__main__':
    main()
