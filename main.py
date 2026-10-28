# -*- coding: utf-8 -*-
"""
Rocket Lab Beta - 한국어 변수명 버전
메인 애플리케이션: 실험 기록 관리와 물로켓 발사 시뮬레이션
패드/노트북 사이즈 고정, 스크롤 없음, 1100x700
로그인 기반의 로컬 기록 저장, 폴더/실험 관리, 삭제/즐겨찾기 가능
"""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import math
import json
import os
from datetime import datetime

# 저장소 경로 (로컬 계정/실험 기록)
STORE_DIR = os.path.join(os.path.expanduser("~"), ".rocket_beta_store")
STORE_FILE = os.path.join(STORE_DIR, "experiments_store.json")

# 1) 데이터 저장소 초기화 및 도구
def ensure_store():
    os.makedirs(STORE_DIR, exist_ok=True)
    if not os.path.exists(STORE_FILE):
        with open(STORE_FILE, "w") as f:
            json.dump({"users": {}}, f, indent=2)

def load_store():
    with open(STORE_FILE, "r") as f:
        return json.load(f)

def save_store(data):
    with open(STORE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ensure_user(store, username):
    if username not in store["users"]:
        store["users"][username] = {"Folders": {"Default": []}}
        save_store(store)

def get_user_folder_data(store, username):
    return store["users"][username]["Folders"]

# ---------------- Rocket 시뮬레이션 패널 ---------------- #
class RocketSimPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=640)
        self.grid_propagate(False)

        # 좌/우 레이아웃
        self.canvas_frame = ctk.CTkFrame(self, width=520)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=(10,10), pady=10)
        self.ctrl_frame = ctk.CTkFrame(self, width=220)
        self.ctrl_frame.grid(row=0, column=0, sticky="ns", padx=(10,0), pady=10)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._build_controls()
        self._build_canvas()

        # 파라미터(한국어 이름 변수)
        self.초기압력_bar = 2.0        # bar
        self.물질량_kg = 0.25          # kg
        self.건조질량_kg = 0.25        # kg
        self.중심비_cm = 0.50          # 비율(0~1)
        self.노즐구경_mm = 12          # mm

        # 물리상수
        self.m_dot = 0.02
        self.g = 9.81
        self.rho = 1.225
        self.Cd = 0.75
        self.본문지름_m = 0.06

        self.A_nozzle = math.pi * (((self.노즐구경_mm) / 1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2

        self.running = False
        self.paused = True
        self.t = 0.0
        self.vy = 0.0
        self.y = 0.0
        self.x = 0.0
        self.vx = 0.0

        self.state_history = []
        self.time_index = 0
        self.Hmax = 0.0
        self.max_time = 60.0
        self.scale = 40.0  # 1m ~ 40px

        self.update_param_displays()
        self.after_id = None

    def _build_controls(self):
        row = 0
        def add_slider(label, from_, to, init, unit, key, cmd=None):
            nonlocal row
            l = ctk.CTkLabel(self.ctrl_frame, text=label)
            l.grid(row=row, column=0, sticky="w", padx=6, pady=6)
            s = ctk.CTkSlider(self.ctrl_frame, from_=from_, to=to, number_of_steps=100, command=cmd)
            s.set(init)
            s.grid(row=row, column=1, sticky="ew", padx=6)
            val_lbl = ctk.CTkLabel(self.ctrl_frame, text=f"{init:.2f} {unit}")
            val_lbl.grid(row=row, column=2, sticky="w", padx=6)

            def on_step(val):
                v = float(val)
                val_lbl.configure(text=f"{v:.2f} {unit}")
                self._update_param(key, v)

            s.configure(command=on_step)
            self._param_widgets[key] = s
            return s

        self._param_widgets = {}

        self._초기압력_bar_slider = add_slider("초기 압력", 0.5, 5.0, self.초기압력_bar, "bar",
                                       "초기압력_bar", None)
        self._param_widgets["초기압력_bar"] = self._초기압력_bar_slider

        self._물질량_kg_slider = add_slider("물 질량", 0.05, 0.5, self.물질량_kg, "kg",
                                        "물질량_kg", None)
        self._param_widgets["물질량_kg"] = self._물질량_kg_slider

        self._건조질량_kg_slider = add_slider("건조 질량", 0.05, 0.5, self.건조질량_kg, "kg",
                                      "건조질량_kg", None)
        self._param_widgets["건조질량_kg"] = self._건조질량_kg_slider

        self._중심비_cm_slider = add_slider("중심 위치(0-1)", 0.4, 0.6, self.중심비_cm, "",
                                       "중심비_cm", None)
        self._param_widgets["중심비_cm"] = self._중심비_cm_slider

        self._노즐구경_mm_slider = add_slider("노즐 구경", 8, 20, self.노즐구경_mm, "mm",
                                       "노즐구경_mm", None)
        self._param_widgets["노즐구경_mm"] = self._노즐구경_mm_slider

        # Run / Pause / Reset
        self.run_btn = ctk.CTkButton(self.ctrl_frame, text="Run", command=self.start_sim)
        self.run_btn.grid(row=row, column=0, columnspan=3, pady=(12,6))
        row += 1

        self.pause_btn = ctk.CTkButton(self.ctrl_frame, text="Pause", command=self.pause_sim)
        self.pause_btn.grid(row=row, column=0, columnspan=1, pady=6)

        self.reset_btn = ctk.CTkButton(self.ctrl_frame, text="Reset", command=self.reset_sim)
        self.reset_btn.grid(row=row, column=2, columnspan=1, pady=6)
        row += 1

        # Speed control
        speed_lbl = ctk.CTkLabel(self.ctrl_frame, text="Speed (x)")
        speed_lbl.grid(row=row, column=0, sticky="w", padx=6)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_slider = ctk.CTkSlider(self.ctrl_frame, from_=0.25, to=4.0, number_of_steps=75,
                                          variable=self.speed_var, command=self._on_speed_change)
        self.speed_slider.grid(row=row, column=1, sticky="ew", padx=6)
        self.speed_val_lbl = ctk.CTkLabel(self.ctrl_frame, text="1.0x")
        self.speed_val_lbl.grid(row=row, column=2, sticky="w", padx=6)
        row += 1

        # Seek bar
        self.seek_scale = tk.Scale(self.ctrl_frame, from_=0, to=100, orient="horizontal",
                                   resolution=1, command=self._seek_to)
        self.seek_scale.grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        row += 1

        # Baseline 재설정
        self.init_btn = ctk.CTkButton(self.ctrl_frame, text="Baseline로 초기화",
                                      command=self.reset_params_to_baseline)
        self.init_btn.grid(row=row, column=0, columnspan=3, pady=6)

    def _build_canvas(self):
        canvas_w = 640
        canvas_h = 460
        self.canvas = ctk.CTkCanvas(self.canvas_frame, width=canvas_w, height=canvas_h, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.origin_x = canvas_w * 0.5
        self.origin_y = canvas_h - 20
        self.rocket_id = None
        self.path_ids = []
        self._draw_ground()

    def _draw_ground(self):
        self.canvas.create_rectangle(0, self.origin_y, self.canvas.winfo_width(), self.canvas.winfo_height(), fill="#e0e0e0", outline="")

    def _draw_rocket(self, x_px, y_px, angle_deg, color="tomato"):
        w = 24
        h = 60
        rad = math.radians(angle_deg)
        pts = [(-w/2, -h/2), (w/2, -h/2), (0, h/2)]
        rotated = []
        for (px, py) in pts:
            xr = px * math.cos(rad) - py * math.sin(rad)
            yr = px * math.sin(rad) + py * math.cos(rad)
            rotated.append((x_px + xr, y_px + yr))
        coords = []
        for p in rotated:
            coords.extend(p)
        if self.rocket_id is not None:
            self.canvas.delete(self.rocket_id)
        self.rocket_id = self.canvas.create_polygon(coords, fill=color, outline="black")

        nose_len = 20
        nose_x = x_px + nose_len * math.cos(rad)
        nose_y = y_px + nose_len * math.sin(rad)
        self.canvas.delete("nose")
        self.canvas.create_line(x_px, y_px, nose_x, nose_y, fill="orange", width=2, tags="nose")

    def _draw_path_point(self, x_m, y_m):
        px = self.origin_x + x_m * self.scale
        py = self.origin_y - y_m * self.scale
        self.path_ids.append(self.canvas.create_oval(px-1, py-1, px+1, py+1, fill="blue", outline="blue"))

    def _seek_to(self, val):
        idx = int(float(val))
        if idx < 0 or idx >= len(self.state_history):
            return
        st = self.state_history[idx]
        self.t = st['t']
        self.y = st['y']
        self.vy = st['vy']
        self.x = st['x']
        self.vx = st['vx']
        self.Hmax = max(self.Hmax, self.y)
        self.time_index = idx
        self._refresh_canvas_by_state(interpolate=False)

    def _on_speed_change(self, value):
        self.speed_val = float(value)
        self.speed_val_lbl.configure(text=f"{self.speed_var.get():.2f}x")

    def _refresh_canvas_by_state(self, interpolate=False):
        px = self.origin_x + self.x * self.scale
        py = self.origin_y - self.y * self.scale
        mass_ratio = (self.건조질량_kg + (self.물질량_kg - max(0.0, self.m_dot * self.t))) / max(1e-6, self.건조질량_kg + self.물질량_kg)
        color = "#33aa33" if mass_ratio < 1.2 else "#aa3333"
        angle = (self.중심비_cm - 0.5) * 18.0
        self._draw_rocket(px, py, angle_deg=angle, color=color)

        if not interpolate:
            self._draw_path_point(self.x, self.y)

        if py > self.origin_y + 20 or py < -20:
            self.running = False

    def _initialize_sim(self):
        self.t = 0.0
        self.vy = 0.0
        self.y = 0.0
        self.x = 0.0
        self.vx = 0.0
        self.Hmax = 0.0
        self.state_history = []
        self.time_index = 0
        self._refresh_canvas_by_state()

    def reset_params_to_baseline(self):
        self.초기압력_bar = 2.0
        self.물질량_kg = 0.25
        self.건조질량_kg = 0.25
        self.중심비_cm = 0.50
        self.노즐구경_mm = 12
        # 슬라이더 초기화
        if hasattr(self, "_param_widgets"):
            if "초기압력_bar" in self._param_widgets:
                self._param_widgets["초기압력_bar"].set(2.0)
            if "물질량_kg" in self._param_widgets:
                self._param_widgets["물질량_kg"].set(0.25)
            if "건조질량_kg" in self._param_widgets:
                self._param_widgets["건조질량_kg"].set(0.25)
            if "중심비_cm" in self._param_widgets:
                self._param_widgets["중심비_cm"].set(0.50)
            if "노즐구경_mm" in self._param_widgets:
                self._param_widgets["노즐구경_mm"].set(12)
        self.A_nozzle = math.pi * (((self.노즐구경_mm)/1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2
        self.update_param_displays()

    def update_param_displays(self):
        # 슬라이더와 디스플레이의 동기화(미사용 시 pass)
        pass

    def _update_param(self, key, value):
        if key == "초기압력_bar":
            self.초기압력_bar = float(value)
        elif key == "물질량_kg":
            self.물질량_kg = float(value)
        elif key == "건조질량_kg":
            self.건조질량_kg = float(value)
        elif key == "중심비_cm":
            self.중심비_cm = float(value)
        elif key == "노즐구경_mm":
            self.노즐구경_mm = float(value)
            self.A_nozzle = math.pi * (((self.노즐구경_mm)/1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2

    # 시뮬레이션 흐름
    def start_sim(self):
        self.A_nozzle = math.pi * (((self.노즐구경_mm)/1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2
        self._initialize_sim()
        self.running = True
        self.paused = False
        self._simulation_loop()

    def pause_sim(self):
        self.paused = True
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    def reset_sim(self):
        self._initialize_sim()
        self.running = False
        self.paused = True
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.seek_scale.set(0)

    def _simulate_step(self, dt):
        mw_remain = max(0.0, self.물질량_kg - self.m_dot * self.t)
        if mw_remain > 0 and self.물질량_kg > 0:
            P_inside = (self.초기압력_bar * 1e5) * (mw_remain / max(1e-6, self.물질량_kg))
            F_thrust = P_inside * self.A_nozzle
        else:
            F_thrust = 0.0

        m = self.건조질량_kg + mw_remain
        v = math.hypot(self.vx, self.vy)
        D = 0.5 * self.rho * v * v * self.Cd * self.A_drag
        a = (F_thrust - D - m * self.g) / max(1e-6, m)

        self.vy += a * dt
        self.y += self.vy * dt
        self.x += self.vx * dt

        self.t += dt
        self.max_time = max(self.max_time, self.t)
        self.Hmax = max(self.Hmax, self.y)

        self.state_history.append({"t": self.t, "x": self.x, "y": self.y, "vx": self.vx, "vy": self.vy})

        if self.y <= 0.0 and self.t > 0.05:
            self.running = False

    def _simulation_loop(self):
        if not self.running:
            return
        dt = 0.02 * max(0.25, min(4.0, getattr(self, "speed_var", tk.DoubleVar(value=1.0)).get()))
        self._simulate_step(dt)

        px = self.origin_x + self.x * self.scale
        py = self.origin_y - self.y * self.scale
        angle = (self.중심비_cm - 0.5) * 18.0
        self._draw_rocket(px, py, angle_deg=angle)

        if py < self.origin_y + 20:
            self._draw_path_point(self.x, self.y)

        idx = min(len(self.state_history)-1, int(self.t / dt))
        self.seek_scale.config(to=max(100, int(self.t/0.02)))
        self.seek_scale.set(int(self.t*100))

        delay = int(dt * 1000)
        self.after_id = self.after(delay, self._simulation_loop)

        if not self.running or self.y <= 0.0:
            self.running = False

    # 외부 API
    def load_params(self, params):
        if "초기압력_bar" in params: self.초기압력_bar = float(params["초기압력_bar"])
        if "물질량_kg" in params: self.물질량_kg = float(params["물질량_kg"])
        if "건조질량_kg" in params: self.건조질량_kg = float(params["건조질량_kg"])
        if "중심비_cm" in params: self.중심비_cm = float(params["중심비_cm"])
        if "노즐구경_mm" in params: self.노즐구경_mm = float(params["노즐구경_mm"])
        self.A_nozzle = math.pi * (((self.노즐구경_mm)/1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2
        self.update_all()

    def get_current_params(self):
        return {
            "초기압력_bar": self.초기압력_bar,
            "물질량_kg": self.물질량_kg,
            "건조질량_kg": self.건조질량_kg,
            "중심비_cm": self.중심비_cm,
            "노즐구경_mm": self.노즐구경_mm
        }

    def update_all(self):
        self.A_nozzle = math.pi * (((self.노즐구경_mm)/1000.0) / 2.0) ** 2
        self.A_drag = math.pi * (self.본문지름_m / 2.0) ** 2

# ---------------- Records Panel (실험 기록 관리) ---------------- #
class RecordsPanel(ctk.CTkFrame):
    def __init__(self, master, sim_panel: RocketSimPanel, **kwargs):
        super().__init__(master, **kwargs)
        self.sim_panel = sim_panel
        self.configure(width=360)
        self.grid_propagate(False)

        ensure_store()
        self.store = load_store()
        self.current_user = None
        self.tree = None

        self._build_ui()

    def _build_ui(self):
        # 로그인 영역
        login_frame = ctk.CTkFrame(self, height=60)
        login_frame.pack(fill="x", pady=(6,6), padx=6)

        tk.Label(login_frame, text="Username:", width=12, anchor="w").pack(side="left", padx=(6,2))
        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(login_frame, textvariable=self.username_var, width=20)
        self.username_entry.pack(side="left", padx=(0,6))
        login_btn = ctk.CTkButton(login_frame, text="Login", command=self._login)
        login_btn.pack(side="left", padx=6)
        logout_btn = ctk.CTkButton(login_frame, text="Logout", command=self._logout)
        logout_btn.pack(side="left", padx=6)

        self.status_label = tk.Label(login_frame, text="Not logged in", fg="red")
        self.status_label.pack(side="right", padx=6)

        # 폴더/실험 관리 영역
        management_frame = ctk.CTkFrame(self, height=480)
        management_frame.pack(fill="both", expand=True, padx=6, pady=(0,6))

        # 폴더 생성
        folder_row = ctk.CTkFrame(management_frame)
        folder_row.pack(fill="x", pady=4)
        tk.Label(folder_row, text="New Folder name:").pack(side="left", padx=(6,2))
        self.new_folder_var = tk.StringVar()
        self.new_folder_entry = tk.Entry(folder_row, textvariable=self.new_folder_var, width=16)
        self.new_folder_entry.pack(side="left", padx=(0,6))
        new_folder_btn = ctk.CTkButton(folder_row, text="Create Folder", command=self._create_folder)
        new_folder_btn.pack(side="left", padx=6)

        # 폴더 드롭다운 + 이동
        move_row = ctk.CTkFrame(management_frame)
        move_row.pack(fill="x", pady=4)
        tk.Label(move_row, text="Move to folder:").pack(side="left", padx=(6,2))
        self.move_folder_var = tk.StringVar()
        self.move_folder_cb = ttk.Combobox(move_row, textvariable=self.move_folder_var, state="readonly", width=14)
        self.move_folder_cb.pack(side="left", padx=(0,6))
        move_btn = ctk.CTkButton(move_row, text="Move Selected", command=self._move_selected)
        move_btn.pack(side="left", padx=6)

        # 실험 목록(Tree)
        tree_frame = ctk.CTkFrame(management_frame)
        tree_frame.pack(fill="both", expand=True, pady=(6,0))
        self.tree = ttk.Treeview(tree_frame, columns=("name","ts","fav"), show="tree headings", height=14)
        self.tree.heading("#0", text="Experiment")
        self.tree.heading("name", text="Name")
        self.tree.heading("ts", text="Timestamp")
        self.tree.heading("fav", text="Favorite")
        self.tree.column("#0", width=180)
        self.tree.column("name", width=120)
        self.tree.column("ts", width=120)
        self.tree.column("fav", width=60)
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        # 버튼들
        btn_row = ctk.CTkFrame(management_frame)
        btn_row.pack(fill="x", pady=6)
        self.run_selected_btn = ctk.CTkButton(btn_row, text="Run Selected", command=self._run_selected)
        self.run_selected_btn.pack(side="left", padx=6)
        self.del_selected_btn = ctk.CTkButton(btn_row, text="Delete Selected", command=self._delete_selected)
        self.del_selected_btn.pack(side="left", padx=6)
        self.fav_selected_btn = ctk.CTkButton(btn_row, text="Toggle Favorite", command=self._toggle_favorite)
        self.fav_selected_btn.pack(side="left", padx=6)
        self.refresh_btn = ctk.CTkButton(btn_row, text="Refresh List", command=self._refresh_tree)
        self.refresh_btn.pack(side="left", padx=6)

        # 초기 화면 채우기
        self._refresh_tree()

    def _login(self):
        username = self.username_var.get().strip()
        if not username:
            return
        ensure_store()
        self.store = load_store()
        ensure_user(self.store, username)
        self.current_user = username
        self.status_label.config(text=f"Logged in as {username}", fg="green")
        self._refresh_folder_options()
        self._refresh_tree()

    def _logout(self):
        self.current_user = None
        self.status_label.config(text="Not logged in", fg="red")

    def _refresh_folder_options(self):
        if not self.current_user:
            return
        user_data = self.store["users"][self.current_user]
        folders = list(user_data.get("Folders", {"Default": []}).keys())
        if "Default" not in folders:
            folders.insert(0, "Default")
            user_data.setdefault("Folders", {})["Default"] = []
        self.move_folder_cb['values'] = folders
        if folders:
            self.move_folder_var.set(folders[0])

    def _create_folder(self):
        if not self.current_user:
            return
        name = self.new_folder_var.get().strip()
        if not name:
            return
        self.store = load_store()
        user = self.current_user
        self.store["users"][user].setdefault("Folders", {})
        if name not in self.store["users"][user]["Folders"]:
            self.store["users"][user]["Folders"][name] = []
            save_store(self.store)
        self.new_folder_var.set("")
        self._refresh_folder_options()
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current_user:
            return
        user = self.current_user
        self.store = load_store()
        folders = self.store["users"][user].get("Folders", {})
        for folder, experiments in folders.items():
            fid = self.tree.insert("", "end", text=f"[Folder] {folder}", open=True)
            for exp in experiments:
                exp_text = exp.get("name","Unnamed")
                ts = exp.get("timestamp", "")
                fav = "★" if exp.get("favorite", False) else ""
                self.tree.insert(fid, "end", text=exp_text, values=(exp_text, ts, fav))
        self._update_folder_options_from_store()

    def _update_folder_options_from_store(self):
        self._refresh_folder_options()

    def _get_selected_experiment(self):
        item = self.tree.selection()
        if not item:
            return None
        item_id = item[0]
        parent = self.tree.parent(item_id)
        if parent:  # 실험 노드
            name = self.tree.item(item_id, "text")
            user = self.current_user
            store = load_store()
            folders = store["users"][user]["Folders"]
            for folder, exps in folders.items():
                for ex in exps:
                    if ex.get("name") == name:
                        return ex
        return None

    def _run_selected(self):
        exp = self._get_selected_experiment()
        if not exp:
            return
        params = exp.get("params", {})
        self.sim_panel.load_params(params)
        self.sim_panel.start_sim()

    def _delete_selected(self):
        exp = self._get_selected_experiment()
        if not exp:
            return
        user = self.current_user
        if not user:
            return
        store = load_store()
        folders = store["users"][user]["Folders"]
        for folder, exps in list(folders.items()):
            new_list = [e for e in exps if e.get("name") != exp.get("name")]
            folders[folder] = new_list
        save_store(store)
        self._refresh_tree()

    def _toggle_favorite(self):
        exp = self._get_selected_experiment()
        if not exp:
            return
        exp["favorite"] = not exp.get("favorite", False)
        store = load_store()
        user = self.current_user
        for folder, exps in store["users"][user]["Folders"].items():
            for e in exps:
                if e.get("name") == exp.get("name"):
                    e["favorite"] = exp["favorite"]
        save_store(store)
        self._refresh_tree()

    def _move_selected(self):
        if not self.current_user:
            return
        dest = self.move_folder_var.get()
        if not dest:
            return
        exp = self._get_selected_experiment()
        if not exp:
            return
        user = self.current_user
        store = load_store()
        folders = store["users"][user]["Folders"]
        for folder, exps in list(folders.items()):
            if exp in exps:
                folders[folder].remove(exp)
        folders[dest].append(exp)
        save_store(store)
        self._refresh_tree()

    # 현재 파라미터로 새 실험 저장
    def save_current_experiment(self, name, folder_name="Default"):
        if not self.current_user:
            return
        store = load_store()
        user = self.current_user
        exp = {
            "name": name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "params": self.sim_panel.get_current_params(),
            "favorite": False
        }
        folders = store["users"][user].setdefault("Folders", {})
        folder = folder_name if folder_name in folders else "Default"
        folders.setdefault(folder, [])
        folders[folder].append(exp)
        save_store(store)
        self._refresh_tree()

# ---------------- 메인 애플리케이션 ---------------- #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rocket Lab Beta — 시뮬레이션 + 기록 시스템 (한국어 변수)")
        self.geometry("1100x700")  # 패드/노트북에 맞춘 고정 사이즈
        self.resizable(False, False)

        # 좌: 기록, 우: 시뮬레이션
        self.records_panel = RecordsPanel(self, sim_panel=None)
        self.sim_panel = RocketSimPanel(self)
        self.records_panel.sim_panel = self.sim_panel

        self.records_panel.grid(row=0, column=0, sticky="ns", padx=(6,6), pady=6)
        self.sim_panel.grid(row=0, column=1, sticky="nsew", padx=(6,6), pady=6)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # 왼쪽 고정
        self.grid_columnconfigure(1, weight=1)  # 오른쪽 확장

        ensure_store()
        self._init_ui_state()

    def _init_ui_state(self):
        self.sim_panel._initialize_sim()
        self.sim_panel.reset_sim()
        self._build_header()

    def _build_header(self):
        self.title("Rocket Lab Beta — 시뮬레이션 + 기록 시스템")

# Run
if __name__ == "__main__":
    app = App()
    app.mainloop()
