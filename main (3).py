import math
import time
import tkinter as tk

# Requirement: customtkinter
import customtkinter as CTk

# Global mapping of difficulties
DIFF_KR = ["상", "중", "하"]  # UI labels (Top to Bottom)
DIFF_INTERNAL = {"상": "Hard", "중": "Medium", "하": "Easy"}

class Robot3DOF:
    def __init__(self):
        self.base = (320, 360)
        self.l1 = 120
        self.l2 = 90
        self.l3 = 60
        self.theta1 = math.radians(60)
        self.theta2 = math.radians(-25)
        self.theta3 = 0.0
        self.phi_target = 0.0
        self.energy = 0.0
        self.picked = False

    def forward(self):
        x0, y0 = self.base
        x1 = x0 + self.l1 * math.cos(self.theta1)
        y1 = y0 - self.l1 * math.sin(self.theta1)
        x2 = x1 + self.l2 * math.cos(self.theta1 + self.theta2)
        y2 = y1 - self.l2 * math.sin(self.theta1 + self.theta2)
        x3 = x2 + self.l3 * math.cos(self.theta1 + self.theta2 + self.theta3)
        y3 = y2 - self.l3 * math.sin(self.theta1 + self.theta2 + self.theta3)
        return (x0, y0), (x1, y1), (x2, y2), (x3, y3)

    def ik_solve(self, target):
        px, py = target
        x = px
        y = -py
        L1, L2, L3 = self.l1, self.l2, self.l3
        d = math.hypot(x, y)
        if d > (L1 + L2 + L3) or d < abs(L1 - L2 - L3):
            return None, None, None
        cos2 = (x*x + y*y - L1*L1 - L2*L2) / (2 * L1 * L2)
        cos2 = max(-1.0, min(1.0, cos2))
        sin2 = math.sqrt(max(0.0, 1 - cos2*cos2))
        t2 = math.atan2(sin2, cos2)
        k1 = L1 + L2 * cos2
        k2 = L2 * sin2
        t1 = math.atan2(y, x) - math.atan2(k2, k1)
        t3 = self.phi_target - (t1 + t2)
        return t1, t2, t3

    def set_angles(self, t1, t2, t3):
        self.energy += (abs(t1 - self.theta1) + abs(t2 - self.theta2) + abs(t3 - self.theta3)) * 2.0
        self.theta1 = t1
        self.theta2 = t2
        self.theta3 = t3

    def reset(self):
        self.theta1 = math.radians(60)
        self.theta2 = math.radians(-25)
        self.theta3 = 0.0
        self.phi_target = 0.0
        self.energy = 0.0
        self.picked = False

class SimpleAIAssistant:
    def __init__(self, parent, initial_credits=2):
        self.parent = parent
        self.credits = initial_credits
        self.memory = {}

    def can_afford(self, cost=1):
        return self.credits >= cost

    def spend(self, cost=1):
        if self.can_afford(cost):
            self.credits -= cost
            self.parent.ai_credits_label.config(text=f"AI 크레딧: {self.credits}")
            return True
        return False

    def earn(self, amount=2):
        self.credits += amount
        self.parent.ai_credits_label.config(text=f"AI 크레딧: {self.credits}")

    def respond_to(self, text):
        t = text.strip().lower()
        if not t:
            resp = "입력 내용을 확인할 수 없어요."
        elif any(k in t for k in ["무엇을 만들어", "의도"]):
            idea = self.memory.get("intent", "로봇의 기본 의도는 사용자가 필요로 하는 기능을 도출하는 것")
            resp = f"현재 의도 추정: {idea}. 필요하면 구체적인 의도 정보를 플레이어가 입력하면 더 나은 조합을 제시할 수 있어요."
        elif any(k in t for k in ["도와줘", "힌트"]):
            resp = "힌트: Easy는 구체적 제약을 따르는 의뢰, Medium은 중간 정도의 제약, Hard는 의도 추론이 필요합니다."
        else:
            resp = "AI: 간단한 의도나 로봇 기능을 입력해 주세요. 예: '나는 돌아다닐 수 있는 로봇' 같은 형식."
        self.parent.ai_chat_text.config(state=tk.NORMAL)
        self.parent.ai_chat_text.insert(tk.END, f"AI: {resp}\n")
        self.parent.ai_chat_text.see(tk.END)
        self.parent.ai_chat_text.config(state=tk.DISABLED)
        self.memory["intent"] = text
        return resp

    def provide_hint(self, difficulty, mission_state):
        if not self.can_afford(1):
            return "크레딧이 부족합니다. 임무를 성공시키면 AI 크레딧이 증가합니다."
        self.spend(1)
        if difficulty == "Easy":
            return "힌트: 팔의 각도 조합을 간단히 시도하고 피킹 루프를 안정화하세요."
        elif difficulty == "Medium":
            return "힌트: 의뢰 요건이 모호할 때는 목표 우선순위를 정하고 로봇 인터페이스를 정리해 보세요."
        else:
            return "힌트: 의도 추정을 돕기 위해, 손님의 목표를 여러 가정으로 나눠 시도해 보세요."

class App(CTk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Custom Robot Builder - MVP (Beta)")
        self.geometry("1100x700")
        self.resizable(False, False)

        self.diff_index = 2  # 시작은 하(Easy)
        self.difficulty_internal = DIFF_INTERNAL[DIFF_KR[self.diff_index]]
        self.robot = Robot3DOF()
        self.ai = SimpleAIAssistant(self, initial_credits=2)
        self.player_credits = 0

        self.sim_running = False
        self.sim_target = (860, 260)
        self.drop_pos = (120, 500)
        self.kpi_time = 0.0
        self.kpi_energy = 0.0

        self._build_ui()
        self._draw_scene()
        self._update_state_text()

        self.bind('<space>', lambda e: self._toggle_sim())
        self._update_mission_text()

    def _build_ui(self):
        # Left panel
        self.left = CTk.CTkFrame(self, width=260, height=700)
        self.left.pack(side="left", fill="y", padx=10, pady=10)
        CTk.CTkLabel(self.left, text="팔 파라미터", font=("Arial",12,"bold")).pack(anchor="w", padx=10, pady=(8,0))
        # Difficulty switch
        self.diff_button = CTk.CTkButton(self.left, text=DIFF_KR[self.diff_index], command=self._toggle_diff)
        self.diff_button.pack(anchor="w", padx=10, pady=(6,6))
        CTk.CTkLabel(self.left, text="도움: Space로 시뮬레이션 시작/정지").pack(anchor="w", padx=10, pady=(6,6))
        # Sliders for L1,L2,L3 and phi
        self.sl_l1 = CTk.CTkSlider(self.left, from_=60, to=200, width=230, command=lambda v: self._update_lengths('l1', float(v)))
        self.sl_l1.set(self.robot.l1)
        self.sl_l1.pack(anchor="w", padx=10, pady=(6,6))
        self.sl_l2 = CTk.CTkSlider(self.left, from_=60, to=200, width=230, command=lambda v: self._update_lengths('l2', float(v)))
        self.sl_l2.set(self.robot.l2)
        self.sl_l2.pack(anchor="w", padx=10, pady=(6,6))
        self.sl_l3 = CTk.CTkSlider(self.left, from_=40, to=140, width=230, command=lambda v: self._update_lengths('l3', float(v)))
        self.sl_l3.set(self.robot.l3)
        self.sl_l3.pack(anchor="w", padx=10, pady=(6,6))
        self.sl_phi = CTk.CTkSlider(self.left, from_=-180, to=180, width=230, command=lambda v: self._update_phi_target(float(v)))
        self.sl_phi.set(0)
        self.sl_phi.pack(anchor="w", padx=10, pady=(6,6))
        # Mission text
        self.mission_box = CTk.CTkFrame(self.left, width=230, height=100)
        self.mission_box.pack(padx=10, pady=(8,10))
        self.mission_text = CTk.CTkLabel(self.mission_box, text="의뢰 흐름: 로봇 조합/프로그래밍 -> 시뮬레이션", wraplength=210, justify="left")
        self.mission_text.pack(padx=8, pady=8)
        # Right panel (AI and KPIs)
        self.right = CTk.CTkFrame(self, width=260, height=700)
        self.right.pack(side="right", fill="y", padx=10, pady=10)
        CTk.CTkLabel(self.right, text="AI 어시스턴트", font=("Arial",12,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        self.ai_chat = CTk.CTkFrame(self.right, width=230, height=150)
        self.ai_chat.pack(padx=8, pady=(4,4))
        self.ai_chat_text = CTk.CTkTextbox(self.ai_chat, width=226, height=140)
        self.ai_chat_text.pack()
        self.ai_chat_text.insert("end", "AI: 로봇 의도에 대한 정보를 입력하고 힌트를 받아보세요.\n")
        self.ai_chat_text.config(state=tk.DISABLED)
        self.ai_user_entry = CTk.CTkEntry(self.right, width=210)
        self.ai_user_entry.pack(side="left", padx=(8,0), pady=(4,8))
        self.ai_send_btn = CTk.CTkButton(self.right, text="질문/답변 입력", command=self._handle_ai_input)
        self.ai_send_btn.pack(side="left", padx=6, pady=(4,8))
        self.ai_hint_btn = CTk.CTkButton(self.right, text="AI 힌트(1 크레딧)", command=self._ai_hint)
        self.ai_hint_btn.pack(side="left", padx=6, pady=(4,8))
        self.ai_credits_label = CTk.CTkLabel(self.right, text=f"AI 크레딧: {self.ai.credits}")
        self.ai_credits_label.pack(anchor="w", padx=8, pady=(4,8))
        self.player_credits_label = CTk.CTkLabel(self.right, text=f"크레딧: {self.player_credits}")
        self.player_credits_label.pack(anchor="w", padx=8, pady=(4,8))
        # Canvas area for robot visualization
        self.canvas = CTk.CTkCanvas(self, width=800, height=600, bg="white", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self._start = False
        self._draw_scene()
        self.diff_btn = self.diff_button  # for compatibility
        
    def _update_mission_text(self):
        text = {
            "Easy": "의뢰: 간단한 피킹-분류-이동-배출 흐름. 제약: 에너지/시간 한도.",
            "Medium": "의뢰: 모호한 요구. 목표를 유추하고 제약 조정.",
            "Hard": "의도 비명시. 로봇이 목표를 찾고 임무를 수행합니다."
        }[self.difficulty_internal]
        self.mission_text.config(text=text)

    def _toggle_diff(self):
        self.diff_index = (self.diff_index + 1) % 3
        self.diff_button.config(text=DIFF_KR[self.diff_index])
        self.difficulty_internal = DIFF_INTERNAL[DIFF_KR[self.diff_index]]
        self.hard_mode = (self.difficulty_internal == "Hard")
        self._update_mission_text()

    def _update_lengths(self, which, value):
        if which == 'l1': self.robot.l1 = int(value)
        if which == 'l2': self.robot.l2 = int(value)
        if which == 'l3': self.robot.l3 = int(value)
        self._draw_scene()

    def _update_phi_target(self, deg):
        self.robot.phi_target = math.radians(deg)
        self._draw_scene()

    def _handle_ai_input(self):
        text = self.ai_user_entry.get().strip()
        if not text:
            return
        self.ai_user_entry.delete(0, tk.END)
        self.ai.memory["last_user_input"] = text
        self.ai_chat_text.config(state=tk.NORMAL)
        self.ai_chat_text.insert(tk.END, f"유저: {text}\n")
        self.ai_chat_text.config(state=tk.DISABLED)
        self.ai.respond_to(text)

    def _ai_hint(self):
        hint = self.ai.provide_hint(self.difficulty_internal, self.sim_stage)
        self.ai_chat_text.config(state=tk.NORMAL)
        self.ai_chat_text.insert(tk.END, f"AI Hint: {hint}\n")
        self.ai_chat_text.config(state=tk.DISABLED)
        self.ai_credits_label.config(text=f"AI 크레딧: {self.ai.credits}")

    def _start_sim(self):
        self.sim_running = True
        self.start_time = time.time()
        self._step_sim()

    def _toggle_sim(self):
        if not self.sim_running:
            self._start_sim()
        else:
            self.sim_running = False

    def _step_sim(self):
        if not self.sim_running:
            return
        # simple IK toward target
        base_x, base_y = self.robot.base
        tx, ty = self.sim_target
        rel_x = tx - base_x
        rel_y = -(ty - base_y)
        t1, t2, t3 = self.robot.ik_solve((rel_x, rel_y))
        if t1 is not None:
            alpha = 0.15
            nt1 = self._approach(self.robot.theta1, t1, alpha)
            nt2 = self._approach(self.robot.theta2, t2, alpha)
            nt3 = self._approach(self.robot.theta3, t3, alpha)
            self.robot.set_angles(nt1, nt2, nt3)
            endp = self.robot.forward()[-1]
            dist = math.hypot(endp[0]-tx, endp[1]-ty)
            if dist < 12 and not self.robot.picked:
                self.robot.picked = True
                self.kpi_status.config(text="상태: 피킹 성공")
        else:
            self.robot.theta1 += math.radians(2)
        self._draw_scene()
        if self.robot.picked:
            dx, dy = self.drop_pos
            dx_rel = dx - base_x
            dy_rel = -(dy - base_y)
            t1, t2, t3 = self.robot.ik_solve((dx_rel, dy_rel))
            if t1 is not None:
                nt1 = self._approach(self.robot.theta1, t1, 0.12)
                nt2 = self._approach(self.robot.theta2, t2, 0.12)
                nt3 = self._approach(self.robot.theta3, t3, 0.12)
                self.robot.set_angles(nt1, nt2, nt3)
                endp = self.robot.forward()[-1]
                dist2 = math.hypot(endp[0]-dx, endp[1]-dy)
                if dist2 < 12:
                    self.kpi_status.config(text="상태: 배출 완료")
                    self.sim_running = False
        # update KPI/time
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        self.kpi_time_label.config(text=f"시간: {elapsed:.1f} s")
        self.kpi_energy_label.config(text=f"에너지: {self.robot.energy:.1f} J")
        self.after(40, self._step_sim)

    def _draw_scene(self):
        self.canvas.delete("scene")
        self.canvas.create_rectangle(0, 0, 800, 600, fill="white", tags="scene")
        tx, ty = self.sim_target
        self.canvas.create_rectangle(tx-12, ty-12, tx+12, ty+12, fill="orange", tags="scene")
        self.canvas.create_text(tx, ty-18, text="Target", fill="orange", tags="scene")
        dx, dy = self.drop_pos
        self.canvas.create_rectangle(dx-12, dy-12, dx+12, dy+12, fill="green", tags="scene")
        self.canvas.create_text(dx, dy-18, text="Drop", fill="green", tags="scene")
        (b0,b1,b2,be) = self.robot.forward()
        self.canvas.create_oval(b0[0]-6,b0[1]-6,b0[0]+6,b0[1]+6, fill="gray", tags="scene")
        self.canvas.create_line(b0[0], b0[1], b1[0], b1[1], width=6, fill="blue", tags="scene")
        self.canvas.create_line(b1[0], b1[1], b2[0], b2[1], width=6, fill="blue", tags="scene")
        self.canvas.create_line(b2[0], b2[1], be[0], be[1], width=6, fill="blue", tags="scene")
        self.canvas.create_oval(be[0]-8, be[1]-8, be[0]+8, be[1]+8, fill="red", tags="scene")
        self.canvas.update()

    def _start_from_mission(self):
        self.sim_target = self.sim_target or (860, 260)
        self._start_sim()

    def _update_state_text(self):
        pass  # for MVP we can skip complex text

    def _update_mission_text(self):
        if self.difficulty_internal == "Easy":
            text = "의뢰: 간단한 피킹/배출 흐름. 제약: 에너지/시간 제한."
        elif self.difficulty_internal == "Medium":
            text = "의뢰: 의도 추론 및 중간 제약."
        else:
            text = "의도 불명 의뢰: 플레이어가 목표를 찾습니다."
        if hasattr(self, 'mission_text'):
            self.mission_text.config(text=text)

    def _draw(self):
        self._draw_scene()

    # Helpers
    def _update_lengths(self, which, v):
        self.robot.l1 = int(v) if which=='l1' else self.robot.l1
        self.robot.l2 = int(v) if which=='l2' else self.robot.l2
        self.robot.l3 = int(v) if which=='l3' else self.robot.l3
        self._draw_scene()

    def _update_phi_target(self, deg):
        self.robot.phi_target = math.radians(deg)
        self._draw_scene()

    def _start(self):
        pass

# Run
if __name__ == '__main__':
    app = App()
    app.mainloop()
