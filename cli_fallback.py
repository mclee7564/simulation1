#!/usr/bin/env python3
import json
import os

PARTS_CATALOG = [
    {"id": "frame", "name": "Base Frame", "specs": {"mass":1.0, "power":0.0}},
    {"id": "gripper", "name": "Gripper", "specs": {"mass":0.5, "power":5.0}},
    {"id": "arm", "name": "Arm Actuator", "specs": {"mass":0.8, "power":7.0}},
    {"id": "vision", "name": "Vision Sensor", "specs": {"mass":0.2, "power":2.0}},
    {"id": "battery", "name": "Li-ion Battery", "specs": {"mass":0.6, "power":-1.0, "capacity":100}},
]
BLUEPRINT_DEFAULT = {"name": "Untitled Robot", "parts": [], "power_budget": 100, "state": "idle", "log": []}

def print_blueprint(bp):
    print("블루프린트:")
    print(f" 이름: {bp['name']}")
    print(" 부품:")
    if not bp['parts']:
        print("  (없음)")
    for i,p in enumerate(bp['parts']):
        print(f"  {i+1}. {p['name']} (mass={p['specs']['mass']}, power={p['specs']['power']})")
    print(f" 에너지 예산: {bp['power_budget']}")
    print(f" 상태: {bp['state']}")


def main():
    bp = BLUEPRINT_DEFAULT.copy()
    while True:
        print("- 명령: add <index>, remove <idx>, show, run, reset, save <path>, load <path>, exit")
        cmd = input(": ").strip()
        if cmd == "exit":
            break
        if cmd.startswith("add "):
            idx = int(cmd.split()[1]) - 1
            if 0 <= idx < len(PARTS_CATALOG):
                bp['parts'].append(PARTS_CATALOG[idx])
                print(f"추가: {PARTS_CATALOG[idx]['name']}")
            else:
                print("잘못된 부품 인덱스")
        elif cmd.startswith("remove "):
            idx = int(cmd.split()[1]) - 1
            if 0 <= idx < len(bp['parts']):
                removed = bp['parts'].pop(idx)
                print(f"제거: {removed['name']}")
            else:
                print("잘못된 인덱스")
        elif cmd == "show":
            print_blueprint(bp)
        elif cmd == "run":
            # 간단한 시뮬레이션: 의뢰 5개를 차례로 처리
            bp['state'] = "running"
            energy = 0.0
            steps = 5
            print("시뮬레이션 시작...")
            for s in range(steps):
                energy += 2.0 + max(0, len(bp['parts']) - 1) * 0.5
                print(f" Step {s+1}: energy={energy:.1f}")
            bp['state'] = "idle"
            print("시뮬레이션 끝")
        elif cmd == "reset":
            bp = BLUEPRINT_DEFAULT.copy()
            print("블루프린트 초기화")
        elif cmd.startswith("save "):
            path = cmd.split(maxsplit=1)[1]
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(bp, f, indent=2, ensure_ascii=False)
            print("저장:", path)
        elif cmd.startswith("load "):
            path = cmd.split(maxsplit=1)[1]
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    bp = json.load(f)
                print("로드:", path)
            else:
                print("파일을 찾을 수 없음:", path)
        elif cmd == "debug":
            print_blueprint(bp)
        else:
            print("알 수 없는 명령입니다.")

if __name__ == "__main__":
    main()
