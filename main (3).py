# -*- coding: utf-8 -*-
"""
물로켓 발사 시뮬레이션 - 베타 버전 (Streamlit)
- 탭 1: 발사 시뮬레이션 (5개 변수 슬라이더, 프레임별 시각화 및 프레임 탐색)
- 탭 2: 결과 요약 카드 (Hmax, Tmax, vmax)
- 로그인/저장 기능 제외, 웹 배포용으로 간단한 탭/카드형 UI 구성
- 베타 버전이므로 물리 모델은 단순화되어 있음
"""

import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 간단한 물로켓 시뮬레이션 (1축 상승 모델) – 파라미터는 한국어 변수명 사용

def simulate(초기압력_bar, 물질량_kg, 건조질량_kg, 중심위치_비율, 노즐구경_mm, dt=0.02, t_end=20.0):
    # 단순 물리 상수 및 파라미터
    A_nozzle = math.pi * ((노즐구경_mm / 1000.0) / 2.0) ** 2
    A_drag = math.pi * ((0.06) / 2.0) ** 2  # 본체 지름 6cm 가정
    g = 9.81
    rho = 1.225
    Cd = 0.75
    m_dot = 0.02  # 질량 유출률 (가정)

    t = 0.0
    y = 0.0
    vy = 0.0
    x = 0.0
    vx = 0.0

    history = []
    # 중심 위치에 따른 간단한 thrust 계수 보정
    thr_eff = max(0.0, 1.0 + (float(중심위치_비율) - 0.5) * 0.8)

    while t < t_end:
        mw_remain = max(0.0, 물질량_kg - m_dot * t)
        if mw_remain > 0 and 물질량_kg > 0:
            P_inside = (초기압력_bar * 1e5) * (mw_remain / max(1e-6, 물질량_kg))
            F_thrust = P_inside * A_nozzle * thr_eff
        else:
            F_thrust = 0.0

        m = 건조질량_kg + mw_remain
        v = abs(vy)
        D = 0.5 * rho * v * v * Cd * A_drag
        a = (F_thrust - D - m * g) / max(1e-6, m)

        vy += a * dt
        y += vy * dt
        x += vx * dt

        t += dt
        history.append({"t": t, "x": x, "y": y, "vx": vx, "vy": vy})

        if y < 0:
            break

    return history


def draw_rocket(ax, y, label=None):
    rocket_height = 0.25
    rocket_width = 0.08
    # 지면 위의 로켓 위치를 표시
    ax.add_patch(Rectangle((-rocket_width/2, max(0.0, y)), rocket_width, rocket_height, color='red'))
    ax.plot([0], [0], 'k|', markersize=6)  # 지면 마커
    if label:
        ax.text(0, max(y+rocket_height+0.2, 0.2), label, ha='center')


def main():
    st.set_page_config(layout="wide", page_title="물로켓 발사 시뮬레이션 베타")
    st.title("물로켓 발사 시뮬레이션 베타 (Streamlit)")

    tab1, tab2 = st.tabs(["발사 시뮬레이션", "결과 요약"])

    # 기본값
    DEFAULTS = {
        "초기압력_bar": 2.0,
        "물질량_kg": 0.25,
        "건조질량_kg": 0.25,
        "중심위치_비율": 0.50,
        "노즐구경_mm": 12,
    }

    with tab1:
        st.subheader("파라미터 설정")
        초기압력_bar = st.slider("초기 압력", 0.5, 5.0, DEFAULTS["초기압력_bar"], 0.1)
        물질량_kg = st.slider("물 질량", 0.05, 0.5, DEFAULTS["물질량_kg"], 0.01)
        건조질량_kg = st.slider("건조 질량", 0.05, 0.5, DEFAULTS["건조질량_kg"], 0.01)
        중심위치_비율 = st.slider("중심 위치 비율", 0.0, 1.0, DEFAULTS["중심위치_비율"], 0.01)
        노즐구경_mm = st.slider("노즐 구경 (mm)", 8, 20, DEFAULTS["노즐구경_mm"], 1)

        run_button = st.button("발사 실행")
        reset_button = st.button("초기화")

        if reset_button:
            st.session_state["history"] = []
            st.session_state["frame_idx"] = 0
            st.success("변수가 초기화되었습니다.")

        if run_button:
            hist = simulate(초기압력_bar, 물질량_kg, 건조질량_kg, 중심위치_비율, 노즐구경_mm)
            st.session_state["history"] = hist
            st.session_state["frame_idx"] = 0

        history = st.session_state.get("history", [])
        idx = st.session_state.get("frame_idx", 0)
        if history:
            # 프레임 컨트롤
            step = max(1, int(round(st.slider("배속", 0.5, 4.0, 1.0, 0.5))))
            if st.button("다음 프레임"):
                st.session_state["frame_idx"] = min(len(history)-1, idx + step)
            if st.button("이전 프레임"):
                st.session_state["frame_idx"] = max(0, idx - step)

            idx = st.slider("프레임 선택", 0, len(history)-1, idx, 1)

            # 현재 프레임 그리기
            t_val = history[int(idx)]["t"]
            y_val = history[int(idx)]["y"]
            vy_val = history[int(idx)]["vy"]

            fig, ax = plt.subplots(figsize=(6, 3))
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(0, max(2.0, y_val + 1.0))
            ax.axhline(0, color="k", linewidth=1)
            draw_rocket(ax, y_val, label=f"time={t_val:.2f}s, y={y_val:.2f}m, vy={vy_val:.2f}m/s")
            ax.set_title("발사 프레임")
            st.pyplot(fig)

            # 전체 궤적 — 고도-시간 그래프
            times = [p["t"] for p in history]
            heights = [p["y"] for p in history]
            fig2, ax2 = plt.subplots(figsize=(6, 2))
            ax2.plot(times, heights, color="C0")
            ax2.set_xlabel("시간 (s)")
            ax2.set_ylabel("고도 (m)")
            ax2.set_title("고도 시간 변화")
            st.pyplot(fig2)

            # 결과 카드는 tab2에서 요약 표시
        else:
            st.info("발사를 실행하고 시뮬레이션 결과를 확인하세요.")

    with tab2:
        history = st.session_state.get("history", [])
        if history:
            heights = [p["y"] for p in history]
            times = [p["t"] for p in history]
            Hmax = max(heights)
            Tmax = times[heights.index(Hmax)]
            Vmax = max([abs(p["vy"]) for p in history])
            col1, col2, col3 = st.columns(3)
            col1.metric("최대 고도 (Hmax)", f"{Hmax:.2f} m")
            col2.metric("도달 시간 (Tmax)", f"{Tmax:.2f} s")
            col3.metric("최대 속도 (|v|)", f"{Vmax:.2f} m/s")
        else:
            st.info("발사를 실행하여 요약 정보를 확인하세요.")

if __name__ == "__main__":
    main()
