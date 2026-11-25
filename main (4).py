#!/usr/bin/env python3
# MVP: Custom Robot Builder - Desktop UI with CustomTkinter fallback

import json
import time
import os
from typing import List, Dict, Any

try:
    import customtkinter as ct
    HAS_CT = True
except Exception:
    ct = None
    HAS_CT = False

import tkinter as tk
from tkinter import filedialog

# Catalog
PARTS_CATALOG = [
    {"id": "frame", "name": "Base Frame", "specs": {"mass":1.0, "power":0.0}},
    {"id": "gripper", "name": "Gripper", "specs": {"mass":0.5, "power":5.0}},
    {"id": "arm", "name": "Arm Actuator", "specs": {"mass":0.8, "power":7.0}},
    {"id": "vision", "name": "Vision Sensor", "specs": {"mass":0.2, "power":2.0}},
    {"id": "battery", "name": "Li-ion Battery", "specs": {"mass":0.6, "power":-1.0, "capacity": 100}},
]

BLUEPRINT_DEFAULT = {"name": "Untitled Robot", "parts": [], "power_budget": 100, "state": "idle", "log": []}

class RobotModel:
    def __init__(self):
        self.name = BLUEPRINT_DEFAULT["name"]
        self.parts: List[Dict[str, Any]] = []
        self.power_budget = BLUEPRINT_DEFAULT["power_budget"]
        self.energy_used = 0.0
        self.tasks_remaining = 5
        self.state = "idle"

    def to_dict(self):
        return {
            "name": self.name,
            "parts": self.parts,
            "power_budget": self.power_budget,
            "energy_used": self.energy_used,
            "tasks_remaining": self.tasks_remaining,
            "state": self.state
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]):
        r = RobotModel()
        r.name = d.get("name", "Untitled Robot")
        r.parts = d.get("parts", [])
        r.power_budget = d.get("power_budget", 100)
        r.energy_used = d.get("energy_used", 0.0)
        r.tasks_remaining = d.get("tasks_remaining", 5)
        r.state = d.get("state", "idle")
        return r

class RobotWorkshopApp:
    def __init__(self):
        self.root = ct.CTk() if HAS_CT else tk.Tk()
        self.root.title("Custom Robot Builder - MVP")
        self.root.geometry("1024x640")

        self.robot = RobotModel()
        self.simulating = False
        self.sim_tick_ms = 350

        self.part_listbox = None
        self.canvas = None
        self.log_widget = None
        self.name_entry = None
        self.run_button = None
        self.step_button = None
        self.reset_button = None

        self._build_ui()

    def _build_ui(self):
        left_frame = (ct.CTkFrame(self.root) if HAS_CT else tk.Frame(self.root, width=260, height=640, bg="white"))
        left_frame.pack(side="left", fill="y", padx=6, pady=6)

        self._label(left_frame, "부품 카탈로그")
        names = [p["name"] for p in PARTS_CATALOG]
        self.part_listbox = self._list(left_frame, names)

        self._button(left_frame, "추가", self._on_add_part)
        self._button(left_frame, "제거", self._on_remove_part)

        right_frame = (ct.CTkFrame(self.root) if HAS_CT else tk.Frame(self.root, bg="white"))
        right_frame.pack(side="right", fill="both", expand=True, padx=6, pady=6)

        self._label(right_frame, "로봇 뷰(블루프린트)")
        self.canvas = self._canvas(right_frame, 420, 360)

        log_frame = self._make_frame(right_frame, width=420, height=200, side="bottom")
        self._label(log_frame, "시뮬레이션 로그")
        self.log_widget = tk.Text(log_frame, height=10, wrap="word")
        self.log_widget.pack(fill="both", expand=True)

        bottom = self._make_frame(self.root, width=1024, height=120, side="bottom")
        self.name_entry = self._entry(bottom, "로봇 이름 (예: 작업용 로봇 A)")
        self.run_button = self._button(bottom, "Run", self._on_run)
        self.step_button = self._button(bottom, "Step", self._on_step)
        self.reset_button = self._button(bottom, "Reset", self._on_reset)
        self._button(bottom, "Export Blueprint", self._export_blueprint)
        self._button(bottom, "Import Blueprint", self._import_blueprint)

        self._draw_robot()

        self.root.mainloop()

    # UI helpers
    def _make_frame(self, parent, width, height, side="left"):
        if HAS_CT:
            frame = ct.CTkFrame(master=parent)
        else:
            frame = tk.Frame(master=parent, width=width, height=height, bg="white")
        frame.pack(side=side, fill="both", expand=False, padx=6, pady=6)
        return frame

    def _label(self, parent, text):
        if HAS_CT:
            lbl = ct.CTkLabel(master=parent, text=text)
        else:
            lbl = tk.Label(master=parent, text=text, anchor="w")
        lbl.pack(pady=6)
        return lbl

    def _list(self, parent, items: List[str]):
        lst = tk.Listbox(master=parent, height=10)
        for it in items:
            lst.insert(tk.END, it)
        lst.pack(padx=6, pady=6, fill="both", expand=True)
        return lst

    def _button(self, parent, text, command):
        btn = tk.Button(master=parent, text=text, command=command)
        btn.pack(pady=6)
        return btn

    def _entry(self, parent, placeholder=""):
        entry = tk.Entry(master=parent)
        entry.insert(0, placeholder)
        entry.pack(padx=6, pady=6, fill="x")
        return entry

    def _canvas(self, parent, w, h):
        canvas = tk.Canvas(master=parent, width=w, height=h, bg="white")
        canvas.pack(padx=6, pady=6)
        return canvas

    # actions
    def _on_add_part(self):
        idxs = self.part_listbox.curselection()
        if not idxs:
            return
        idx = int(idxs[0])
        part = PARTS_CATALOG[idx]
        self.robot.parts.append(part)
        self._log(f"Added part: {part['name']}")
        self._draw_robot()

    def _on_remove_part(self):
        idxs = self.part_listbox.curselection()
        if not idxs:
            return
        idx = int(idxs[0])
        if idx < len(self.robot.parts):
            removed = self.robot.parts.pop(idx)
            self._log(f"Removed part: {removed['name']}")
            self._draw_robot()

    def _on_run(self):
        if self.simulating:
            self._log("Already running.")
            return
        self.simulating = True
        self.robot.state = "running"
        self._log("Simulation started.")
        self._simulate_step()

    def _on_step(self):
        self._simulate_step()

    def _on_reset(self):
        self.simulating = False
        self.robot = RobotModel()
        self._log("Simulation reset.")
        self._draw_robot()

    def _simulate_step(self):
        if not self.simulating:
            return
        if self.robot.tasks_remaining <= 0:
            self._log("모든 의뢰를 완료했습니다.")
            self.simulating = False
            self.robot.state = "idle"
            self._draw_robot()
            return
        energy_cost = 2.0 + max(0.0, len(self.robot.parts) - 1) * 0.5
        self.robot.energy_used += energy_cost
        self.robot.tasks_remaining -= 1
        self.robot.state = "running"
        self._log(f"Step complete. 남은 의뢰: {self.robot.tasks_remaining}, 에너지 소모: {energy_cost:.1f}")
        self._draw_robot()
        self.root.after(self.sim_tick_ms, self._simulate_step)

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.robot.log.append(line)
        if self.log_widget:
            self.log_widget.insert(tk.END, line + "\n")
            self.log_widget.see(tk.END)

    def _draw_robot(self):
        self.canvas.delete("all")
        w, h = 420, 360
        cx, cy = 210, 180
        # body
        self.canvas.create_rectangle(cx-80, cy-40, cx+80, cy+40, fill="#c0c0c0", outline="black")
        # parts
        for i, p in enumerate(self.robot.parts):
            y = cy - 60 - i * 24
            self.canvas.create_oval(cx - 120, y, cx - 100, y + 20, fill="#8fd3ff", outline="black")
            self.canvas.create_text(cx - 110, y + 10, text=p["name"].split()[0], font=("Arial", 8))
        # energy bar
        ratio = min(1.0, max(0.0, self.robot.energy_used / max(1.0, self.robot.power_budget)))
        self.canvas.create_rectangle(10, 10, 210, 28, fill="#e0e0e0", outline="black")
        self.canvas.create_rectangle(10, 10, 10 + 200 * ratio, 28, fill="#4caf50", outline="")
        self.canvas.create_text(110, 19, text=f"Energy {self.robot.energy_used:.1f}/{self.robot.power_budget}", fill="black", font=("Arial", 9))
        self.canvas.create_text(cx, 320, text=f"상태: {self.robot.state} | 남은 의뢰: {self.robot.tasks_remaining}", font=("Arial", 10))
        name = self.name_entry.get() if self.name_entry else self.robot.name
        self.robot.name = name

    def _export_blueprint(self):
        blueprint = self.robot.to_dict()
        name = (self.robot.name or "robot").replace(" ", "_")
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{name}_blueprint.json", title="Export Blueprint")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, indent=2, ensure_ascii=False)
        self._log(f"Blueprint exported as {path}")

    def _import_blueprint(self):
        path = filedialog.askopenfilename(title="Import Blueprint", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.robot = RobotModel.from_dict(data)
            self._log(f"Blueprint loaded from {path}")
            self._draw_robot()
        except Exception as e:
            self._log(f"Blueprint load failed: {e}")

def main():
    app = RobotWorkshopApp()

if __name__ == "__main__":
    main()
