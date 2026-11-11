#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI MVP version of the custom robot builder game.
- 3DOF planar arm model (base at (0,0))
- Easy/Medium/Hard difficulty mapping via '상/중/하' UI in GUI, here via user input
- No GUI dependencies; runs in a terminal
- Includes a tiny AI assistant with credit-based hints
"""
import math
import time
import random

# ---------- 로봇 모델 (3DOF 팔 + 베이스) ----------
class Robot3DOF:
    def __init__(self):
        self.base = (0.0, 0.0)  # 원점 기준
        self.l1 = 120.0
        self.l2 = 90.0
        self.l3 = 60.0
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
        y = py  # 도메인에 맞추려 절대값 방향 유지해도 무방
        L1, L2, L3 = self.l1, self.l2, self.l3
        d = math.hypot(x, y)
        if d > (L1 + L2 + L3) or d < abs(L1 - L2 - L3):
            return None, None, None
        # Elbow-down 2DOF 해법
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
        self.base = (0.0, 0.0)
        self.theta1 = math.radians(60)
        self.theta2 = math.radians(-25)
        self.theta3 = 0.0
        self.phi_target = 0.0
        self.energy = 0.0
        self.picked = False

# ---------- 간단한 AI 어시스턴트 ----------
class SimpleAIAssistant:
    def __init__(self, initial_credits=2):
        self.credits = initial_credits
        self.memory = {}

    def can_afford(self, cost=1):
        return self.credits >= cost

    def spend(self, cost=1):
        if self.can_afford(cost):
            self.credits -= cost
            return True
        return False

    def earn(self, amount=2):
        self.credits += amount

    def respond_to(self, text):
        t = (text or "").strip().lower()
        if not t:
            return "입력 내용을 확인할 수 없어요."
        if "의도" in t or "무엇" in t:
            idea = self.memory.get("intent", "로봇의 기본 의도는 사용자가 필요로 하는 기능을 도출하는 것")
            return f"현재 의도 추정: {idea}. 필요하면 구체적 의도 정보를 입력해 주세요."
        elif "힌트" in t or "도움" in t:
            return "힌트: Easy는 구체적 제약, Medium은 중간 제약, Hard는 의도 추론이 핵심입니다."
        else:
            self.memory["intent"] = text
            return "AI: 간단한 의도나 로봇 기능을 입력해 주세요. 예: '나는 돌아다닐 수 있는 로봇'"

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

# ---------- CLI 엔트리 ----------

def print_banner():
    print("=== 로봇 제작 CLI MVP ===")
    print("난이도: 상(Hard) / 중(Medium) / 하(Easy)" )

DIFF_MAP = {"1":"Hard","2":"Medium","3":"Easy"}


def select_difficulty():
    while True:
        ch = input("난이도를 선택하세요. 1: 상, 2: 중, 3: 하 > ").strip()
        if ch in DIFF_MAP:
            return DIFF_MAP[ch]
        print("잘못된 입력입니다. 1/2/3 중 하나를 입력해 주세요.")


def simple_distance(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])


def approach_angle(current, target, rate=0.15):
    diff = target - current
    # -pi..pi 보정
    while diff > math.pi:
        diff -= 2*math.pi
    while diff < -math.pi:
        diff += 2*math.pi
    step = max(-rate, min(rate, diff))
    return current + step


def ik_to_angles(robot, target):
    t1, t2, t3 = robot.ik_solve(target)
    return t1, t2, t3


def run_mission(difficulty):
    robot = Robot3DOF()
    ai = SimpleAIAssistant()
    start = time.time()
    target = (150.0, -40.0)
    drop = (40.0, -120.0)

    print(f"난이도 {difficulty}로 시작합니다. 기본 로봇 파라미터: L1={robot.l1}, L2={robot.l2}, L3={robot.l3}")
    print(f"목표 위치: {target}, 드랍 위치: {drop}")

    t1, t2, t3 = ik_to_angles(robot, target)
    if t1 is None:
        print("목표 도달이 불가능합니다. 다른 좌표를 시도하세요.")
        return None

    # 간단한 제어 루프: 목표 위치로 천천히 이동
    robot.theta1, robot.theta2, robot.theta3 = t1, t2, t3
    end = robot.forward()[-1]
    dist = simple_distance(end, target)
    steps = 0
    while dist > 5 and steps < 200:
        nt1 = approach_angle(robot.theta1, t1, 0.15)
        nt2 = approach_angle(robot.theta2, t2, 0.15)
        nt3 = approach_angle(robot.theta3, t3, 0.15)
        robot.set_angles(nt1, nt2, nt3)
        end = robot.forward()[-1]
        dist = simple_distance(end, target)
        steps += 1
        print(f"[진행] 엔드 이펙터: ({end[0]:.1f}, {end[1]:.1f}) 거리={dist:.2f}")
        time.sleep(0.05)

    if dist <= 5:
        print("피킹 성공: 목표에 도달했습니다.")
        robot.picked = True
    else:
        print("피킹 실패: 시간 초과")
        return {
            'success': False,
            'time': time.time()-start,
            'energy': robot.energy,
            'ai_credits_before': ai.credits,
            'credits_awarded': 0,
        }

    # 드랍 위치로 이동
    t1b, t2b, t3b = ik_to_angles(robot, drop)
    if t1b is None:
        print("드랍 위치로의 경로를 찾을 수 없음.")
        return {
            'success': False,
            'time': time.time()-start,
            'energy': robot.energy,
            'ai_credits_before': ai.credits,
            'credits_awarded': 0,
        }
    robot.set_angles(t1b, t2b, t3b)
    end = robot.forward()[-1]
    dist2 = simple_distance(end, drop)
    steps = 0
    while dist2 > 5 and steps < 200:
        nt1 = approach_angle(robot.theta1, t1b, 0.12)
        nt2 = approach_angle(robot.theta2, t2b, 0.12)
        nt3 = approach_angle(robot.theta3, t3b, 0.12)
        robot.set_angles(nt1, nt2, nt3)
        end = robot.forward()[-1]
        dist2 = simple_distance(end, drop)
        steps += 1
        print(f"[드랍 진행] 엔드: ({end[0]:.1f}, {end[1]:.1f}) dist={dist2:.2f}")
        time.sleep(0.05)

    if dist2 <= 5:
        print("배출 완료: 의뢰 성공!")
        robot.energy += 1.0
        ai.earn(2)
        return {
            'success': True,
            'time': time.time()-start,
            'energy': robot.energy,
            'ai_credits_final': ai.credits,
        }
    else:
        print("배출 실패: 시간 초과")
        return {
            'success': False,
            'time': time.time()-start,
            'energy': robot.energy,
            'ai_credits_before': ai.credits,
            'credits_awarded': 0,
        }


def main():
    print_banner()
    while True:
        diff = select_difficulty()
        print(f"선택된 난이도: {diff}")
        result = run_mission(diff)
        print("--- 결과 ---")
        print(result)
        again = input("다시 하시겠습니까? (y/n) > ").strip().lower()
        if again != 'y' and again != 'yes':
            print("종료합니다.")
            break

if __name__ == '__main__':
    main()
