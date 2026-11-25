# Minimal Streamlit app for the improved Robot Builder MVP (web UI) with Fleet Simulation
import streamlit as st
import json
import os
import matplotlib.pyplot as plt
from io import BytesIO

PARTS_CATALOG = [
    {"id": "frame", "name": "Base Frame", "specs": {"mass":1.0, "power":0.0}},
    {"id": "gripper", "name": "Gripper", "specs": {"mass":0.5, "power":5.0}},
    {"id": "arm", "name": "Arm Actuator", "specs": {"mass":0.8, "power":7.0}},
    {"id": "vision", "name": "Vision Sensor", "specs": {"mass":0.2, "power":2.0}},
    {"id": "battery", "name": "Li-ion Battery", "specs": {"mass":0.6, "power":-1.0, "capacity":100}},
]

BLUEPRINT_DEFAULT = {
    "name": "Untitled Robot Fleet",
    "fleet": [
        {"robot_id": 1, "name": "Robot-1", "parts": [], "power_budget": 100, "state": "idle", "energy_used": 0.0, "tasks_remaining": 5},
        {"robot_id": 2, "name": "Robot-2", "parts": [], "power_budget": 100, "state": "idle", "energy_used": 0.0, "tasks_remaining": 5}
    ],
    "global": {"simulation_tick": 0},
    "log": []
}
BLUEPRINT_DIR = "blueprints"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def save_blueprint(bp, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bp, f, indent=2, ensure_ascii=False)


def load_blueprint(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_fleet(bp):
    # Simple 2D fleet visualization using matplotlib
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    # Fleet base line
    ax.plot([0, 10], [1.5, 1.5], color="#888", lw=2)
    # Robots as boxes
    for i, r in enumerate(bp.get("fleet", [])):
        x = 1 + i * 4
        y = 0.8
        ax.add_patch(plt.Rectangle((x, y), 2, 1.2, fill=True, color="#c0e6ff", ec="black"))
        ax.text(x + 1, y + 0.6, r.get("name", f"Robot-{r.get('robot_id', i+1)}"), ha="center", va="center", fontsize=8)
        # status
        ax.text(x + 1, y + 0.25, f"{r.get('state','idle')}", ha="center", va="center", fontsize=7)
    fig.tight_layout()
    return fig


def main():
    st.set_page_config(page_title="Custom Robot Builder - Fleet MVP", layout="wide")
    st.title("Custom Robot Builder - Fleet MVP (Web UI)")

    if "blueprint" not in st.session_state:
        st.session_state.blueprint = json.loads(json.dumps(BLUEPRINT_DEFAULT))

    bp = st.session_state.blueprint

    # Left: Fleet management
    with st.sidebar:
        st.header("병렬 로봇 관리")
        fleets = bp.get("fleet", [])
        # Add robot
        if st.button("Add Robot to Fleet"):
            rid = max([r.get("robot_id", 0) for r in fleets] or [0]) + 1
            fleets.append({"robot_id": rid, "name": f"Robot-{rid}", "parts": [], "power_budget": 100, "state": "idle", "energy_used": 0.0, "tasks_remaining": 5})
            bp["fleet"] = fleets
            st.experimental_rerun()
        # Show each robot panel
        for idx, r in enumerate(fleets):
            with st.expander(f"로봇 {r.get('name','')}"):
                new_name = st.text_input("이름", value=r.get("name","Robot"+str(r.get('robot_id', idx+1))))
                if new_name != r.get("name"):
                    r["name"] = new_name
                new_budget = st.slider("에너지 예산", min_value=0, max_value=500, value=r.get("power_budget", 100))
                r["power_budget"] = new_budget
                # parts quick add/remove
                st.markdown("부품:")
                current = {p["id"] for p in r.get("parts", [])}
                for p in PARTS_CATALOG:
                    if p["id"] in current:
                        if st.button(f"Remove {p['name']}", key=f"rm_{idx}_{p['id']}"):
                            r["parts"].remove(p)
                            st.experimental_rerun()
                    else:
                        if st.button(f"Add {p['name']}", key=f"add_{idx}_{p['id']}"):
                            r["parts"].append(p)
                            st.experimental_rerun()

                st.write(f"State: {r.get('state','idle')}")
                if st.button(f"Remove Robot {r.get('name','Robot')}", key=f"del_{idx}"):
                    fleets.pop(idx)
                    bp["fleet"] = fleets
                    st.experimental_rerun()
        st.markdown("---")
        # Scenario control
        scenario = st.selectbox("시나리오 선택", ["Single Robot", "Dual Collaboration", "Three Robot Line"])
        st.session_state.scenario = scenario
        if st.button("Export Fleet Blueprint"):
            ensure_dir(BLUEPRINT_DIR)
            path = os.path.join(BLUEPRINT_DIR, f"fleet_blueprint_{scenario.replace(' ','_')}.json")
            save_blueprint(bp, path)
            st.success(f"Fleet blueprint saved: {path}")
        if st.button("Reset Fleet Blueprint"):
            st.session_state.blueprint = json.loads(json.dumps(BLUEPRINT_DEFAULT))
            st.experimental_rerun()
        st.markdown("---")
        uploaded = st.file_uploader("Load fleet blueprint JSON", type=["json"])
        if uploaded is not None:
            content = json.load(uploaded)
            st.session_state.blueprint = content
            st.experimental_rerun()

    # Main: Fleet overview + visualization + KPI
    st.subheader(" fleet overview ")
    st.pyplot(draw_fleet(bp))

    # KPI board
    total_energy = sum(r.get("energy_used",0.0) for r in bp.get("fleet", []))
    total_tasks = sum(r.get("tasks_remaining",0) for r in bp.get("fleet", []))
    st.metric(label="전체 에너지 사용량", value=f"{total_energy:.1f}")
    st.metric(label="전체 남은 의뢰 수", value=total_tasks)

    # Per-robot stats table
    st.subheader("로봇별 상태")
    table_data = []
    for r in bp.get("fleet", []):
        table_data.append({
            "Robot": r.get("name","Robot"),
            "Parts": ",".join([p["name"] for p in r.get("parts", [])]),
            "Energy": r.get("energy_used",0.0),
            "Budget": r.get("power_budget", 100),
            "Remaining": r.get("tasks_remaining",0),
            "State": r.get("state","idle"),
        })
    st.table(table_data)

    # Run controls
    st.subheader("시뮬레이션 컨트롤")
    if st.button("Run Fleet"):
        # simple fleet step: each robot consumes energy and processes one task if available
        for r in bp.get("fleet", []):
            if r.get("tasks_remaining",0) > 0:
                energy_cost = 2.0 + max(0, len(r.get("parts", [])) - 1) * 0.5
                r["energy_used"] = r.get("energy_used",0.0) + energy_cost
                r["tasks_remaining"] = max(0, r["tasks_remaining"] - 1)
                r["state"] = "running"
        bp["global"]["simulation_tick"] = bp["global"].get("simulation_tick",0) + 1
        st.session_state.blueprint = bp
        st.experimental_rerun()
    if st.button("Step Fleet"):
        for r in bp.get("fleet", []):
            if r.get("tasks_remaining",0) > 0:
                energy_cost = 2.0 + max(0, len(r.get("parts", [])) - 1) * 0.5
                r["energy_used"] = r.get("energy_used",0.0) + energy_cost
                r["tasks_remaining"] = max(0, r["tasks_remaining"] - 1)
                r["state"] = "running"
        st.session_state.blueprint = bp
        st.experimental_rerun()
    if st.button("Reset Fleet"):
        st.session_state.blueprint = json.loads(json.dumps(BLUEPRINT_DEFAULT))
        st.experimental_rerun()

    st.subheader("로그")
    if "logs" not in st.session_state:
        st.session_state.logs = []
    for line in bp.get("log", [])[-20:]:
        st.write(line)

if __name__ == "__main__":
    main()
