#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CFRP Router CAM - lightweight 2D CAM for Windows (single Python file)

Run (either command, depending on your Python installation):
    py cfrp_router_cam.py
    python cfrp_router_cam.py

Requirements:
    Python 3.9+ (Tkinter is included in the normal Windows installer)
    DXF import:  py -m pip install ezdxf
    STEP import: py -m pip install cadquery-ocp-novtk

Supported DXF entities: LINE, LWPOLYLINE, POLYLINE, ARC, CIRCLE.
Curves are tessellated into line segments. Units are millimetres.
Output post: Mach3 metric G-code (G21/G90/G54, M3/M5).

STEP solids are reduced to the boundary loops of one selected planar machining
face, then processed by the same proven 2.5D routing engine as DXF contours.
Always
inspect the preview, simulate/dry-run above the stock, verify zero/origin and
clamps, and use suitable dust extraction and PPE for conductive CFRP dust.
"""

from __future__ import annotations

import bisect
import hashlib
import math
import os
import queue
import re
import copy
import ctypes
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import multiprocessing as mp
import tkinter as tk
import tkinter.font as tkfont
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Point3 = Tuple[float, float, float]
EPS = 1e-7
STEP_FACE_NORMAL_DOT = 0.999
APP_VERSION = "1.10"
SETTINGS_FILENAME = "settings.json"
SETTINGS_APPDATA_DIR = "CFRP_Router_CAM"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/wofidkr57-jpg/CFRP-Router-CAM/main/latest.json"
UPDATE_DOWNLOAD_PREFIX = "https://github.com/wofidkr57-jpg/CFRP-Router-CAM/releases/download/"
UPDATE_TEMP_FILENAME = "_CFRP_Router_CAM_update.exe"
LEGACY_DEFAULT_START_CODE = "G21\nG90\nG17\nG94\nG0 Z{SAFE_Z}\nM3 S{RPM}\nG4 P1"
LEGACY_DEFAULT_END_CODE = "M5\nG0 Z{SAFE_Z}\nG0 X0 Y0\nM2"
V101_DEFAULT_START_CODE = "%\nO0001\nG21\nG90\nG17\nG94\nG0 Z{SAFE_Z}\nS{RPM} M3"
V102_DEFAULT_START_CODE = "%\nO0001\nG21\nG90\nG17\nG94\nG54\nG0 Z{SAFE_Z}\nS{RPM} M3\nG4 P1"
V103_DEFAULT_START_CODE = "%\nO0001\nG21\nG90\nG17\nG94\nG54\nG92.1\nG0 Z{SAFE_Z}\nS{RPM} M3\nG4 P1"
DEFAULT_START_CODE = "%\nO0001\nG21\nG90\nG17\nG94\nG54\nG0 Z{SAFE_Z}\nS{RPM} M3\nG4 P1"
DEFAULT_END_CODE = "G0 Z{SAFE_Z}\nM5\nM30\n%"
OBJECT_COLORS = ("#ffd84d", "#67d9ff", "#ff8fb8", "#9ee56f", "#c9a0ff", "#ffad5c", "#72e0c1", "#f4ef7a")
OBJECT_TREE_COLORS = OBJECT_COLORS


# UI language is deliberately separate from CAM values and NC output.  Existing
# settings may contain Korean enum values, so the machining engine continues to
# accept both languages while only the presentation layer is translated.
CURRENT_LANGUAGE = "ko"
SUPPORTED_LANGUAGES = ("ko", "en")

_UI_EN_EXACT = {
    "한국어": "Korean",
    "연산 중": "Working",
    "준비 중...": "Ready...",
    "DXF 열기": "Open DXF",
    "STEP 열기": "Open STEP",
    "여러 파일 추가": "Add Files",
    "예제 사각형": "Example Rectangle",
    "G-code 생성": "Generate G-code",
    "G-code 저장": "Save G-code",
    "3D 시뮬레이션": "3D Simulation",
    "되돌리기 (Ctrl+Z)": "Undo (Ctrl+Z)",
    "다시 실행 (Ctrl+Y)": "Redo (Ctrl+Y)",
    "화면 맞춤": "Fit View",
    "경로 안전검사": "Toolpath Safety Check",
    "거리 측정: OFF": "Measure Distance: OFF",
    "거리 측정: ON": "Measure Distance: ON",
    "측정 지우기": "Clear Measurement",
    "그리드": "Grid",
    "공구 지름 (mm)": "Tool Diameter (mm)",
    "판 두께 (mm)": "Stock Thickness (mm)",
    "관통 여유 (mm)": "Through Allowance (mm)",
    "안전 Z (mm)": "Safe Z (mm)",
    "패스 수": "Pass Count",
    "탭 개수/외곽": "Tabs per Outer Contour",
    "마이크로탭 길이 (mm)": "Microtab Length (mm)",
    "탭 잔여두께 (mm)": "Tab Remaining Thickness (mm)",
    "탭 ramp (mm)": "Tab Ramp (mm)",
    "Z축 원점": "Z Origin",
    "XY 작업 원점": "XY Work Origin",
    "좌하단": "Lower-left",
    "좌상단": "Upper-left",
    "우상단": "Upper-right",
    "우하단": "Lower-right",
    "중앙": "Center",
    "DXF 원점": "DXF origin",
    "선택점": "Selected point",
    "DXF XY 원점 선택: OFF": "Select DXF XY Origin: OFF",
    "DXF XY 원점 선택: ON": "Select DXF XY Origin: ON",
    "급속이송 최소화 (홀 묶음)": "Minimize Rapids (group holes)",
    "절삭유/에어 사용 (M8 ON → M9 OFF)": "Coolant/Air (M8 ON → M9 OFF)",
    "홈 사용: 종료 후 G53 주차": "Homed Machine: G53 Park at End",
    "황삭 측면여유 → 벽면 정삭": "Rough Wall Allowance → Wall Finish",
    "외곽 관통부 어니언스킨": "Onion Skin on Through Outer Contours",
    "정삭 적용 범위": "Finishing Scope",
    "전체": "All",
    "외곽만": "Outer only",
    "내부홀만": "Inner only",
    "어니언스킨 잔여 (mm)": "Onion Skin Remaining (mm)",
    "황삭 측면 여유 (mm)": "Rough Wall Allowance (mm)",
    "정삭 Feed (%)": "Finish Feed (%)",
    "탭 형상": "Tab Shape",
    "탭 설정 / 배치": "Tab Settings / Placement",
    "기존 누적거리 (m)": "Previous Accumulated Distance (m)",
    "기존 누적시간 (분)": "Previous Accumulated Time (min)",
    "라인 복구 허용오차 (mm)": "Line Repair Tolerance (mm)",
    "끊긴 라인 복구": "Repair Broken Lines",
    "두 라인 선택 연결: OFF": "Join Two Lines: OFF",
    "두 라인 선택 연결: ON": "Join Two Lines: ON",
    "자동 어레이 / 판재 배치": "Automatic Array / Sheet Layout",
    "판재 X (mm)": "Sheet X (mm)",
    "판재 Y (mm)": "Sheet Y (mm)",
    "가공물 간격 (mm)": "Part Spacing (mm)",
    "가장자리 여유 (mm)": "Edge Margin (mm)",
    "단일 객체 수량 (0=최대)": "Single-object Quantity (0=maximum)",
    "90° 회전 배치 허용": "Allow 90° Rotation",
    "자동 회전 최적화 (5° 단위)": "Optimize Rotation (5° steps)",
    "판재에 자동 어레이": "Auto-array on Sheet",
    "수동 어레이 시작 (드래그 / R 회전)": "Start Manual Array (drag / R rotates)",
    "수동 어레이 편집 (드래그 / R 회전)": "Edit Manual Array (drag / R rotates)",
    "어레이 해제": "Clear Array",
    "탭 배치 (최외곽만)": "Tab Placement (outermost only)",
    "자동 탭 다시 배치": "Rebuild Automatic Tabs",
    "수동 탭 추가: OFF": "Add Manual Tab: OFF",
    "수동 탭 추가: ON": "Add Manual Tab: ON",
    "수동 탭 모두 지우기": "Clear All Manual Tabs",
    "선택 윤곽 설정": "Selected Contour Settings",
    "선택 없음": "No selection",
    "깊이 mm (빈칸=관통)": "Depth mm (blank=through)",
    "가공 순번 (빈칸=자동)": "Cut Order (blank=automatic)",
    "내부/외부": "Inner/Outer",
    "자동": "Auto",
    "내부": "Inner",
    "외부": "Outer",
    "이 윤곽에 탭 허용": "Allow Tabs on This Contour",
    "이 윤곽 가공에 포함": "Include This Contour in Machining",
    "이 윤곽 안전검사 제외": "Exclude This Contour from Safety Check",
    "목록 다중선택 검사 제외/복원": "Exclude/Restore Selected Safety Checks",
    "선택 설정 적용": "Apply Selection Settings",
    "절삭 시작점 선택: OFF": "Select Cut Start: OFF",
    "절삭 시작점 선택: ON": "Select Cut Start: ON",
    "공구 보정경로/순서 표시": "Show Compensated Toolpath/Order",
    "꼬인 작은 루프 자동 잘라내기": "Automatically Trim Small Tangled Loops",
    "파일별 객체 / 배치 수량": "Objects / Quantity by File",
    "객체": "Object",
    "수량": "Qty",
    "윤곽": "Contour",
    "선택 수량": "Selected Qty",
    "적용": "Apply",
    "객체 삭제": "Delete Object",
    "가공 순서 / 윤곽 목록": "Cut Order / Contour List",
    "선택 윤곽만 보기": "Show Selected Contours",
    "전체 보기": "Show All",
    "선택→PART1 / 나머지→PART2 G-code 생성": "Selected→PART1 / Remaining→PART2",
    "순서": "Order",
    "지정": "Manual",
    "깊이": "Depth",
    "검사": "Check",
    "제외": "Excluded",
    "G-code 미리보기": "G-code Preview",
    "Z 설정 도움말": "Z Setup Help",
    "설정": "Settings",
    "START G-code (비워두면 안전 기본값 사용)": "START G-code (blank uses safe defaults)",
    "화면 글자 크기": "UI Font Size",
    "글자 크기 (8~20)": "Font Size (8-20)",
    "글자 크기 적용": "Apply Font Size",
    "프로그램 업데이트": "Program Update",
    "지금 업데이트 확인": "Check for Updates Now",
    "언어 설정": "Language",
    "언어 적용": "Apply Language",
    "재시작 후 적용됩니다.": "The change is applied after restart.",
    "① 가공면 선택 (Ctrl 다중)": "① Select Machining Faces (Ctrl multi-select)",
    "선택면 → +Z / Z0": "Selected Faces → +Z / Z0",
    "② 원점 꼭짓점": "② Origin Vertex",
    "선택점 → XYZ0": "Selected Point → XYZ0",
    "③ XY 끌기": "③ Drag XY",
    "취소": "Cancel",
    "CAM으로 가져오기": "Import into CAM",
    "초기화": "Reset",
    "Z 회전 °": "Z Rotation °",
    "회전 적용": "Apply Rotation",
    "원점 프리셋": "Origin Preset",
    "반대면": "Opposite Side",
    "등각": "Isometric",
    "▶ 재생": "▶ Play",
    "⏸ 일시정지": "⏸ Pause",
    "■ 처음": "■ Start",
    "속도": "Speed",
    "급속이동 표시": "Show Rapids",
    "표시 방식": "Display Mode",
    "공구경로": "Toolpath",
    "깊이맵": "Depth map",
    "가공 깊이": "Machining Depth",
    "표면 0.00": "Surface 0.00",
    "관통": "Through",
}

_UI_EN_PHRASES = {
    "DXF 또는 STEP을 열어 주세요 (단위: mm)": "Open a DXF or STEP file (units: mm)",
    "저장된 설정을 불러왔습니다. DXF 또는 STEP을 열어 주세요.": "Saved settings loaded. Open a DXF or STEP file.",
    "가공할 평면을 클릭한 뒤 ‘선택면 → +Z / Z0’을 누르세요.": "Click a machining plane, then press 'Selected Faces → +Z / Z0'.",
    "먼저 DXF 또는 STEP 형상을 가져오세요.": "Import DXF or STEP geometry first.",
    "먼저 DXF를 열어 주세요.": "Open a DXF file first.",
    "가공에 포함된 윤곽이 없습니다.": "No contours are included in machining.",
    "가공면을 하나 이상 선택하세요.": "Select at least one machining face.",
    "선택된 가공면이 없습니다.": "No machining face is selected.",
    "선택면 번호가 올바르지 않습니다.": "The selected face index is invalid.",
    "어레이할 형상이 없습니다.": "There is no geometry to array.",
    "객체에 배치할 형상이 없습니다.": "The object has no geometry to place.",
    "배치할 객체가 없습니다.": "There are no objects to place.",
    "설정한 판재와 여유 안에 가공물이 들어가지 않습니다.": "The part does not fit inside the configured sheet and margins.",
    "공구 보정경로에서 이상을 찾지 못했습니다.": "No problems were found in the compensated toolpath.",
    "표시할 G0/G1 이동을 찾지 못했습니다.": "No G0/G1 moves were found to display.",
    "가공면을 먼저 선택하세요.": "Select a machining face first.",
    "원점 꼭짓점을 먼저 선택하세요.": "Select an origin vertex first.",
    "각도를 숫자로 입력하세요.": "Enter the angle as a number.",
    "좌표계를 초기화했습니다.": "The work coordinate system was reset.",
    "업데이트 확인은 배포용 EXE에서 작동합니다.": "Update checking works in the distributed EXE.",
    "이미 업데이트를 확인하거나 다운로드하고 있습니다.": "An update check or download is already running.",
    "현재 허용오차 안에서 연결할 끝점을 찾지 못했습니다.": "No endpoints were found within the current repair tolerance.",
    "열린 선만 연결할 수 있습니다.": "Only open lines can be joined.",
    "폐곡선이 아닌 열린 선을 선택하세요.": "Select an open line, not a closed contour.",
    "폐곡선에서 절삭을 시작할 위치를 클릭하세요.": "Click the desired cut start point on a closed contour.",
    "절삭 시작점은 폐곡선에서 선택하세요.": "A cut start point can only be selected on a closed contour.",
    "거리 측정을 지웠습니다.": "The distance measurement was cleared.",
    "패스 수는 1 이상이어야 합니다.": "Pass count must be at least 1.",
    "공구, 판 두께, RPM, Feed, Plunge, 안전 Z는 0보다 커야 합니다.": "Tool diameter, stock, RPM, feed, plunge and Safe Z must be greater than zero.",
    "관통 여유와 탭 잔여두께 값을 확인하세요.": "Check through allowance and tab remaining thickness.",
    "정삭 Feed는 0 초과 100% 이하로 설정하세요.": "Finish feed must be greater than 0% and no more than 100%.",
    "누적 거리와 누적 시간은 음수가 될 수 없습니다.": "Accumulated distance and time cannot be negative.",
    "라인 복구 허용오차는 음수가 될 수 없습니다.": "Line repair tolerance cannot be negative.",
    "판재 X/Y 크기는 0보다 커야 합니다.": "Sheet X/Y dimensions must be greater than zero.",
    "최신 버전 확인 중...": "Checking for the latest version...",
    "업데이트 다운로드 완료": "Update download complete",
    "업데이트 실패": "Update Failed",
    "업데이트 확인 실패": "Update Check Failed",
    "업데이트 실행 실패": "Update Launch Failed",
    "새 버전 발견": "New Version Found",
    "설정 오류": "Settings Error",
    "생성 오류": "Generation Error",
    "가공 전 점검": "Pre-machining Check",
    "가공 점검": "Machining Check",
    "경로 검사": "Path Check",
    "STEP 오류": "STEP Error",
    "DXF 오류": "DXF Error",
    "STEP 좌표계": "STEP Work Coordinates",
    "STEP 원점": "STEP Origin",
    "STEP 가져오기": "STEP Import",
    "2분할 G-code": "Split G-code",
    "2분할 G-code 저장": "Save Split G-code",
}

_UI_EN_WORDS = {
    "업데이트": "update", "가공": "machining", "공구": "tool", "보정경로": "compensated path",
    "경로": "path", "안전검사": "safety check", "검사": "check", "윤곽": "contour",
    "선택": "selected", "설정": "settings", "오류": "error", "완료": "complete",
    "불러오기": "load", "가져오기": "import", "저장": "save", "생성": "generate",
    "배치": "layout", "어레이": "array", "판재": "sheet", "객체": "object",
    "수량": "quantity", "간격": "spacing", "가장자리": "edge", "여유": "allowance",
    "면": "face", "깊이": "depth", "관통": "through", "내부": "inner", "외곽": "outer",
    "외부": "outer", "탭": "tab", "회전": "rotation", "원점": "origin", "좌표계": "coordinates",
    "자동": "automatic", "수동": "manual", "추가": "add", "제외": "exclude", "복원": "restore",
    "변경": "changed", "실패": "failed", "확인": "check", "진행": "progress", "준비": "prepare",
    "계산": "calculate", "이동": "move", "거리": "distance", "시간": "time", "분": "min",
    "초": "sec", "개": "", "곳": "", "쌍": "pairs", "중": "", "후": "after",
}


def ui_text(value):
    """Translate visible UI text while leaving stored CAM data untouched."""
    if CURRENT_LANGUAGE != "en" or not isinstance(value, str) or not value:
        return value
    if value in _UI_EN_EXACT:
        return _UI_EN_EXACT[value]
    if value in _UI_EN_PHRASES:
        return _UI_EN_PHRASES[value]
    result = value
    for source, target in sorted(_UI_EN_PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(source, target)
    for source, target in sorted(_UI_EN_EXACT.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(source, target)
    for source, target in sorted(_UI_EN_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(source, target)
    # A missed status fragment must never leak Korean into English mode.  Core
    # labels and safety messages have exact translations above; this fallback
    # keeps uncommon progress details readable as English/numeric context.
    result = re.sub(r"[가-힣]+", "", result)
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r" *\n *", "\n", result).strip()
    return result or "Status"


_ENUM_KO = {
    "Lower-left":"좌하단", "Upper-left":"좌상단", "Upper-right":"우상단", "Lower-right":"우하단",
    "Center":"중앙", "DXF origin":"DXF 원점", "Selected point":"선택점",
    "All":"전체", "Outer only":"외곽만", "Inner only":"내부홀만",
}


def localized_enum_value(value):
    if CURRENT_LANGUAGE == "en":
        return ui_text(value)
    return _ENUM_KO.get(str(value), value)


class DisplayStringVar(tk.StringVar):
    def __init__(self, master=None, value=None, name=None):
        super().__init__(master=master, value=ui_text(value), name=name)

    def set(self, value):
        return super().set(ui_text(value))


def _localized_options(options):
    converted = dict(options)
    if "text" in converted:
        converted["text"] = ui_text(converted["text"])
    if "values" in converted and CURRENT_LANGUAGE == "en":
        converted["values"] = tuple(ui_text(value) if isinstance(value, str) else value
                                    for value in converted["values"])
        variable = converted.get("textvariable")
        if variable is not None:
            try:
                current = variable.get()
                if isinstance(current, str):
                    variable.set(ui_text(current))
            except tk.TclError:
                pass
    return converted


class _LocalizedWidgetMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **_localized_options(kwargs))

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            cnf = _localized_options(cnf)
        return super().configure(cnf, **_localized_options(kwargs))

    config = configure


_OriginalTtkButton = ttk.Button
_OriginalTtkLabel = ttk.Label
_OriginalTtkCheckbutton = ttk.Checkbutton
_OriginalTtkRadiobutton = ttk.Radiobutton
_OriginalTtkLabelframe = ttk.LabelFrame
_OriginalTtkCombobox = ttk.Combobox
_OriginalTtkNotebook = ttk.Notebook
_OriginalTtkTreeview = ttk.Treeview
_OriginalTkCanvas = tk.Canvas
_OriginalTk = tk.Tk
_OriginalToplevel = tk.Toplevel


class _LocalizedButton(_LocalizedWidgetMixin, _OriginalTtkButton):
    pass


class _LocalizedLabel(_LocalizedWidgetMixin, _OriginalTtkLabel):
    pass


class _LocalizedCheckbutton(_LocalizedWidgetMixin, _OriginalTtkCheckbutton):
    pass


class _LocalizedRadiobutton(_LocalizedWidgetMixin, _OriginalTtkRadiobutton):
    pass


class _LocalizedLabelframe(_LocalizedWidgetMixin, _OriginalTtkLabelframe):
    pass


class _LocalizedCombobox(_LocalizedWidgetMixin, _OriginalTtkCombobox):
    pass


class _LocalizedNotebook(_OriginalTtkNotebook):
    def add(self, child, **kwargs):
        return super().add(child, **_localized_options(kwargs))


class _LocalizedTreeview(_OriginalTtkTreeview):
    def heading(self, column, option=None, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = ui_text(kwargs["text"])
        return super().heading(column, option, **kwargs)


class _LocalizedCanvas(_OriginalTkCanvas):
    def create_text(self, *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = ui_text(kwargs["text"])
        return super().create_text(*args, **kwargs)


class _LocalizedWindowMixin:
    def title(self, string=None):
        return super().title(ui_text(string) if string is not None else None)


class _LocalizedTk(_LocalizedWindowMixin, _OriginalTk):
    pass


class _LocalizedToplevel(_LocalizedWindowMixin, _OriginalToplevel):
    pass


ttk.Button = _LocalizedButton
ttk.Label = _LocalizedLabel
ttk.Checkbutton = _LocalizedCheckbutton
ttk.Radiobutton = _LocalizedRadiobutton
ttk.LabelFrame = _LocalizedLabelframe
ttk.Combobox = _LocalizedCombobox
ttk.Notebook = _LocalizedNotebook
ttk.Treeview = _LocalizedTreeview
tk.Canvas = _LocalizedCanvas
tk.Tk = _LocalizedTk
tk.Toplevel = _LocalizedToplevel


def _wrap_messagebox(function):
    def localized(title=None, message=None, *args, **kwargs):
        return function(ui_text(title), ui_text(message), *args, **kwargs)
    return localized


for _messagebox_name in ("showinfo", "showwarning", "showerror", "askokcancel", "askyesno", "askretrycancel"):
    if hasattr(messagebox, _messagebox_name):
        setattr(messagebox, _messagebox_name, _wrap_messagebox(getattr(messagebox, _messagebox_name)))


def application_directory() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def startup_settings_candidates() -> List[str]:
    portable = os.path.join(application_directory(), SETTINGS_FILENAME)
    appdata = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                           SETTINGS_APPDATA_DIR, SETTINGS_FILENAME)
    return [portable] if os.path.normcase(os.path.abspath(portable)) == os.path.normcase(os.path.abspath(appdata)) else [portable, appdata]


def saved_interface_language() -> Optional[str]:
    override = str(os.environ.get("CFRP_CAM_LANGUAGE", "")).strip().lower()
    if override in SUPPORTED_LANGUAGES:
        return override
    for path in startup_settings_candidates():
        try:
            with open(path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
            language = str(data.get("language", "")).strip().lower()
            if language in SUPPORTED_LANGUAGES:
                return language
        except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return None


def choose_interface_language(parent) -> str:
    """Show a standalone first-run modal even while the main window is hidden."""
    result = {"language": "ko"}
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title("Language / 언어")
    dialog.resizable(False, False)
    # A transient of a withdrawn root stays hidden on Windows.  Keep this
    # window independent so first-run users can see it and reach it via Alt+Tab.
    frame = ttk.Frame(dialog, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Choose interface language\n사용할 언어를 선택하세요",
              justify="center", font=("Segoe UI", 12, "bold")).pack(pady=(0, 16))

    def select(language):
        result["language"] = language
        dialog.destroy()

    ttk.Button(frame, text="한국어", command=lambda: select("ko"), width=18).pack(fill="x", pady=4)
    ttk.Button(frame, text="English", command=lambda: select("en"), width=18).pack(fill="x", pady=4)
    dialog.protocol("WM_DELETE_WINDOW", lambda: select("ko"))
    dialog.update_idletasks()
    width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
    x = max(0, (dialog.winfo_screenwidth() - width) // 2)
    y = max(0, (dialog.winfo_screenheight() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.lift()
    dialog.focus_force()
    dialog.grab_set()
    parent.wait_window(dialog)
    return result["language"]


@dataclass
class Contour:
    points: List[Point]
    closed: bool = True
    name: str = ""
    depth: int = 0
    role: str = "outer"
    tabs: List[float] = field(default_factory=list)  # distance along original path
    layer: str = "0"
    target_depth: Optional[float] = None  # positive depth below stock top
    forced_role: str = "auto"            # auto / inner / outer
    tabs_enabled: bool = True
    enabled: bool = True
    safety_excluded: bool = False
    start_s: float = 0.0
    bridges: List[Tuple[Point, Point]] = field(default_factory=list)
    cut_order: Optional[int] = None
    object_id: int = 0
    object_name: str = ""
    instance_id: int = 0
    # Distinguish an intentional zero-tab choice from a newly-created contour
    # whose automatic tabs have not been populated yet.
    tabs_cleared: bool = False

    @property
    def area(self) -> float:
        return signed_area(self.points) if self.closed else 0.0

    @property
    def length(self) -> float:
        return path_length(self.points, self.closed)


@dataclass
class PartObject:
    object_id: int
    name: str
    contours: List[Contour]
    quantity: int = 1
    source_path: str = ""
    stock: Optional[float] = None
    display_offset: Point = (0.0, 0.0)
    enabled: bool = True
    quantity_set: bool = False
    # Parts selected from one multi-body STEP keep their original relative XY
    # placement while remaining independently selectable/arrayable.
    layout_group: str = ""


@dataclass
class NestPlacement:
    object_id: int
    instance_id: int
    angle: float
    x: float
    y: float
    width: float
    height: float


@dataclass
class StepFace:
    vertices: List[Point3]
    triangles: List[Tuple[int, int, int]]
    normal: Point3
    center: Point3
    topo_shape: object = None


@dataclass
class StepModel:
    filename: str
    faces: List[StepFace]
    vertices: List[Point3]
    matrix: List[List[float]] = field(default_factory=lambda: mat_identity())
    shape: object = None
    face_components: List[int] = field(default_factory=list)
    component_vertices: Dict[int,List[Point3]] = field(default_factory=dict)


def v3_add(a: Point3, b: Point3) -> Point3:
    return a[0]+b[0], a[1]+b[1], a[2]+b[2]


def v3_sub(a: Point3, b: Point3) -> Point3:
    return a[0]-b[0], a[1]-b[1], a[2]-b[2]


def v3_mul(a: Point3, s: float) -> Point3:
    return a[0]*s, a[1]*s, a[2]*s


def v3_dot(a: Point3, b: Point3) -> float:
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def v3_cross(a: Point3, b: Point3) -> Point3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def v3_len(a: Point3) -> float:
    return math.sqrt(v3_dot(a, a))


def v3_unit(a: Point3) -> Point3:
    n = v3_len(a)
    return (0.0, 0.0, 1.0) if n < EPS else v3_mul(a, 1.0/n)


def mat_identity() -> List[List[float]]:
    return [[1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],
            [0.0,0.0,1.0,0.0],[0.0,0.0,0.0,1.0]]


def mat_mul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> List[List[float]]:
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def mat_apply(m: Sequence[Sequence[float]], p: Point3, vector: bool = False) -> Point3:
    w = 0.0 if vector else 1.0
    q = [sum(m[i][j]*([p[0],p[1],p[2],w][j]) for j in range(4)) for i in range(3)]
    return float(q[0]), float(q[1]), float(q[2])


def mat_translate(x: float, y: float, z: float) -> List[List[float]]:
    m=mat_identity();m[0][3]=x;m[1][3]=y;m[2][3]=z;return m


def mat_rotate_z(degrees: float) -> List[List[float]]:
    a=math.radians(degrees);c,s=math.cos(a),math.sin(a);m=mat_identity()
    m[0][0]=c;m[0][1]=-s;m[1][0]=s;m[1][1]=c;return m


def rotation_from_to(source: Point3, target: Point3) -> List[List[float]]:
    """Return a stable 4x4 rotation that maps source onto target."""
    a,b=v3_unit(source),v3_unit(target);c=max(-1.0,min(1.0,v3_dot(a,b)))
    if c > 1.0-1e-10:return mat_identity()
    if c < -1.0+1e-10:
        trial=(1.0,0.0,0.0) if abs(a[0])<.8 else (0.0,1.0,0.0)
        axis=v3_unit(v3_cross(a,trial));angle=math.pi
    else:
        axis=v3_unit(v3_cross(a,b));angle=math.acos(c)
    x,y,z=axis;co,si=math.cos(angle),math.sin(angle);t=1.0-co
    r=mat_identity()
    r[0][:3]=[t*x*x+co,t*x*y-si*z,t*x*z+si*y]
    r[1][:3]=[t*x*y+si*z,t*y*y+co,t*y*z-si*x]
    r[2][:3]=[t*x*z-si*y,t*y*z+si*x,t*z*z+co]
    return r


def triangle_normal(a: Point3, b: Point3, c: Point3) -> Tuple[Point3, float]:
    cross=v3_cross(v3_sub(b,a),v3_sub(c,a));twice_area=v3_len(cross)
    return v3_unit(cross), twice_area*.5


def step_mesh_components(faces: Sequence[StepFace]) -> Tuple[List[int],Dict[int,List[Point3]]]:
    """Group meshed STEP faces that share an edge into connected components."""
    count=len(faces)
    if not count:return [],{}
    parent=list(range(count))
    def find(index:int)->int:
        while parent[index]!=index:
            parent[index]=parent[parent[index]];index=parent[index]
        return index
    def union(a:int,b:int):
        ra,rb=find(a),find(b)
        if ra!=rb:parent[rb]=ra
    edge_owner:Dict[Tuple[Tuple[int,int,int],Tuple[int,int,int]],int]={}
    scale=100000.0
    for face_index,face in enumerate(faces):
        keys=[(round(p[0]*scale),round(p[1]*scale),round(p[2]*scale)) for p in face.vertices]
        for tri in face.triangles:
            if any(index<0 or index>=len(keys) for index in tri):continue
            for ia,ib in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
                a,b=keys[ia],keys[ib]
                if a==b:continue
                edge=(a,b) if a<b else (b,a)
                owner=edge_owner.setdefault(edge,face_index)
                if owner!=face_index:union(face_index,owner)
    component_by_root:Dict[int,int]={};face_components=[]
    for face_index in range(count):
        root=find(face_index)
        if root not in component_by_root:component_by_root[root]=len(component_by_root)
        face_components.append(component_by_root[root])
    component_vertices:Dict[int,List[Point3]]={};seen:Dict[int,set]={}
    for face_index,face in enumerate(faces):
        component=face_components[face_index];bucket=component_vertices.setdefault(component,[]);known=seen.setdefault(component,set())
        for point in face.vertices:
            key=tuple(round(value,7) for value in point)
            if key not in known:known.add(key);bucket.append(point)
    return face_components,component_vertices


def load_step_model(filename: str, tolerance: float = 0.08,
                    progress:Optional[Callable[[float,str],None]]=None) -> StepModel:
    """Load STEP directly with OCCT and preserve individual CAD faces for picking."""
    def report(value:float,message:str):
        if progress:progress(value,message)
    report(2,"STEP 엔진 준비 중")
    try:
        from OCP.BRep import BRep_Tool
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_Reader
        from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_VERTEX
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopLoc import TopLoc_Location
        from OCP.TopoDS import TopoDS
    except ImportError as exc:
        raise RuntimeError(f"STEP 엔진 로드 실패\n{type(exc).__name__}: {exc}") from exc
    report(7,"STEP 파일 읽는 중");reader=STEPControl_Reader()
    if reader.ReadFile(filename)!=IFSelect_RetDone:raise ValueError("STEP 파일 형식 또는 경로를 읽지 못했습니다.")
    report(16,"STEP 솔리드 변환 중")
    if reader.TransferRoots()<=0:raise ValueError("STEP에서 솔리드를 변환하지 못했습니다.")
    shape=reader.OneShape();report(25,"3D 표시 메시 생성 중")
    mesher=BRepMesh_IncrementalMesh(shape,tolerance,False,0.1,True);mesher.Perform();report(35,"면 목록 구성 중")
    face_shapes=[];explorer=TopExp_Explorer(shape,TopAbs_FACE)
    while explorer.More():
        face_shapes.append(TopoDS.Face_s(explorer.Current()));explorer.Next()
    faces=[]
    for face_index,face in enumerate(face_shapes,1):
        report(35+50*face_index/max(len(face_shapes),1),f"3D 면 처리 {face_index}/{len(face_shapes)}")
        location=TopLoc_Location();mesh=BRep_Tool.Triangulation_s(face,location)
        if mesh is not None:
            trsf=location.Transformation();verts=[];tris=[]
            for i in range(1,mesh.NbNodes()+1):
                p=mesh.Node(i).Transformed(trsf);verts.append((float(p.X()),float(p.Y()),float(p.Z())))
            reverse=face.Orientation()==TopAbs_REVERSED
            for i in range(1,mesh.NbTriangles()+1):
                tri=mesh.Triangle(i);a,b,c=tri.Value(1)-1,tri.Value(2)-1,tri.Value(3)-1
                tris.append((a,c,b) if reverse else (a,b,c))
            normal_sum=(0.0,0.0,0.0);center_sum=(0.0,0.0,0.0);area_sum=0.0
            for ia,ib,ic in tris:
                a,b,c=verts[ia],verts[ib],verts[ic];n,area=triangle_normal(a,b,c)
                normal_sum=v3_add(normal_sum,v3_mul(n,area));center_sum=v3_add(center_sum,v3_mul(v3_mul(v3_add(v3_add(a,b),c),1/3),area));area_sum+=area
            if area_sum>EPS:faces.append(StepFace(verts,tris,v3_unit(normal_sum),v3_mul(center_sum,1/area_sum),face))
    report(88,"꼭짓점 정리 중");model_vertices=[];seen=set();explorer=TopExp_Explorer(shape,TopAbs_VERTEX)
    while explorer.More():
        vertex=TopoDS.Vertex_s(explorer.Current());p=BRep_Tool.Pnt_s(vertex);q=(float(p.X()),float(p.Y()),float(p.Z()))
        key=tuple(round(x,7) for x in q)
        if key not in seen:seen.add(key);model_vertices.append(q)
        explorer.Next()
    if not faces:raise ValueError("STEP에서 표시 가능한 면을 찾지 못했습니다.")
    face_components,component_vertices=step_mesh_components(faces)
    report(100,"STEP 불러오기 완료")
    return StepModel(filename,faces,model_vertices,shape=shape,
                     face_components=face_components,component_vertices=component_vertices)


def face_boundary_loops(face: StepFace, matrix: Sequence[Sequence[float]]) -> List[List[Point3]]:
    """Recover outer and hole loops from the selected face's triangulation."""
    scale=100000.0
    keys=[(round(p[0]*scale),round(p[1]*scale),round(p[2]*scale)) for p in face.vertices]
    canonical:Dict[Tuple[int,int,int],int]={};remap=[];points=[]
    for key,p in zip(keys,face.vertices):
        if key not in canonical:canonical[key]=len(points);points.append(p)
        remap.append(canonical[key])
    counts:Dict[Tuple[int,int],int]={}
    for tri in face.triangles:
        ids=[remap[tri[0]],remap[tri[1]],remap[tri[2]]]
        for a,b in ((ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])):
            edge=(a,b) if a<b else (b,a);counts[edge]=counts.get(edge,0)+1
    boundary=[e for e,n in counts.items() if n==1]
    adjacency:Dict[int,List[int]]={}
    for a,b in boundary:adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    unused=set(boundary);loops=[]
    while unused:
        first=next(iter(unused));start,cur=first;prev=start;ids=[start,cur];unused.discard(first)
        for _ in range(len(boundary)+2):
            choices=[n for n in adjacency.get(cur,[]) if ((cur,n) if cur<n else (n,cur)) in unused]
            if not choices:break
            nxt=choices[0]
            edge=(cur,nxt) if cur<nxt else (nxt,cur);unused.discard(edge)
            prev,cur=cur,nxt
            if cur==start:break
            ids.append(cur)
        if cur==start and len(ids)>=3:loops.append([mat_apply(matrix,points[i]) for i in ids])
    return loops


def dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def signed_area(pts: Sequence[Point]) -> float:
    if len(pts) < 3:
        return 0.0
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
                     pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def path_length(pts: Sequence[Point], closed: bool = True) -> float:
    n = len(pts)
    if n < 2:
        return 0.0
    end = n if closed else n - 1
    return sum(dist(pts[i], pts[(i + 1) % n]) for i in range(end))


def point_in_poly(p: Point, poly: Sequence[Point]) -> bool:
    x, y = p
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi:
            inside = not inside
        j = i
    return inside


def clean_points(pts: Sequence[Point], closed: bool) -> List[Point]:
    out: List[Point] = []
    for p in pts:
        q = (float(p[0]), float(p[1]))
        if not out or dist(out[-1], q) > EPS:
            out.append(q)
    if closed and len(out) > 2 and dist(out[0], out[-1]) < 1e-5:
        out.pop()
    return out


def depth_from_layer(layer: str) -> Optional[float]:
    """Recognise e.g. DEPTH_1.5, DEPTH-1.5, Z-2.2, POCKET_0.8."""
    text = layer.upper().replace(",", ".")
    m = re.search(r"(?:DEPTH|POCKET|Z)\s*[_=:-]?\s*(-?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    value = abs(float(m.group(1)))
    return value if value > EPS else None


def line_intersection(p: Point, r: Point, q: Point, s: Point) -> Optional[Point]:
    cross = r[0] * s[1] - r[1] * s[0]
    if abs(cross) < EPS:
        return None
    qp = (q[0] - p[0], q[1] - p[1])
    t = (qp[0] * s[1] - qp[1] * s[0]) / cross
    return p[0] + t * r[0], p[1] + t * r[1]


def segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    return ((o1 > EPS and o2 < -EPS) or (o1 < -EPS and o2 > EPS)) and \
           ((o3 > EPS and o4 < -EPS) or (o3 < -EPS and o4 > EPS))


def point_in_rect(p:Point,rect:Tuple[float,float,float,float])->bool:
    x0,y0,x1,y1=rect
    return x0-EPS<=p[0]<=x1+EPS and y0-EPS<=p[1]<=y1+EPS


def segment_intersects_rect(a:Point,b:Point,rect:Tuple[float,float,float,float])->bool:
    """Liang-Barsky segment/rectangle test, including edge touches."""
    if point_in_rect(a,rect) or point_in_rect(b,rect):return True
    x0,y0,x1,y1=rect;dx=b[0]-a[0];dy=b[1]-a[1];lo,hi=0.0,1.0
    for p,q in ((-dx,a[0]-x0),(dx,x1-a[0]),(-dy,a[1]-y0),(dy,y1-a[1])):
        if abs(p)<EPS:
            if q<-EPS:return False
            continue
        t=q/p
        if p<0:lo=max(lo,t)
        else:hi=min(hi,t)
        if lo>hi+EPS:return False
    return True


def contour_in_selection_rect(contour:Contour,rect:Tuple[float,float,float,float],crossing:bool)->bool:
    """CAD window selection: contained L->R, crossing R->L."""
    if not contour.points:return False
    if not crossing:return all(point_in_rect(p,rect) for p in contour.points)
    if any(point_in_rect(p,rect) for p in contour.points):return True
    n=len(contour.points);end=n if contour.closed else n-1
    return any(segment_intersects_rect(contour.points[i],contour.points[(i+1)%n],rect)
               for i in range(max(0,end)))


def self_intersection_count(pts: Sequence[Point], limit: int = 5) -> int:
    n=len(pts); hits=0
    for i in range(n):
        a,b=pts[i],pts[(i+1)%n]
        aminx,amaxx=sorted((a[0],b[0])); aminy,amaxy=sorted((a[1],b[1]))
        for j in range(i+1,n):
            if j==i or j==(i+1)%n or i==(j+1)%n: continue
            c,d=pts[j],pts[(j+1)%n]
            if max(aminx,min(c[0],d[0])) > min(amaxx,max(c[0],d[0]))+EPS: continue
            if max(aminy,min(c[1],d[1])) > min(amaxy,max(c[1],d[1]))+EPS: continue
            if segments_cross(a,b,c,d):
                hits+=1
                if hits>=limit: return hits
    return hits


def trim_small_self_loops(pts: Sequence[Point], max_cuts: int = 20) -> Tuple[List[Point], List[List[Point]], List[Point]]:
    """Clip small self-intersection loops, retaining the largest-area closed route."""
    route=list(pts); removed:List[List[Point]]=[]; cuts:List[Point]=[]
    for _ in range(max_cuts):
        n=len(route); found=None
        for i in range(n):
            a,b=route[i],route[(i+1)%n]
            for j in range(i+1,n):
                if j==i or j==(i+1)%n or i==(j+1)%n:continue
                c,d=route[j],route[(j+1)%n]
                if segments_cross(a,b,c,d):
                    hit=line_intersection(a,(b[0]-a[0],b[1]-a[1]),c,(d[0]-c[0],d[1]-c[1]))
                    if hit is not None:found=(i,j,hit);break
            if found:break
        if not found:break
        i,j,hit=found
        loop_a=clean_points([hit]+route[i+1:j+1]+[hit],True)
        loop_b=clean_points([hit]+route[j+1:]+route[:i+1]+[hit],True)
        if len(loop_a)<3 or len(loop_b)<3:break
        if abs(signed_area(loop_a))>=abs(signed_area(loop_b)):
            route,discard=loop_a,loop_b
        else:
            route,discard=loop_b,loop_a
        removed.append(discard+[discard[0]]);cuts.append(hit)
    return route,removed,cuts


def compensated_route(contour: Contour, tool_d: float, auto_trim: bool = False,
                      source_points: Optional[Sequence[Point]] = None) -> Tuple[List[Point],List[List[Point]],List[Point]]:
    pts=list(source_points) if source_points is not None else list(contour.points)
    amount=tool_d/2 if contour.role=="outer" else -tool_d/2
    raw=offset_polygon(pts,amount)
    if auto_trim and self_intersection_count(raw):
        return trim_small_self_loops(raw)
    return raw,[],[]


def offset_polygon(pts: Sequence[Point], amount: float) -> List[Point]:
    """Miter offset. Positive means geometrically outward, independent of winding."""
    n = len(pts)
    if n < 3 or abs(amount) < EPS:
        return list(pts)
    orientation = 1.0 if signed_area(pts) > 0 else -1.0
    # For CCW, right normal is outward.
    side = -orientation
    shifted = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        if ln < EPS:
            shifted.append((a, (1.0, 0.0)))
            continue
        nx, ny = side * (-dy / ln) * amount, side * (dx / ln) * amount
        shifted.append(((a[0] + nx, a[1] + ny), (dx, dy)))
    out = []
    miter_limit = max(abs(amount) * 8.0, 0.01)
    for i in range(n):
        p1, r1 = shifted[(i - 1) % n]
        p2, r2 = shifted[i]
        hit = line_intersection(p1, r1, p2, r2)
        if hit is None or dist(hit, pts[i]) > miter_limit:
            # Bevel-like fallback for parallel/very acute corners.
            hit = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
        out.append(hit)
    return out


def reverse_if_needed(pts: List[Point], want_ccw: bool) -> List[Point]:
    is_ccw = signed_area(pts) > 0
    return list(reversed(pts)) if is_ccw != want_ccw else pts


def point_at(pts: Sequence[Point], s: float, closed: bool = True) -> Tuple[Point, int, float]:
    total = path_length(pts, closed)
    if total <= EPS:
        return pts[0], 0, 0.0
    s = s % total if closed else min(max(s, 0), total)
    nseg = len(pts) if closed else len(pts) - 1
    run = 0.0
    for i in range(nseg):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        ln = dist(a, b)
        if run + ln >= s - EPS:
            t = 0 if ln < EPS else (s - run) / ln
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), i, t
        run += ln
    return pts[-1], nseg - 1, 1.0


def nearest_path_distance(pts: Sequence[Point], p: Point, closed: bool = True) -> Tuple[float, float]:
    best_d, best_s, run = 1e100, 0.0, 0.0
    nseg = len(pts) if closed else len(pts) - 1
    for i in range(nseg):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        vx, vy = b[0] - a[0], b[1] - a[1]
        ll = vx * vx + vy * vy
        t = 0.0 if ll < EPS else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / ll))
        q = (a[0] + vx * t, a[1] + vy * t)
        d = dist(p, q)
        if d < best_d:
            best_d, best_s = d, run + math.sqrt(ll) * t
        run += math.sqrt(ll)
    return best_d, best_s


def rotate_closed_path(pts: Sequence[Point], s: float) -> List[Point]:
    """Rotate a closed polyline so the requested path position becomes point 0."""
    if len(pts) < 3 or abs(s) < EPS:
        return list(pts)
    p, seg, t = point_at(pts, s, True)
    if t <= EPS:
        start = seg
        return list(pts[start:]) + list(pts[:start])
    if t >= 1.0 - EPS:
        start = (seg + 1) % len(pts)
        return list(pts[start:]) + list(pts[:start])
    return [p] + list(pts[seg + 1:]) + list(pts[:seg + 1])


def polygon_centroid(pts: Sequence[Point]) -> Point:
    a = signed_area(pts)
    if abs(a) < EPS:
        return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))
    cx = cy = 0.0
    for i, p in enumerate(pts):
        q = pts[(i+1) % len(pts)]
        cross = p[0]*q[1] - q[0]*p[1]
        cx += (p[0]+q[0])*cross; cy += (p[1]+q[1])*cross
    return cx/(6*a), cy/(6*a)


def rotated_group_size(source:Sequence[Contour],angle_deg:float)->Tuple[float,float]:
    angle=math.radians(angle_deg);ca,sa=math.cos(angle),math.sin(angle)
    pts=[(p[0]*ca-p[1]*sa,p[0]*sa+p[1]*ca) for c in source for p in c.points]
    if not pts:raise ValueError("어레이할 형상이 없습니다.")
    return max(p[0] for p in pts)-min(p[0] for p in pts),max(p[1] for p in pts)-min(p[1] for p in pts)


def oriented_contour_group(source:Sequence[Contour],angle_deg:float)->Tuple[List[Contour],float,float]:
    """Rotate one complete part and normalize its lower-left bound to (0, 0)."""
    angle=math.radians(angle_deg);ca,sa=math.cos(angle),math.sin(angle)
    def rot(p:Point)->Point:return p[0]*ca-p[1]*sa,p[0]*sa+p[1]*ca
    group=copy.deepcopy(list(source))
    rotated=[rot(p) for c in group for p in c.points]
    if not rotated:raise ValueError("어레이할 형상이 없습니다.")
    minx=min(p[0] for p in rotated);miny=min(p[1] for p in rotated)
    maxx=max(p[0] for p in rotated);maxy=max(p[1] for p in rotated)
    def move(p:Point)->Point:
        q=rot(p);return q[0]-minx,q[1]-miny
    for c in group:
        c.points=[move(p) for p in c.points]
        c.bridges=[(move(a),move(b)) for a,b in c.bridges]
        c.cut_order=None
    return group,maxx-minx,maxy-miny


def contour_group_key(c:Contour)->Tuple[int,int]:
    return c.object_id,c.instance_id or 1


def contour_group_bounds(contours:Sequence[Contour],key:Tuple[int,int])->Optional[Tuple[float,float,float,float]]:
    pts=[p for c in contours if contour_group_key(c)==key for p in c.points]
    if not pts:return None
    return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)


def contour_group_bounds_map(contours:Sequence[Contour])->Dict[Tuple[int,int],Tuple[float,float,float,float]]:
    bounds:Dict[Tuple[int,int],List[float]]={}
    for c in contours:
        if not c.object_id or not c.points:continue
        key=contour_group_key(c);x0=min(p[0] for p in c.points);y0=min(p[1] for p in c.points)
        x1=max(p[0] for p in c.points);y1=max(p[1] for p in c.points)
        if key not in bounds:bounds[key]=[x0,y0,x1,y1]
        else:
            b=bounds[key];b[0]=min(b[0],x0);b[1]=min(b[1],y0);b[2]=max(b[2],x1);b[3]=max(b[3],y1)
    return {key:(b[0],b[1],b[2],b[3]) for key,b in bounds.items()}


def move_contour_group(contours:Sequence[Contour],key:Tuple[int,int],dx:float,dy:float)->int:
    changed=0
    for c in contours:
        if contour_group_key(c)!=key:continue
        c.points=[(x+dx,y+dy) for x,y in c.points]
        c.bridges=[((a[0]+dx,a[1]+dy),(b[0]+dx,b[1]+dy)) for a,b in c.bridges]
        changed+=1
    return changed


def rotate_contour_group(contours:Sequence[Contour],key:Tuple[int,int],degrees:float=90.0)->int:
    bounds=contour_group_bounds(contours,key)
    if bounds is None:return 0
    x0,y0,x1,y1=bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
    angle=math.radians(degrees);ca,sa=math.cos(angle),math.sin(angle)
    def rot(p:Point)->Point:
        x,y=p[0]-cx,p[1]-cy
        return cx+x*ca-y*sa,cy+x*sa+y*ca
    changed=0
    for c in contours:
        if contour_group_key(c)!=key:continue
        c.points=[rot(p) for p in c.points]
        c.bridges=[(rot(a),rot(b)) for a,b in c.bridges]
        changed+=1
    return changed


def best_oriented_array_layout(stock_w:float,stock_h:float,gap:float,edge:float,
                               orientations:Sequence[Tuple[float,float,float]],
                               quantity:int=0)->List[Tuple[float,float,float]]:
    """Mix arbitrary-angle rows using a 0.5 mm dynamic-programming height search."""
    usable_w=stock_w-2*edge;usable_h=stock_h-2*edge
    if min(usable_w,usable_h)<=EPS:return []
    row_types=[]
    for angle,w,h in orientations:
        if min(w,h)<=EPS or w>usable_w+EPS or h>usable_h+EPS:continue
        cap=max(0,int(math.floor((usable_w+gap)/(w+gap))))
        if cap:row_types.append((float(angle),w,h,cap))
    if not row_types:return []
    scale=2.0;budget=max(0,int(math.floor((usable_h+gap)*scale+EPS)))
    costs=[max(1,int(math.ceil((h+gap)*scale-EPS))) for _,_,h,_ in row_types]
    dp=[-10**9]*(budget+1);prev=[None]*(budget+1);dp[0]=0
    for used in range(budget+1):
        if dp[used]<0:continue
        for kind,cost in enumerate(costs):
            nxt=used+cost
            if nxt<=budget and dp[used]+row_types[kind][3]>dp[nxt]:
                dp[nxt]=dp[used]+row_types[kind][3];prev[nxt]=(used,kind)
    def score(i:int):return (min(dp[i],quantity) if quantity>0 else dp[i],-i)
    end=max(range(budget+1),key=score)
    if dp[end]<=0:return []
    rows=[]
    while end and prev[end] is not None:
        end,kind=prev[end];rows.append(kind)
    rows.reverse();placements=[];y=edge
    for kind in rows:
        angle,w,h,cap=row_types[kind]
        for col in range(cap):
            if quantity>0 and len(placements)>=quantity:return placements
            placements.append((angle,edge+col*(w+gap),y))
        y+=h+gap
    return placements


def best_array_layout(stock_w:float,stock_h:float,gap:float,edge:float,
                      part_w:float,part_h:float,allow_rotate:bool=True,
                      quantity:int=0)->List[Tuple[float,float,float]]:
    """Compatibility wrapper for the normal mixed 0°/90° layout."""
    types=[(0,part_w,part_h)]
    if allow_rotate and abs(part_w-part_h)>EPS:types.append((90,part_h,part_w))
    return best_oriented_array_layout(stock_w,stock_h,gap,edge,types,quantity)


def normalized_contour_group(source:Sequence[Contour])->Tuple[List[Contour],float,float,Point]:
    """Deep-copy a complete part and move its lower-left bound to (0, 0)."""
    group=copy.deepcopy(list(source));pts=[p for c in group for p in c.points]
    if not pts:raise ValueError("객체에 배치할 형상이 없습니다.")
    minx=min(p[0] for p in pts);miny=min(p[1] for p in pts)
    maxx=max(p[0] for p in pts);maxy=max(p[1] for p in pts)
    def move(p:Point)->Point:return p[0]-minx,p[1]-miny
    for c in group:
        c.points=[move(p) for p in c.points]
        c.bridges=[(move(a),move(b)) for a,b in c.bridges]
        c.cut_order=None
    return group,maxx-minx,maxy-miny,(minx,miny)


def part_preview_offsets(parts:Sequence[PartObject],gap:float)->Dict[int,Point]:
    """Choose source-layout offsets for one STEP, otherwise a readable row."""
    if not parts:return {}
    multi=len(parts)>1
    preserve=(multi and bool(parts[0].layout_group) and
              all(part.layout_group==parts[0].layout_group for part in parts))
    if not multi or preserve:return {part.object_id:part.display_offset for part in parts}
    offsets={};cursor_x=0.0
    for part in parts:
        pts=[p for contour in part.contours for p in contour.points]
        width=(max(p[0] for p in pts)-min(p[0] for p in pts)) if pts else 0.0
        offsets[part.object_id]=(cursor_x,0.0);cursor_x+=width+gap
    return offsets


def _split_free_rectangles(free_rects:Sequence[Tuple[float,float,float,float]],
                           used:Tuple[float,float,float,float])->List[Tuple[float,float,float,float]]:
    """MaxRects split/prune step. Rectangles are x, y, width, height."""
    ux,uy,uw,uh=used;ur=ux+uw;ut=uy+uh;out=[]
    for fx,fy,fw,fh in free_rects:
        fr=fx+fw;ft=fy+fh
        if ur<=fx+EPS or ux>=fr-EPS or ut<=fy+EPS or uy>=ft-EPS:
            out.append((fx,fy,fw,fh));continue
        if ux>fx+EPS:out.append((fx,fy,ux-fx,fh))
        if ur<fr-EPS:out.append((ur,fy,fr-ur,fh))
        if uy>fy+EPS:out.append((fx,fy,fw,uy-fy))
        if ut<ft-EPS:out.append((fx,ut,fw,ft-ut))
    cleaned=[]
    for i,r in enumerate(out):
        x,y,w,h=r
        if w<=EPS or h<=EPS:continue
        contained=False
        for j,q in enumerate(out):
            if i==j:continue
            qx,qy,qw,qh=q
            if x>=qx-EPS and y>=qy-EPS and x+w<=qx+qw+EPS and y+h<=qy+qh+EPS:
                if (qw*qh>w*h+EPS) or j<i:
                    contained=True;break
        if not contained:cleaned.append(r)
    return cleaned


def best_mixed_nesting(parts:Sequence[PartObject],stock_w:float,stock_h:float,gap:float,edge:float,
                       angles:Sequence[float],progress:Optional[Callable[[float,str],None]]=None
                       )->Tuple[List[NestPlacement],Dict[int,int]]:
    """Pack requested quantities of different files with safe rotated bounding boxes."""
    usable_w=stock_w-2*edge;usable_h=stock_h-2*edge
    if min(usable_w,usable_h)<=EPS:return [],{}
    orientation_map:Dict[int,List[Tuple[float,float,float]]]={}
    items=[];area_by_id={};order_by_id={}
    for order,part in enumerate(p for p in parts if p.enabled and p.quantity>0):
        order_by_id[part.object_id]=order
        choices=[]
        for angle in angles:
            w,h=rotated_group_size(part.contours,angle)
            if w<=usable_w+EPS and h<=usable_h+EPS:
                candidate=(float(angle),w,h)
                if not any(abs(w-q[1])<1e-6 and abs(h-q[2])<1e-6 for q in choices):choices.append(candidate)
        if not choices:continue
        orientation_map[part.object_id]=choices
        area_by_id[part.object_id]=choices[0][1]*choices[0][2]
        items.extend((part.object_id,i) for i in range(1,part.quantity+1))
    if not items:return [],{}

    def pack(sequence:Sequence[Tuple[int,int]],choices_by_id:Dict[int,List[Tuple[float,float,float]]],
             heuristic:int)->List[NestPlacement]:
        # One trailing gap is added to the bin so the last part can end exactly at the edge margin.
        free=[(0.0,0.0,usable_w+gap,usable_h+gap)];placed=[]
        for object_id,instance_id in sequence:
            best=None
            for angle,w,h in choices_by_id.get(object_id,()):
                rw,rh=w+gap,h+gap
                for fi,(x,y,fw,fh) in enumerate(free):
                    if rw<=fw+EPS and rh<=fh+EPS:
                        if heuristic==0:score=(y,x,rw*rh,max(y+rh,x+rw),min(fw-rw,fh-rh),abs(angle))
                        elif heuristic==1:score=(rw*rh,y,x,fw*fh-rw*rh,min(fw-rw,fh-rh),abs(angle))
                        else:score=(min(fw-rw,fh-rh),fw*fh-rw*rh,max(y+rh,x+rw),y,x,rw*rh,abs(angle))
                        if best is None or score<best[0]:best=(score,fi,angle,w,h,x,y,rw,rh)
            if best is None:continue
            _,_,angle,w,h,x,y,rw,rh=best
            placed.append(NestPlacement(object_id,instance_id,angle,edge+x,edge+y,w,h))
            free=_split_free_rectangles(free,(x,y,rw,rh))
        return placed

    orders=[]
    orders.append(sorted(items,key=lambda z:(-area_by_id.get(z[0],0),order_by_id.get(z[0],0),z[1])))
    orders.append(sorted(items,key=lambda z:(-max(max(q[1],q[2]) for q in orientation_map.get(z[0],[(0,0,0)])),
                                             -area_by_id.get(z[0],0),z[1])))
    orders.append(sorted(items,key=lambda z:(order_by_id.get(z[0],0),z[1])))
    orders.append(sorted(items,key=lambda z:(z[1],-area_by_id.get(z[0],0),order_by_id.get(z[0],0))))
    axial_map={oid:[q for q in choices if abs(q[0]%90)<1e-6] for oid,choices in orientation_map.items()}
    compact_map={}
    for oid,choices in orientation_map.items():
        min_area=min(q[1]*q[2] for q in choices)
        compact_map[oid]=[q for q in choices if q[1]*q[2]<=min_area+1e-6]
    orientation_strategies=(axial_map,compact_map,orientation_map)
    best_placed=[];best_score=(-1,)+(-1e100,)*6
    trial=0;trial_total=max(1,len(orders)*len(orientation_strategies)*3)
    for sequence in orders:
        for choices in orientation_strategies:
            for heuristic in range(3):
                trial+=1
                if progress:progress(trial/trial_total*100.0,f"자동배치 조합 계산 {trial}/{trial_total}")
                placed=pack(sequence,choices,heuristic)
                used_width=max((p.x+p.width for p in placed),default=edge)-edge
                used_height=max((p.y+p.height for p in placed),default=edge)-edge
                envelope=used_width*used_height;total_box=sum(p.width*p.height for p in placed)
                angled=sum(abs(p.angle%90)>1e-6 for p in placed)
                score=(len(placed),-envelope,-max(used_width,used_height),-used_height,-used_width,-total_box,-angled)
                if score>best_score:best_score=score;best_placed=placed
    counts:Dict[int,int]={}
    for p in best_placed:counts[p.object_id]=counts.get(p.object_id,0)+1
    return best_placed,counts


def contour_shape_score(a: Sequence[Point], b: Sequence[Point]) -> Optional[float]:
    """Return a small score for coincident STEP loops, or None when they differ."""
    if len(a) < 3 or len(b) < 3:
        return None
    ca, cb = polygon_centroid(a), polygon_centroid(b)
    ax0,ax1=min(p[0] for p in a),max(p[0] for p in a)
    ay0,ay1=min(p[1] for p in a),max(p[1] for p in a)
    bx0,bx1=min(p[0] for p in b),max(p[0] for p in b)
    by0,by1=min(p[1] for p in b),max(p[1] for p in b)
    span=max(ax1-ax0,ay1-ay0,bx1-bx0,by1-by0,1.0)
    center_gap=dist(ca,cb);size_gap=abs((ax1-ax0)-(bx1-bx0))+abs((ay1-ay0)-(by1-by0))
    aa,ab=abs(signed_area(a)),abs(signed_area(b))
    area_gap=abs(aa-ab)/max(aa,ab,EPS)
    if center_gap>max(.20,span*.02) or size_gap>max(.35,span*.05) or area_gap>.12:
        return None
    return center_gap+size_gap+area_gap*span


def step_faces_to_2d_features(model: StepModel, selected_faces: Sequence[int],
                              matrix: Sequence[Sequence[float]],
                              progress:Optional[Callable[[float,str],None]]=None
                              ) -> Tuple[List[Contour],float,int,int]:
    """Flatten several coplanar STEP faces into one CAM job."""
    def report(value:float,message:str):
        if progress:progress(value,message)
    face_indices=list(dict.fromkeys(int(i) for i in selected_faces))
    if not face_indices:raise ValueError("가공면을 하나 이상 선택하세요.")
    if any(i<0 or i>=len(model.faces) for i in face_indices):raise ValueError("선택면 번호가 올바르지 않습니다.")
    report(3,f"선택면 {len(face_indices)}개 윤곽 분석 중")
    all_vertices=[mat_apply(matrix,p) for p in model.vertices]
    global_bottom=min((p[2] for p in all_vertices),default=0.0)
    if len(model.face_components)!=len(model.faces) or not model.component_vertices:
        model.face_components,model.component_vertices=step_mesh_components(model.faces)
    transformed_components={component:[mat_apply(matrix,p) for p in points]
                            for component,points in model.component_vertices.items()}
    component_count=len(set(model.face_components))
    groups=[]
    for part_no,face_index in enumerate(face_indices,1):
        top_loops=face_boundary_loops(model.faces[face_index],matrix)
        prepared=[]
        for loop in top_loops:
            pts=clean_points([(p[0],p[1]) for p in loop],True)
            if len(pts)>=3 and abs(signed_area(pts))>EPS:prepared.append(pts)
        if not prepared:raise ValueError(f"면 {face_index+1}의 2D 경계를 만들지 못했습니다.")
        prepared.sort(key=lambda p:abs(signed_area(p)),reverse=True)
        top_z=mat_apply(matrix,model.faces[face_index].center)[2]
        outer=prepared[0];local_vertices=[]
        for point in all_vertices:
            xy=(point[0],point[1])
            if point_in_poly(xy,outer) or nearest_path_distance(outer,xy,True)[0]<=.08:local_vertices.append(point)
        component=model.face_components[face_index]
        component_points=transformed_components.get(component,[])
        component_bottom=min((p[2] for p in component_points),default=top_z)
        if component_bottom<top_z-.005:
            bottom_z=component_bottom
        elif component_count==1:
            # Compatibility fallback for synthetic/mesh-only files that contain
            # just the selected top face but still expose exact B-Rep vertices.
            bottom_z=global_bottom
        else:
            bottom_z=min((p[2] for p in local_vertices),default=global_bottom)
        local_stock=max(top_z-bottom_z,.01);through_layer=f"STEP_P{part_no}_THROUGH_{local_stock:.3f}"
        contours=[]
        for loop_no,pts in enumerate(prepared):
            is_outer=loop_no==0
            contours.append(Contour(pts,True,
                                    f"STEP part {part_no} outer" if is_outer else f"STEP part {part_no} opening {loop_no}",
                                    layer=through_layer,forced_role="outer" if is_outer else "inner",tabs_enabled=is_outer))
        groups.append({"part":part_no,"face":face_index,"top_z":top_z,"stock":local_stock,
                       "through_layer":through_layer,"contours":contours})

    top_levels=[g["top_z"] for g in groups]
    if max(top_levels)-min(top_levels)>.05:
        raise ValueError("선택한 가공면들의 Z 높이가 서로 다릅니다. 같은 높이의 면만 선택하세요.")
    stocks=[g["stock"] for g in groups]
    if max(stocks)-min(stocks)>.05:
        raise ValueError("선택한 부품들의 판 두께가 서로 다릅니다. 같은 두께의 부품만 한 번에 가져오세요.")
    stock=sum(stocks)/len(stocks)

    report(18,"포켓·카운터보어 후보 면 분석 중")
    floor_candidates=[]
    face_total=max(1,len(model.faces))
    for fi,face in enumerate(model.faces):
        report(18+57*(fi+1)/face_total,f"깊이 면 검사 {fi+1}/{len(model.faces)}")
        if fi in face_indices:continue
        tv=[mat_apply(matrix,p) for p in face.vertices]
        if not tv:continue
        zs=[p[2] for p in tv]
        if max(zs)-min(zs)>.04:continue
        z=sum(zs)/len(zs)
        loops=[]
        for loop in face_boundary_loops(face,matrix):
            pts=clean_points([(p[0],p[1]) for p in loop],True)
            if len(pts)>=3 and abs(signed_area(pts))>EPS:loops.append(pts)
        if loops:
            loops.sort(key=lambda p:abs(signed_area(p)),reverse=True)
            floor_candidates.append((z,fi,loops))

    report(82,"포켓·카운터보어 대응 중")
    depth_count=added_count=processed=0;combined=[]
    total_work=max(1,len(groups)*max(1,len(floor_candidates)))
    for group in groups:
        contours=group["contours"];floors=[]
        for z,fi,loops in floor_candidates:
            depth=group["top_z"]-z
            if depth<=.04 or depth>=group["stock"]-.04:continue
            if any(contour_shape_score(c.points,loops[0]) is not None for c in contours[1:]):
                floors.append((depth,fi,loops))
        floors.sort(key=lambda item:item[0])
        for depth,fi,loops in floors:
            processed+=1;report(82+15*processed/total_work,f"부품 {group['part']} 깊이 형상 대응")
            floor_outer=loops[0];matches=[]
            for contour in contours[1:]:
                score=contour_shape_score(contour.points,floor_outer)
                if score is not None:matches.append((score,contour))
            if not matches:continue
            matched=min(matches,key=lambda item:item[0])[1]
            if matched.target_depth is None or depth<matched.target_depth:
                matched.target_depth=depth;matched.name=f"STEP part {group['part']} pocket/counterbore Z-{depth:.3f}"
                matched.layer=f"STEP_P{group['part']}_DEPTH_{depth:.3f}";depth_count+=1
            for inner in loops[1:]:
                center=polygon_centroid(inner)
                if not point_in_poly(center,floor_outer):continue
                if any(contour_shape_score(c.points,inner) is not None for c in contours):continue
                added_count+=1
                contours.append(Contour(inner,True,f"STEP part {group['part']} counterbore through",
                                        layer=group["through_layer"],forced_role="inner",tabs_enabled=False))
        combined.extend(contours)
    classify_contours(combined)
    report(100,f"STEP 면 {len(groups)}개 2D 변환 완료")
    return combined,stock,depth_count,added_count


def step_to_2d_features(model: StepModel, selected_face: int,
                        matrix: Sequence[Sequence[float]],
                        progress:Optional[Callable[[float,str],None]]=None
                        ) -> Tuple[List[Contour],float,int,int]:
    """Backward-compatible single-face STEP conversion."""
    return step_faces_to_2d_features(model,[selected_face],matrix,progress)


def split_step_contour_parts(contours:Sequence[Contour])->List[Tuple[int,List[Contour]]]:
    """Split multi-face STEP output into independently arrayable parts."""
    grouped:Dict[int,List[Contour]]={};unmatched=[]
    for contour in contours:
        match=re.match(r"STEP_P(\d+)_",str(contour.layer),re.IGNORECASE)
        if match:grouped.setdefault(int(match.group(1)),[]).append(contour)
        else:unmatched.append(contour)
    if len(grouped)<=1:return [(next(iter(grouped),1),list(contours))]
    if unmatched:grouped[min(grouped)].extend(unmatched)
    return [(part,grouped[part]) for part in sorted(grouped)]


def safe_interior_point(pts: Sequence[Point]) -> Point:
    """Find a practical interior start point for a hole/polygon."""
    minx,maxx=min(p[0] for p in pts),max(p[0] for p in pts)
    miny,maxy=min(p[1] for p in pts),max(p[1] for p in pts)
    candidates = [polygon_centroid(pts), ((minx+maxx)/2,(miny+maxy)/2)]
    candidates += [(minx+(maxx-minx)*i/10, miny+(maxy-miny)*j/10)
                   for i in range(1,10) for j in range(1,10)]
    inside = [p for p in candidates if point_in_poly(p, pts)]
    if not inside:
        return pts[0]
    return max(inside, key=lambda p: nearest_path_distance(pts, p, True)[0])


@dataclass
class LeadPlan:
    entry: Point
    mode: str
    center: Optional[Point] = None
    clockwise: bool = False


def lead_arc_points(plan: LeadPlan, end: Point, segments: int = 14) -> List[Point]:
    if plan.center is None:return [plan.entry,end]
    cx,cy=plan.center
    a0=math.atan2(plan.entry[1]-cy,plan.entry[0]-cx);a1=math.atan2(end[1]-cy,end[0]-cx)
    sweep=a1-a0
    if plan.clockwise:
        while sweep>=0:sweep-=2*math.pi
    else:
        while sweep<=0:sweep+=2*math.pi
    r=dist(plan.entry,plan.center)
    return [(cx+r*math.cos(a0+sweep*i/segments),cy+r*math.sin(a0+sweep*i/segments))
            for i in range(segments+1)]


def lead_plan(contour: Contour, route: Sequence[Point], lead_len: float) -> LeadPlan:
    """Prefer a quarter-circle lead in waste material, then linear, then centre."""
    p0=route[0]
    if not contour.closed or lead_len<=EPS or len(route)<2:return LeadPlan(p0,"none")
    p1=route[1];tx,ty=p1[0]-p0[0],p1[1]-p0[1];ln=math.hypot(tx,ty) or 1.0
    tx,ty=tx/ln,ty/ln;nx,ny=-ty,tx
    want_inside=contour.role=="inner"
    # For holes, preserve the same cutter-radius clearance as the compensated
    # route instead of merely checking that the centre is inside the outline.
    safe_boundary=route if want_inside else contour.points
    cutter_clearance=nearest_path_distance(contour.points,p0,True)[0] if want_inside else 0.0
    def valid_lead_point(q:Point)->bool:
        if not want_inside:return not point_in_poly(q,contour.points)
        return (point_in_poly(q,contour.points) and
                nearest_path_distance(contour.points,q,True)[0]>=cutter_clearance-.02)
    for radius in (lead_len,lead_len*.75,lead_len*.5):
        if radius<=.05:continue
        for side in (1.0,-1.0):
            center=(p0[0]+side*nx*radius,p0[1]+side*ny*radius)
            entry=(center[0]-tx*radius,center[1]-ty*radius)
            plan=LeadPlan(entry,"arc-inside" if want_inside else "arc-outside",center,clockwise=side<0)
            samples=lead_arc_points(plan,p0,18)[:-1]
            valid=all(valid_lead_point(q) for q in samples)
            if valid:return plan
    if want_inside:
        center=safe_interior_point(safe_boundary);available=dist(center,p0)
        if available>EPS and available>=lead_len:
            candidate=(p0[0]+(center[0]-p0[0])*lead_len/available,
                       p0[1]+(center[1]-p0[1])*lead_len/available)
            if all(valid_lead_point((candidate[0]+(p0[0]-candidate[0])*i/10,
                                     candidate[1]+(p0[1]-candidate[1])*i/10))
                   for i in range(10)):
                return LeadPlan(candidate,"inside-radial")
        return LeadPlan(center,"center-fallback")
    candidate=(p0[0]-tx*lead_len,p0[1]-ty*lead_len)
    return LeadPlan(candidate,"outside-tangent")


def lead_point(contour: Contour, route: Sequence[Point], lead_len: float) -> Tuple[Point, str]:
    plan=lead_plan(contour,route,lead_len)
    return plan.entry,plan.mode


def contour_toolpath_issues(contour: Contour, tool_d: float, auto_trim: bool = False) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings) for compensated profile geometry."""
    errors: List[str]=[]; warnings: List[str]=[]
    if not contour.enabled or contour.safety_excluded or not contour.closed or len(contour.points)<3:
        return errors,warnings
    expected="inner" if contour.depth%2 else "outer"
    if contour.forced_role in ("inner","outer") and contour.role!=expected:
        warnings.append(f"자동 판정 {expected} / 수동 지정 {contour.role} 충돌")
    route,removed,cuts=compensated_route(contour,tool_d,auto_trim)
    if removed: warnings.append(f"꼬인 작은 루프 자동 절단 {len(removed)}곳")
    hits=self_intersection_count(route)
    if hits: errors.append(f"공구 보정경로 자기교차 {hits}곳 이상")
    original_area=signed_area(contour.points); route_area=signed_area(route)
    if abs(route_area)<EPS or original_area*route_area<=0:
        errors.append("공구 보정 후 경로 면적 붕괴/방향 반전")
    if contour.role=="inner":
        width=max(p[0] for p in contour.points)-min(p[0] for p in contour.points)
        height=max(p[1] for p in contour.points)-min(p[1] for p in contour.points)
        if min(width,height)<=tool_d+EPS: errors.append("내부 형상 최소 크기가 공구 지름 이하")
        samples=route+[((route[i][0]+route[(i+1)%len(route)][0])/2,
                        (route[i][1]+route[(i+1)%len(route)][1])/2) for i in range(len(route))]
        outside=sum(not point_in_poly(p,contour.points) for p in samples)
        if outside>max(1,len(samples)//20): errors.append("내부 보정경로가 홀/포켓 바깥으로 이탈")
    return errors,warnings


def _path_segments(pts:Sequence[Point],closed:bool)->List[Tuple[Point,Point]]:
    if len(pts)<2:return []
    pairs=list(zip(pts,pts[1:]))
    if closed:pairs.append((pts[-1],pts[0]))
    return pairs


def _point_segment_distance(p:Point,a:Point,b:Point)->float:
    dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
    if den<=EPS:return dist(p,a)
    t=max(0.0,min(1.0,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return dist(p,(a[0]+t*dx,a[1]+t*dy))


def _segment_distance(a:Point,b:Point,c:Point,d:Point)->float:
    if segments_cross(a,b,c,d):return 0.0
    return min(_point_segment_distance(a,c,d),_point_segment_distance(b,c,d),
               _point_segment_distance(c,a,b),_point_segment_distance(d,a,b))


def expected_stepped_feature_pair(a:Contour,b:Contour)->bool:
    """Treat nested inner profiles at different Z depths as one stepped hole/pocket."""
    if not (a.closed and b.closed and a.role=="inner" and b.role=="inner"):return False
    if a.object_id and b.object_id and (a.object_id!=b.object_id or a.instance_id!=b.instance_id):return False
    depth_a=a.target_depth;depth_b=b.target_depth
    if depth_a is None and depth_b is None:return False
    if depth_a is not None and depth_b is not None and abs(depth_a-depth_b)<=.01:return False
    center_a=polygon_centroid(a.points);center_b=polygon_centroid(b.points)
    return point_in_poly(center_a,b.points) or point_in_poly(center_b,a.points)


def cam_worker_count(task_count:int)->int:
    """Leave one logical CPU free for the UI and cap CAM workers to limit RAM."""
    available=max(1,(os.cpu_count() or 1)-1)
    return max(1,min(int(task_count),available,8))


_ROUTE_PARALLEL_MIN_SCORE=2_000_000
_ROUTE_WORK_PER_WORKER=2_000_000
_ROUTE_LINEAR_POINT_WEIGHT=4
_COLLISION_PARALLEL_MIN_WORK=4_000_000
_COLLISION_WORK_PER_WORKER=4_000_000
_COLLISION_REPLICATED_SEGMENT_BUDGET=800_000


def _route_parallel_workers(ordered:Sequence[Contour],auto_trim:bool)->int:
    """Choose spawn workers only when compensation is large enough to repay startup."""
    if len(ordered)<2:return 1
    score=0
    for c in ordered:
        point_count=len(c.points)
        if not c.closed:
            score+=point_count
        elif auto_trim:
            # The self-intersection scan is quadratic in the contour point count.
            score+=point_count*point_count
        else:
            score+=point_count*_ROUTE_LINEAR_POINT_WEIGHT
    if score<_ROUTE_PARALLEL_MIN_SCORE:return 1
    by_work=max(2,math.ceil(score/_ROUTE_WORK_PER_WORKER))
    return min(cam_worker_count(len(ordered)),by_work)


def _collision_parallel_workers(prepared)->int:
    """Bound collision workers by candidate work and Windows-spawn copy size."""
    task_count=len(prepared)
    if task_count<2:return 1
    cpu_workers=cam_worker_count(task_count)
    segment_count=sum(len(rsegs)+len(gsegs) for _,rsegs,gsegs,_,_ in prepared)
    if segment_count<=0:return 1
    data_workers=max(1,_COLLISION_REPLICATED_SEGMENT_BUDGET//segment_count)
    max_workers=min(cpu_workers,data_workers)
    if max_workers<2:return 1
    candidate_work=0
    work_cap=_COLLISION_WORK_PER_WORKER*max_workers
    for i,(_,rsegs,_,rb,_) in enumerate(prepared):
        for j,(_,_,gsegs,_,gb) in enumerate(prepared):
            if i==j:continue
            if rb[2]<gb[0]-EPS or rb[0]>gb[2]+EPS or rb[3]<gb[1]-EPS or rb[1]>gb[3]+EPS:continue
            candidate_work+=len(rsegs)*len(gsegs)
            if candidate_work>=work_cap:return max_workers
    if candidate_work<_COLLISION_PARALLEL_MIN_WORK:return 1
    by_work=max(2,math.ceil(candidate_work/_COLLISION_WORK_PER_WORKER))
    return min(max_workers,by_work)


_COLLISION_WORK_DATA=()
_COLLISION_WORK_RADIUS=0.0


def _collision_worker_init(prepared,radius:float):
    global _COLLISION_WORK_DATA,_COLLISION_WORK_RADIUS
    _COLLISION_WORK_DATA=prepared;_COLLISION_WORK_RADIUS=radius


def _collision_hits_for_index(index:int,prepared,radius:float)->Tuple[int,List[str]]:
    c,rsegs,_,rb,_=prepared[index];hits=[]
    for j,(other,_,gsegs,_,gb) in enumerate(prepared):
        if index==j:continue
        if expected_stepped_feature_pair(c,other):continue
        if rb[2]<gb[0]-EPS or rb[0]>gb[2]+EPS or rb[3]<gb[1]-EPS or rb[1]>gb[3]+EPS:continue
        collided=False
        for a,b in rsegs:
            aminx,amaxx=min(a[0],b[0])-radius,max(a[0],b[0])+radius
            aminy,amaxy=min(a[1],b[1])-radius,max(a[1],b[1])+radius
            for d,e in gsegs:
                if amaxx<min(d[0],e[0])-EPS or aminx>max(d[0],e[0])+EPS:continue
                if amaxy<min(d[1],e[1])-EPS or aminy>max(d[1],e[1])+EPS:continue
                if _segment_distance(a,b,d,e)<=radius+.01:collided=True;break
            if collided:break
        if collided:
            label=f"Layer {other.layer}"
            if other.object_name:label+=f" / {other.object_name} #{other.instance_id or 1}"
            hits.append(f"공구 반경 경로가 다른 형상과 충돌: {label}")
            if len(hits)>=8:break
    return index,hits


def _collision_worker(index:int)->Tuple[int,List[str]]:
    return _collision_hits_for_index(index,_COLLISION_WORK_DATA,_COLLISION_WORK_RADIUS)


def tool_sweep_collisions(contours:Sequence[Contour],tool_d:float,auto_trim:bool=False,
                          progress:Optional[Callable[[float,str],None]]=None,
                          use_parallel:bool=True)->Dict[int,List[str]]:
    """Find where the cutter-radius sweep of one path touches another model line."""
    active=[c for c in contours if c.enabled and not c.safety_excluded and len(c.points)>=2]
    radius=max(0.0,tool_d/2.0)
    prepared=[]
    for c in active:
        route=compensated_route(c,tool_d,auto_trim)[0] if c.closed else list(c.points)
        rsegs=_path_segments(route,c.closed);gsegs=_path_segments(c.points,c.closed)
        rb=(min(p[0] for p in route)-radius,min(p[1] for p in route)-radius,
            max(p[0] for p in route)+radius,max(p[1] for p in route)+radius)
        gb=(min(p[0] for p in c.points),min(p[1] for p in c.points),
            max(p[0] for p in c.points),max(p[1] for p in c.points))
        prepared.append((c,rsegs,gsegs,rb,gb))
    result:Dict[int,List[str]]={};workers=_collision_parallel_workers(prepared) if use_parallel else 1
    completed=[]
    if workers>1:
        try:
            context=mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=workers,mp_context=context,
                                     initializer=_collision_worker_init,initargs=(prepared,radius)) as pool:
                futures=[pool.submit(_collision_worker,i) for i in range(len(prepared))]
                for done,future in enumerate(as_completed(futures),1):
                    completed.append(future.result())
                    if progress:progress(done/max(len(prepared),1)*100.0,
                                         f"공구 반경 충돌검사 {done}/{len(prepared)} · {workers}코어")
        except Exception:
            completed=[]
            if progress:progress(0,"멀티코어 초기화 실패 · 1코어로 재시도")
    if not completed:
        for i in range(len(prepared)):
            completed.append(_collision_hits_for_index(i,prepared,radius))
            if progress:progress((i+1)/max(len(prepared),1)*100.0,
                                 f"공구 반경 충돌검사 {i+1}/{len(prepared)} · 1코어")
    for index,hits in completed:
        if hits:result[id(prepared[index][0])]=hits
    return result


def contour_auto_key(c: Contour) -> Tuple[float, ...]:
    group = 0 if c.role == "inner" else (0.5 if not c.closed else 1)
    return (group,
            abs(c.area) if c.role == "inner" else -c.depth,
            abs(c.area))


def _contour_center(c:Contour)->Point:
    if c.closed and len(c.points)>=3:return polygon_centroid(c.points)
    if not c.points:return (0.0,0.0)
    return (sum(p[0] for p in c.points)/len(c.points),sum(p[1] for p in c.points)/len(c.points))


def _contour_nearest_point(c:Contour,current:Point)->Tuple[float,Point]:
    if not c.points:return (float("inf"),current)
    distance,s=nearest_path_distance(c.points,current,c.closed)
    return distance,point_at(c.points,s,c.closed)[0]


def _same_inner_feature(a:Contour,b:Contour)->bool:
    """Keep concentric through-hole/counterbore profiles together."""
    if not (a.closed and b.closed and a.role=="inner" and b.role=="inner"):return False
    if a.object_id and b.object_id and (a.object_id!=b.object_id or a.instance_id!=b.instance_id):return False
    ca,cb=_contour_center(a),_contour_center(b)
    span=max(math.sqrt(max(abs(a.area),abs(b.area),EPS)),1.0)
    return dist(ca,cb)<=max(.08,span*.015)


def _inner_feature_bundles(contours:Sequence[Contour])->List[List[Contour]]:
    groups:List[List[Contour]]=[]
    for contour in contours:
        hits=[i for i,group in enumerate(groups) if any(_same_inner_feature(contour,x) for x in group)]
        if not hits:groups.append([contour]);continue
        target=groups[hits[0]];target.append(contour)
        for index in reversed(hits[1:]):target.extend(groups.pop(index))
    for group in groups:group.sort(key=lambda c:(abs(c.area),-c.depth,c.layer))
    return groups


def _nearest_contour_sequence(contours:Sequence[Contour],current:Point)->Tuple[List[Contour],Point]:
    remaining=list(contours);result=[]
    while remaining:
        index=min(range(len(remaining)),key=lambda i:(_contour_nearest_point(remaining[i],current)[0],
                                                        abs(remaining[i].area),i))
        contour=remaining.pop(index);result.append(contour)
        if contour.closed:current=_contour_nearest_point(contour,current)[1]
        elif contour.points:
            current=contour.points[-1] if dist(current,contour.points[0])<=dist(current,contour.points[-1]) else contour.points[0]
    return result,current


def ordered_contours(contours: Sequence[Contour],rapid_optimize:bool=True,
                     start_point:Point=(0.0,0.0)) -> List[Contour]:
    """Preserve manual/safe ordering, then minimize XY jumps inside each safe group."""
    active=[c for c in contours if c.enabled]
    manual=sorted((c for c in active if c.cut_order is not None),
                  key=lambda c:(c.cut_order,)+contour_auto_key(c))
    automatic=[c for c in active if c.cut_order is None]
    if not rapid_optimize:
        return manual+sorted(automatic,key=contour_auto_key)
    result=list(manual);current=start_point
    for c in manual:
        if c.closed:current=_contour_nearest_point(c,current)[1]
        elif c.points:current=c.points[-1]
    inner=[c for c in automatic if c.closed and c.role=="inner"]
    bundles=_inner_feature_bundles(inner)
    while bundles:
        index=min(range(len(bundles)),key=lambda i:min(_contour_nearest_point(c,current)[0] for c in bundles[i]))
        bundle=bundles.pop(index)
        for c in bundle:
            result.append(c);current=_contour_nearest_point(c,current)[1]
    opened=[c for c in automatic if not c.closed]
    seq,current=_nearest_contour_sequence(opened,current);result.extend(seq)
    outer=[c for c in automatic if c.closed and c.role!="inner"]
    seq,current=_nearest_contour_sequence(outer,current);result.extend(seq)
    return result


def dxf_to_contours(filename: str, chord: float = 0.35, gap_tol: float = 0.20) -> List[Contour]:
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError("DXF 불러오기는 ezdxf가 필요합니다. 명령창에서: py -m pip install ezdxf") from exc
    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()
    contours: List[Contour] = []
    loose: List[Tuple[Point, Point, str]] = []

    def arc_points(cx, cy, radius, a0, a1) -> List[Point]:
        sweep = a1 - a0
        while sweep <= 0:
            sweep += 360.0
        steps = max(8, int(math.ceil(math.radians(sweep) * radius / max(chord, .05))))
        return [(cx + radius * math.cos(math.radians(a0 + sweep * i / steps)),
                 cy + radius * math.sin(math.radians(a0 + sweep * i / steps))) for i in range(steps + 1)]

    for e in msp:
        typ = e.dxftype()
        layer = str(e.dxf.layer)
        layer_depth = depth_from_layer(layer)
        if typ == "LINE":
            loose.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), layer))
        elif typ == "LWPOLYLINE":
            # ezdxf flattening handles bulges accurately.
            try:
                pts = [(v.x, v.y) for v in e.flattening(chord)]
            except Exception:
                pts = [(v[0], v[1]) for v in e.get_points("xy")]
            closed = bool(e.closed)
            pts = clean_points(pts, closed)
            if len(pts) >= (3 if closed else 2):
                contours.append(Contour(pts, closed, "LWPOLYLINE", layer=layer, target_depth=layer_depth))
        elif typ == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            closed = bool(e.is_closed)
            pts = clean_points(pts, closed)
            if len(pts) >= (3 if closed else 2):
                contours.append(Contour(pts, closed, "POLYLINE", layer=layer, target_depth=layer_depth))
        elif typ == "CIRCLE":
            c, r = e.dxf.center, float(e.dxf.radius)
            steps = max(24, int(math.ceil(2 * math.pi * r / max(chord, .05))))
            pts = [(c.x + r * math.cos(2 * math.pi * i / steps), c.y + r * math.sin(2 * math.pi * i / steps)) for i in range(steps)]
            contours.append(Contour(pts, True, "CIRCLE", layer=layer, target_depth=layer_depth))
        elif typ == "ARC":
            c, r = e.dxf.center, float(e.dxf.radius)
            pts = arc_points(c.x, c.y, r, e.dxf.start_angle, e.dxf.end_angle)
            for a, b in zip(pts, pts[1:]):
                loose.append((a, b, layer))

    # Join individual lines/arcs by nearest matching endpoints.
    tol = max(gap_tol, 0.001)
    while loose:
        a, b, chain_layer = loose.pop(0)
        chain = [a, b]
        changed = True
        while changed and loose:
            changed = False
            for i, (u, v, seg_layer) in enumerate(loose):
                if seg_layer != chain_layer:
                    continue
                if dist(chain[-1], u) <= tol: chain.append(v)
                elif dist(chain[-1], v) <= tol: chain.append(u)
                elif dist(chain[0], v) <= tol: chain.insert(0, u)
                elif dist(chain[0], u) <= tol: chain.insert(0, v)
                else: continue
                loose.pop(i); changed = True; break
        closed = len(chain) > 2 and dist(chain[0], chain[-1]) <= tol
        chain = clean_points(chain, closed)
        if len(chain) >= (3 if closed else 2):
            contours.append(Contour(chain, closed, "joined geometry", layer=chain_layer,
                                    target_depth=depth_from_layer(chain_layer)))
    heal_open_contours(contours, gap_tol)
    classify_contours(contours)
    return contours


def classify_contours(contours: List[Contour]) -> None:
    closed = [c for c in contours if c.closed and len(c.points) >= 3]
    for c in closed:
        if c.forced_role in ("inner","outer"):
            c.depth=1 if c.forced_role=="inner" else 0;c.role=c.forced_role;continue
        probe = c.points[0]
        c.depth = sum(1 for other in closed if other is not c and abs(other.area) > abs(c.area) and point_in_poly(probe, other.points))
        c.role = "inner" if c.depth % 2 else "outer"


def heal_open_contours(contours: List[Contour], tolerance: float) -> int:
    """Join/close open contours by endpoints, restricted to the same DXF layer."""
    tolerance = max(float(tolerance), 0.0)
    if tolerance <= EPS:
        return 0
    repaired = 0
    changed = True
    while changed:
        changed = False
        opens = [c for c in contours if not c.closed and len(c.points) >= 2]
        for ai, a in enumerate(opens):
            for b in opens[ai + 1:]:
                if a.layer != b.layer:
                    continue
                options = [
                    (dist(a.points[-1], b.points[0]), False, False),
                    (dist(a.points[-1], b.points[-1]), False, True),
                    (dist(a.points[0], b.points[0]), True, False),
                    (dist(a.points[0], b.points[-1]), True, True),
                ]
                gap, reverse_a, reverse_b = min(options, key=lambda x: x[0])
                if gap > tolerance:
                    continue
                pa = list(reversed(a.points)) if reverse_a else list(a.points)
                pb = list(reversed(b.points)) if reverse_b else list(b.points)
                bridge = (pa[-1], pb[0])
                a.points = clean_points(pa + pb, False)
                a.bridges = list(a.bridges) + list(b.bridges)
                if gap > EPS: a.bridges.append(bridge)
                contours.remove(b)
                repaired += 1; changed = True
                break
            if changed:
                break
    for c in contours:
        if not c.closed and len(c.points) >= 3 and dist(c.points[0], c.points[-1]) <= tolerance:
            if dist(c.points[0], c.points[-1]) > EPS:
                c.bridges.append((c.points[-1], c.points[0]))
            c.points = clean_points(c.points, True)
            c.closed = True
            repaired += 1
    classify_contours(contours)
    return repaired


def auto_tabs(contour: Contour, count: int, flat: float, ramp: float) -> List[float]:
    if count <= 0 or not contour.closed:
        return []
    pts, candidates, run = contour.points, [], 0.0
    for i in range(len(pts)):
        ln = dist(pts[i], pts[(i + 1) % len(pts)])
        if ln >= flat + 2 * ramp + 0.5:
            candidates.append((ln, run + ln / 2))
        run += ln
    total = contour.length
    if not candidates:
        return [total * (i + .5) / count for i in range(count)]
    selected: List[float] = []
    # Long straight segments first, while encouraging even spacing.
    for _ in range(count):
        best = max(candidates, key=lambda x: x[0] if not selected else
                   x[0] * min(min(abs(x[1] - s), total - abs(x[1] - s)) for s in selected))
        selected.append(best[1])
        candidates.remove(best)
        if not candidates:
            break
    while len(selected) < count:
        target = total * len(selected) / count
        selected.append(target)
    return sorted(selected)


def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def z_for_distance(s: float, total: float, tabs: Sequence[float], cut_z: float,
                   tab_z: float, flat: float, ramp: float) -> float:
    z = cut_z
    for center in tabs:
        delta = abs(s - center)
        if total > 0:
            delta = min(delta, total - delta)
        half = flat / 2.0
        if delta <= half:
            z = max(z, tab_z)
        elif ramp > EPS and delta <= half + ramp:
            f = (half + ramp - delta) / ramp
            z = max(z, cut_z + (tab_z - cut_z) * f)
    return z


def toolpath_with_events(pts: Sequence[Point], tabs: Sequence[float], flat: float,
                         ramp: float) -> List[Tuple[Point, float]]:
    """Split path at every tab boundary; returned tuples are point, distance."""
    total = path_length(pts, True)
    events = {0.0, total}
    for c in tabs:
        for off in (-flat/2-ramp, -flat/2, flat/2, flat/2+ramp):
            events.add((c + off) % total)
    # Include original vertices.
    run = 0.0
    for i in range(len(pts)):
        events.add(run)
        run += dist(pts[i], pts[(i + 1) % len(pts)])
    values = sorted(events)
    # ``total`` already maps back to the first point and closes the loop.  Do
    # not append it twice; duplicate terminal G1 moves distort timing and can
    # confuse downstream simulators.
    return [(point_at(pts, s, True)[0], s) for s in values]


def wall_finish_for(c:Contour,target:float,stock:float,cfg:dict)->bool:
    if not (cfg.get("wall_finish") and c.closed):return False
    scope=cfg.get("finish_scope","전체")
    if c.role=="inner":return scope in ("전체","내부홀만","All","Inner only")
    return target>=stock-EPS and scope in ("전체","외곽만","All","Outer only")


def onion_skin_for(c:Contour,target:float,stock:float,cfg:dict)->bool:
    # Onion skin only supports the outer profile.  Inner holes have no loose
    # workpiece to retain and are cut directly to their requested depth.
    return bool(cfg.get("onion_skin_enabled") and c.closed and c.role=="outer" and target>=stock-EPS)


def staged_finish_for(c:Contour,target:float,stock:float,cfg:dict)->bool:
    return wall_finish_for(c,target,stock,cfg) or onion_skin_for(c,target,stock,cfg)


def finish_allowance_for(c:Contour,route:Sequence[Point],cfg:dict)->float:
    allowance=max(0.0,float(cfg.get("finish_allowance",0.0)))
    if c.role!="inner" or not route:return allowance
    width=max(p[0] for p in route)-min(p[0] for p in route)
    height=max(p[1] for p in route)-min(p[1] for p in route)
    # Keep a valid roughing loop even when the compensated hole is very small.
    return min(allowance,max(0.0,min(width,height)*.35))


def rough_route_for(c:Contour,route:Sequence[Point],cfg:dict)->Tuple[List[Point],float]:
    allowance=finish_allowance_for(c,route,cfg)
    direction=-1.0 if c.role=="inner" else 1.0
    return offset_polygon(route,direction*allowance),allowance


def rough_target_for(target:float,stock:float,cfg:dict,use_onion_skin:bool)->float:
    return max(.01,stock-float(cfg.get("onion_skin",0.0))) if use_onion_skin else target


def _gcode_route_worker(task)->Tuple[int,float,List[Point],int]:
    """CPU-heavy compensation stage; safe to run outside the Tk process."""
    ci,c,cfg,stock,extra=task
    target=min(max(c.target_depth if c.target_depth is not None else stock+extra,.01),stock+extra)
    pts=list(c.points);removed_count=0
    if c.closed:
        want_ccw=(c.role=="inner") if cfg["climb"] else (c.role!="inner")
        pts=reverse_if_needed(pts,want_ccw)
        pts,removed_loops,_=compensated_route(c,cfg["tool_d"],cfg.get("auto_trim",False),pts)
        removed_count=len(removed_loops)
    return ci,target,pts,removed_count


def prepare_gcode_routes(ordered:Sequence[Contour],cfg:dict,stock:float,extra:float,
                         progress:Optional[Callable[[float,str],None]]=None
                         )->List[Tuple[int,float,List[Point],int]]:
    tasks=[(ci,c,cfg,stock,extra) for ci,c in enumerate(ordered,1)]
    workers=_route_parallel_workers(ordered,bool(cfg.get("auto_trim",False)));results=[]
    if workers>1:
        try:
            context=mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
                futures=[pool.submit(_gcode_route_worker,task) for task in tasks]
                for done,future in enumerate(as_completed(futures),1):
                    results.append(future.result())
                    if progress:progress(done/max(len(tasks),1)*100.0,
                                         f"공구 보정경로 준비 {done}/{len(tasks)} · {workers}코어")
        except Exception:
            results=[]
            if progress:progress(0,"멀티코어 경로 준비 실패 · 1코어로 재시도")
    if not results:
        for index,task in enumerate(tasks,1):
            results.append(_gcode_route_worker(task))
            if progress:progress(index/max(len(tasks),1)*100.0,
                                 f"공구 보정경로 준비 {index}/{len(tasks)} · 1코어")
    return sorted(results,key=lambda item:item[0])


def work_origin_for_contours(contours:Sequence[Contour],cfg:dict)->Point:
    active=[c for c in contours if c.enabled]
    all_pts=[p for c in active for p in c.points]
    if all_pts:
        minx,maxx=min(p[0] for p in all_pts),max(p[0] for p in all_pts)
        miny,maxy=min(p[1] for p in all_pts),max(p[1] for p in all_pts)
    else:minx=maxx=miny=maxy=0.0
    mode=cfg.get("xy_origin","DXF 원점")
    if mode in ("Lower-left","좌하단"):return minx,miny
    if mode in ("Upper-left","좌상단"):return minx,maxy
    if mode in ("Upper-right","우상단"):return maxx,maxy
    if mode in ("Lower-right","우하단"):return maxx,miny
    if mode in ("Center","중앙"):return (minx+maxx)/2,(miny+maxy)/2
    return 0.0,0.0


def split_outer_inner_conflicts(part1:Sequence[Contour],part2:Sequence[Contour])->int:
    """Count unsafe cases where PART1 releases an outer before its PART2 inner cut."""
    outers=[c for c in part1 if c.enabled and c.closed and c.role=="outer" and len(c.points)>=3]
    inners=[c for c in part2 if c.enabled and c.closed and c.role=="inner" and c.points]
    return sum(1 for outer in outers for inner in inners
               if point_in_poly(inner.points[0],outer.points))


def split_gcode_paths(filename:str)->Tuple[str,str]:
    root,ext=os.path.splitext(filename);ext=ext or ".nc"
    root=re.sub(r"_(?:PART1|PART2)$","",root,flags=re.IGNORECASE)
    return f"{root}_PART1{ext}",f"{root}_PART2{ext}"


def filename_component(value:str,fallback:str="job")->str:
    text=re.sub(r'[<>:"/\\|?*]+',"-",str(value or "").strip())
    text=re.sub(r"\s+","_",text).strip(" ._")
    return text or fallback


def endmill_name(tool_d:float)->str:
    text=f"{float(tool_d):.4f}".rstrip("0").rstrip(".")
    if "." not in text:text+=".0"
    return f"{text}endmill"


def stock_thickness_name(stock:float)->str:
    text=f"{float(stock):.4f}".rstrip("0").rstrip(".")
    if "." not in text:text+=".0"
    return f"T{text}"


def loaded_source_name(part_objects:Sequence[PartObject],filename:str)->str:
    unique:Dict[str,str]={}
    for part in part_objects:
        if not part.source_path:continue
        key=os.path.normcase(os.path.abspath(part.source_path))
        unique.setdefault(key,os.path.splitext(os.path.basename(part.source_path))[0])
    if len(unique)>1:return "multi"
    if len(unique)==1:return filename_component(next(iter(unique.values())))
    stem=os.path.splitext(os.path.basename(filename or "job"))[0]
    if stem.lower() in ("multi","multi_job"):return "multi"
    return filename_component(stem)


def placed_object_count(contours:Sequence[Contour])->int:
    groups=set()
    for contour in contours:
        if not contour.enabled:continue
        groups.add((contour.object_id if contour.object_id else -1,
                    contour.instance_id if contour.object_id and contour.instance_id else 1))
    return len(groups)


def default_gcode_filename(part_objects:Sequence[PartObject],filename:str,contours:Sequence[Contour],
                           tool_d:float,stock:float,minutes:float,when:Optional[datetime]=None)->str:
    date_text=(when or datetime.now()).strftime("%y%m%d")
    source=loaded_source_name(part_objects,filename)
    quantity=max(1,placed_object_count(contours))
    rounded_minutes=max(1,int(math.floor(max(0.0,float(minutes))+0.5)))
    return f"{date_text}_{endmill_name(tool_d)}_{stock_thickness_name(stock)}_{source}_{quantity}_{rounded_minutes}min.nc"


def version_numbers(value:str)->Tuple[int,...]:
    numbers=tuple(int(part) for part in re.findall(r"\d+",str(value)))
    return numbers or (0,)


def newer_version(candidate:str,current:str)->bool:
    left=list(version_numbers(candidate));right=list(version_numbers(current))
    size=max(len(left),len(right));left.extend([0]*(size-len(left)));right.extend([0]*(size-len(right)))
    return tuple(left)>tuple(right)


def validated_update_manifest(data:dict,current_version:str=APP_VERSION)->Optional[dict]:
    if not isinstance(data,dict):raise ValueError("업데이트 정보 형식이 올바르지 않습니다.")
    version=str(data.get("version","")).strip()
    download_url=str(data.get("download_url","")).strip()
    sha256=str(data.get("sha256","")).strip().lower()
    message=str(data.get("message","")).strip()
    if not version or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*",version):
        raise ValueError("업데이트 버전 번호가 올바르지 않습니다.")
    if not download_url.startswith(UPDATE_DOWNLOAD_PREFIX):
        raise ValueError("허용되지 않은 업데이트 다운로드 주소입니다.")
    if not re.fullmatch(r"[0-9a-f]{64}",sha256):
        raise ValueError("업데이트 파일 검증값이 올바르지 않습니다.")
    if not newer_version(version,current_version):return None
    return {"version":version,"download_url":download_url,"sha256":sha256,"message":message}


def file_sha256(path:str)->str:
    digest=hashlib.sha256()
    with open(path,"rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def fetch_update_manifest(timeout:float=5.0)->Optional[dict]:
    request=urllib.request.Request(
        UPDATE_MANIFEST_URL,headers={"User-Agent":f"CFRP-Router-CAM/{APP_VERSION}","Cache-Control":"no-cache"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        if int(getattr(response,"status",200))!=200:raise OSError("업데이트 서버 응답 오류")
        data=json.loads(response.read(65537).decode("utf-8"))
    return validated_update_manifest(data)


def download_verified_update(url:str,destination:str,expected_sha256:str,timeout:float=120.0):
    if not url.startswith(UPDATE_DOWNLOAD_PREFIX):raise ValueError("허용되지 않은 업데이트 다운로드 주소입니다.")
    expected=str(expected_sha256).lower()
    if not re.fullmatch(r"[0-9a-f]{64}",expected):raise ValueError("업데이트 검증값이 올바르지 않습니다.")
    partial=destination+".part"
    try:
        request=urllib.request.Request(url,headers={"User-Agent":f"CFRP-Router-CAM/{APP_VERSION}"})
        with urllib.request.urlopen(request,timeout=timeout) as response,open(partial,"wb") as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                output.write(chunk)
            output.flush();os.fsync(output.fileno())
        if file_sha256(partial)!=expected:raise ValueError("다운로드한 업데이트 파일의 SHA-256이 일치하지 않습니다.")
        os.replace(partial,destination)
    except Exception:
        try:
            if os.path.isfile(partial):os.remove(partial)
        except OSError:pass
        raise


def wait_for_windows_process(pid:int,timeout_ms:int=30000)->bool:
    if os.name!="nt":return True
    from ctypes import wintypes
    kernel32=ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel32.OpenProcess.restype=wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel32.WaitForSingleObject.restype=wintypes.DWORD
    kernel32.CloseHandle.argtypes=(wintypes.HANDLE,)
    kernel32.CloseHandle.restype=wintypes.BOOL
    handle=kernel32.OpenProcess(0x00100000,False,int(pid))
    if not handle:return True
    try:return kernel32.WaitForSingleObject(handle,int(timeout_ms))==0
    finally:kernel32.CloseHandle(handle)


def replace_executable_files(source_exe:str,target_exe:str,expected_sha256:str):
    source=os.path.abspath(source_exe);target=os.path.abspath(target_exe)
    if os.path.normcase(os.path.dirname(source))!=os.path.normcase(os.path.dirname(target)):
        raise ValueError("업데이트 파일 위치가 올바르지 않습니다.")
    if os.path.basename(source)!=UPDATE_TEMP_FILENAME or not target.lower().endswith(".exe"):
        raise ValueError("업데이트 대상 파일명이 올바르지 않습니다.")
    if not os.path.isfile(source) or not os.path.isfile(target):raise FileNotFoundError("업데이트 파일을 찾지 못했습니다.")
    if file_sha256(source)!=str(expected_sha256).lower():raise ValueError("업데이트 실행 파일 검증에 실패했습니다.")
    backup=target+".update-backup"
    if os.path.isfile(backup):os.remove(backup)
    os.replace(target,backup)
    try:
        shutil.copy2(source,target)
        if file_sha256(target)!=str(expected_sha256).lower():raise ValueError("교체된 실행 파일 검증에 실패했습니다.")
    except Exception:
        try:
            if os.path.isfile(target):os.remove(target)
            os.replace(backup,target)
        except OSError:pass
        raise
    try:os.remove(backup)
    except OSError:pass


def apply_update_process(source_exe:str,target_exe:str,old_pid:int,expected_sha256:str)->int:
    try:
        if not wait_for_windows_process(old_pid):raise TimeoutError("기존 프로그램이 종료되지 않았습니다.")
        replace_executable_files(source_exe,target_exe,expected_sha256)
        subprocess.Popen([target_exe,"--cleanup-update",source_exe],cwd=os.path.dirname(target_exe),close_fds=True)
        return 0
    except Exception as exc:
        try:
            with open(os.path.join(os.path.dirname(source_exe),"update_error.txt"),"w",encoding="utf-8") as f:f.write(str(exc))
        except OSError:pass
        try:
            if os.path.isfile(target_exe):subprocess.Popen([target_exe],cwd=os.path.dirname(target_exe),close_fds=True)
        except OSError:pass
        return 1


def cleanup_update_file(path:str,timeout:float=8.0):
    candidate=os.path.abspath(path);current=os.path.abspath(sys.executable)
    if (os.path.normcase(os.path.dirname(candidate))!=os.path.normcase(os.path.dirname(current)) or
            os.path.basename(candidate)!=UPDATE_TEMP_FILENAME):return
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            if os.path.isfile(candidate):os.remove(candidate)
            return
        except OSError:time.sleep(.2)


_NC_ENUMS = {
    "좌하단":"LOWER_LEFT", "좌상단":"UPPER_LEFT", "우상단":"UPPER_RIGHT", "우하단":"LOWER_RIGHT",
    "중앙":"CENTER", "DXF 원점":"DXF_ORIGIN", "선택점":"SELECTED_POINT",
    "Lower-left":"LOWER_LEFT", "Upper-left":"UPPER_LEFT", "Upper-right":"UPPER_RIGHT",
    "Lower-right":"LOWER_RIGHT", "Center":"CENTER", "Selected point":"SELECTED_POINT",
    "전체":"ALL", "외곽만":"OUTER_ONLY", "내부홀만":"INNER_ONLY",
    "All":"ALL", "Outer only":"OUTER_ONLY", "Inner only":"INNER_ONLY",
}


def nc_ascii_text(value) -> str:
    """Return controller-safe ASCII and remove any Korean/user Unicode text."""
    text=_NC_ENUMS.get(str(value),str(value))
    text=text.replace("(","[").replace(")","]")
    return text.encode("ascii","ignore").decode("ascii").strip()


def nc_ascii_line(value) -> str:
    return str(value).encode("ascii","ignore").decode("ascii")


def nc_yes_no(value) -> str:
    return "YES" if bool(value) else "NO"


def gcode_settings_header(cfg:dict,active:Sequence[Contour],origin:Point,
                          safe_machine_z:float,actual_passes:int) -> List[str]:
    stock=float(cfg["stock"]);extra=float(cfg["extra"])
    bottom_zero=cfg.get("z_origin")=="Bottom"
    final_through_z=-extra if bottom_zero else -(stock+extra)
    custom_depths=sorted({round(float(c.target_depth),6) for c in active if c.target_depth is not None})
    custom_text=",".join(fmt(value) for value in custom_depths) if custom_depths else "NONE"
    closed_count=sum(bool(c.closed) for c in active)
    safety_excluded=sum(bool(c.safety_excluded) for c in active)
    return [
        "(----- CAM SETTINGS BEGIN -----)",
        f"(UNITS: MM)",
        f"(ACTIVE_CONTOURS: {len(active)} CLOSED: {closed_count} OPEN: {len(active)-closed_count})",
        f"(SAFETY_CHECK_EXCLUDED: {safety_excluded})",
        f"(TOOL_DIAMETER_MM: {fmt(float(cfg['tool_d']))})",
        f"(SPINDLE_RPM: {int(round(float(cfg['rpm'])))})",
        f"(FEED_XY_MM_MIN: {fmt(float(cfg['feed']))})",
        f"(PLUNGE_MM_MIN: {fmt(float(cfg['plunge']))})",
        f"(STOCK_THICKNESS_MM: {fmt(stock)})",
        f"(THROUGH_ALLOWANCE_MM: {fmt(extra)})",
        f"(DEFAULT_THROUGH_DEPTH_BELOW_TOP_MM: {fmt(stock+extra)})",
        f"(DEFAULT_FINAL_Z: {fmt(final_through_z)})",
        f"(CUSTOM_DEPTHS_BELOW_TOP_MM: {custom_text})",
        f"(Z_ORIGIN: {nc_ascii_text(cfg.get('z_origin','Top')).upper()})",
        f"(XY_ORIGIN_MODE: {nc_ascii_text(cfg.get('xy_origin','DXF origin')).upper()})",
        f"(XY_ORIGIN_SOURCE_X_MM: {fmt(float(origin[0]))})",
        f"(XY_ORIGIN_SOURCE_Y_MM: {fmt(float(origin[1]))})",
        f"(SAFE_Z_CLEARANCE_MM: {fmt(float(cfg['safe_z']))})",
        f"(SAFE_Z_PROGRAMMED: {fmt(float(safe_machine_z))})",
        f"(LEAD_IN_OUT_MM: {fmt(float(cfg['lead']))})",
        f"(FULL_DEPTH_ONE_PASS: {nc_yes_no(cfg.get('full_depth'))})",
        f"(PROGRAMMED_PASS_COUNT: {int(actual_passes)})",
        f"(CUT_DIRECTION: {'CLIMB' if cfg.get('climb') else 'CONVENTIONAL'})",
        f"(RAPID_OPTIMIZE: {nc_yes_no(cfg.get('rapid_optimize',True))})",
        f"(COOLANT_AIR_M8: {nc_yes_no(cfg.get('m8_enabled'))})",
        f"(TAB_COUNT_PER_OUTER: {int(cfg.get('tab_count',0))})",
        f"(TAB_LENGTH_MM: {fmt(float(cfg.get('tab_flat',0.0)))})",
        f"(TAB_REMAINING_MM: {fmt(float(cfg.get('tab_remain',0.0)))})",
        f"(TAB_RAMP_MM: {fmt(float(cfg.get('tab_ramp',0.0)))})",
        f"(TAB_SHAPE: {nc_ascii_text(cfg.get('tab_shape','Flat+ramp')).upper()})",
        f"(WALL_FINISH: {nc_yes_no(cfg.get('wall_finish'))})",
        f"(ONION_SKIN: {nc_yes_no(cfg.get('onion_skin_enabled'))})",
        f"(FINISH_SCOPE: {nc_ascii_text(cfg.get('finish_scope','All')).upper()})",
        f"(ONION_SKIN_REMAINING_MM: {fmt(float(cfg.get('onion_skin',0.0)))})",
        f"(ROUGH_WALL_ALLOWANCE_MM: {fmt(float(cfg.get('finish_allowance',0.0)))})",
        f"(FINISH_FEED_PERCENT: {fmt(float(cfg.get('finish_feed_pct',100.0)))})",
        f"(AUTO_TRIM_SMALL_LOOPS: {nc_yes_no(cfg.get('auto_trim'))})",
        f"(LINE_REPAIR_TOLERANCE_MM: {fmt(float(cfg.get('gap_tol',0.0)))})",
        f"(MACHINE_HOME_G53_PARK: {nc_yes_no(cfg.get('machine_home_enabled'))})",
        f"(G53_PARK_X: {fmt(float(cfg.get('machine_park_x',10.0)))})",
        f"(G53_PARK_Y: {fmt(float(cfg.get('machine_park_y',10.0)))})",
        f"(G53_PARK_Z: {fmt(float(cfg.get('machine_park_z',-2.0)))})",
        f"(SHEET_X_MM: {fmt(float(cfg.get('sheet_w',0.0)))})",
        f"(SHEET_Y_MM: {fmt(float(cfg.get('sheet_h',0.0)))})",
        f"(ARRAY_GAP_MM: {fmt(float(cfg.get('array_gap',0.0)))})",
        f"(ARRAY_EDGE_MM: {fmt(float(cfg.get('array_edge',0.0)))})",
        f"(ARRAY_REQUESTED_QTY: {int(cfg.get('array_qty',0))})",
        f"(ARRAY_ALLOW_90_DEG: {nc_yes_no(cfg.get('array_rotate'))})",
        f"(ARRAY_AUTO_ROTATE: {nc_yes_no(cfg.get('array_auto_rotate'))})",
        f"(ACCUMULATED_BEFORE_JOB_M: {fmt(float(cfg.get('accum_distance_m',0.0)))})",
        f"(ACCUMULATED_BEFORE_JOB_MIN: {fmt(float(cfg.get('accum_time_min',0.0)))})",
        "(----- CAM SETTINGS END -----)",
    ]


def generate_gcode(contours: List[Contour], cfg: dict,
                   progress:Optional[Callable[[float,str],None]]=None) -> str:
    def report(value:float,message:str):
        if progress:progress(value,message)
    report(2,"G-code 설정 준비 중")
    safe_z, stock, extra = cfg["safe_z"], cfg["stock"], cfg["extra"]
    bottom_zero = cfg.get("z_origin") == "Bottom"
    safe_machine_z = stock + safe_z if bottom_zero else safe_z
    def machine_z(depth_below_top: float) -> float:
        return stock - depth_below_top if bottom_zero else -depth_below_top
    passes = 1 if cfg["full_depth"] else max(1, cfg["passes"])
    active = [c for c in contours if c.enabled]
    origin_mode = cfg.get("xy_origin", "DXF 원점")
    override=cfg.get("_xy_origin_override")
    origin_x,origin_y=(float(override[0]),float(override[1])) if override is not None else work_origin_for_contours(active,cfg)
    rapid_optimize=bool(cfg.get("rapid_optimize",True))
    ordered=ordered_contours(active,rapid_optimize,(origin_x,origin_y))
    macros = {"{RPM}": str(int(cfg["rpm"])), "{SAFE_Z}": fmt(safe_machine_z),
              "{FEED}": fmt(cfg["feed"]), "{PLUNGE}": fmt(cfg["plunge"])}
    def expand(code: str) -> List[str]:
        for key, value in macros.items():code = code.replace(key, value)
        return [x.strip() for x in code.splitlines() if x.strip()]
    start_lines=expand(cfg.get("start_code", "")) or expand(DEFAULT_START_CODE)
    end_lines=expand(cfg.get("end_code", "")) or expand(DEFAULT_END_CODE)
    def has_mcode(lines:Sequence[str],number:int)->bool:
        for line in lines:
            executable=re.sub(r"\([^)]*\)","",line).split(";",1)[0]
            if re.search(rf"M0*{number}(?!\d)",executable,re.IGNORECASE):return True
        return False
    if cfg.get("m8_enabled") and not has_mcode(start_lines,8):start_lines.append("M8")
    if cfg.get("m8_enabled") and not has_mcode(end_lines,9):
        stop_index=next((i for i,line in enumerate(end_lines)
                         if line.strip()=="%" or has_mcode((line,),30) or has_mcode((line,),2)),len(end_lines))
        end_lines.insert(stop_index,"M9")
    if cfg.get("machine_home_enabled"):
        has_g53=any(re.search(r"(?:^|\s)G0*53(?:\s|$)",
                             re.sub(r"\([^)]*\)","",line).split(";",1)[0],re.IGNORECASE)
                    for line in end_lines)
        if not has_g53:
            stop_index=next((i for i,line in enumerate(end_lines)
                             if line.strip()=="%" or has_mcode((line,),30) or has_mcode((line,),2)),len(end_lines))
            park=("G90",
                  f"G53 G0 Z{fmt(float(cfg.get('machine_park_z',-2.0)))}",
                  f"G53 G0 X{fmt(float(cfg.get('machine_park_x',10.0)))} Y{fmt(float(cfg.get('machine_park_y',10.0)))}")
            end_lines[stop_index:stop_index]=park
    program_header=[]
    while start_lines and (start_lines[0].strip()=="%" or re.fullmatch(r"O\d+",start_lines[0].strip(),re.IGNORECASE)):
        program_header.append(start_lines.pop(0))
    report(10,"가공 거리·시간 계산 중")
    metres, minutes, total_metres, total_minutes = machining_report(
        contours,cfg,lambda value,message:report(10+value*.08,message))
    job_label=nc_ascii_text(cfg.get("_job_label",""))
    job_note=nc_ascii_text(cfg.get("_job_note",""))
    job_header=([f"(Job part: {job_label})"] if job_label else [])+([f"({job_note})"] if job_note else [])
    settings_header=gcode_settings_header(cfg,active,(origin_x,origin_y),safe_machine_z,passes)
    out = program_header+[f"(CFRP Router CAM V{APP_VERSION} - Mach3 post)", f"(XY origin mode: {nc_ascii_text(origin_mode)})"]+job_header+settings_header+[
           f"(This job cutting distance: {fmt(metres)} m)",
           f"(This job estimated cutting time: {fmt(minutes)} min)",
           f"(Accumulated after job: {fmt(total_metres)} m, {fmt(total_minutes)} min)"]+start_lines

    current_xy:Point=(origin_x,origin_y)
    def emit_phase(c:Contour,route:List[Point],depths:Sequence[float],tab_distances:Sequence[float],
                   feed:float,label:str,sink:Optional[List[str]]=None)->str:
        nonlocal current_xy
        dst=out if sink is None else sink
        plan=lead_plan(c,route,cfg["lead"]) if c.closed else LeadPlan(route[0],"none")
        shifted=[(p[0]-origin_x,p[1]-origin_y) for p in route]
        lead=(plan.entry[0]-origin_x,plan.entry[1]-origin_y)
        center=None if plan.center is None else (plan.center[0]-origin_x,plan.center[1]-origin_y)
        p0=shifted[0];dst.append(f"(Phase: {label}, feed={fmt(feed)})")
        if plan.mode=="center-fallback":dst.append("(Lead-in auto: insufficient space -> safe interior center)")
        dst.append(f"G0 X{fmt(lead[0])} Y{fmt(lead[1])}")
        for pi,depth in enumerate(depths,1):
            active_tabs=list(tab_distances) if pi==len(depths) else []
            tab_flat=0.0 if cfg.get("tab_shape")=="Triangle" else cfg["tab_flat"]
            total=path_length(shifted,True) if c.closed else 0.0
            # A user-selected/optimized route can start inside a tab.  Plunging
            # directly to full depth there would drill through the material the
            # tab is supposed to retain, so begin at the tab profile's Z.
            start_z=(z_for_distance(0.0,total,active_tabs,depth,
                                     machine_z(stock-cfg["tab_remain"]),tab_flat,cfg["tab_ramp"])
                     if c.closed else depth)
            dst.append(f"G1 Z{fmt(start_z)} F{fmt(cfg['plunge'])}")
            if center is not None:
                code="G2" if plan.clockwise else "G3"
                dst.append(f"{code} X{fmt(p0[0])} Y{fmt(p0[1])} I{fmt(center[0]-lead[0])} J{fmt(center[1]-lead[1])} F{fmt(feed)}")
            elif lead!=p0:dst.append(f"G1 X{fmt(p0[0])} Y{fmt(p0[1])} F{fmt(feed)}")
            if c.closed:
                events=toolpath_with_events(shifted,active_tabs,tab_flat,cfg["tab_ramp"])
                for p,s in events[1:]:
                    z=z_for_distance(s%total if total else 0,total,active_tabs,depth,
                                     machine_z(stock-cfg["tab_remain"]),tab_flat,cfg["tab_ramp"])
                    dst.append(f"G1 X{fmt(p[0])} Y{fmt(p[1])} Z{fmt(z)} F{fmt(feed)}")
            else:
                for p in shifted[1:]:dst.append(f"G1 X{fmt(p[0])} Y{fmt(p[1])} F{fmt(feed)}")
            if pi!=len(depths):dst.extend((f"G0 Z{fmt(safe_machine_z)}",f"G0 X{fmt(lead[0])} Y{fmt(lead[1])}"))
        if c.closed and cfg["lead"]>0:
            if center is not None:
                code="G3" if plan.clockwise else "G2"
                dst.append(f"{code} X{fmt(lead[0])} Y{fmt(lead[1])} I{fmt(center[0]-p0[0])} J{fmt(center[1]-p0[1])} F{fmt(feed)}")
            else:dst.append(f"G1 X{fmt(lead[0])} Y{fmt(lead[1])} F{fmt(feed)}")
        dst.append(f"G0 Z{fmt(safe_machine_z)}")
        current_xy=plan.entry if c.closed else route[-1]
        return plan.mode

    def resolved_tab_source(c:Contour)->List[float]:
        """Return stored/automatic tabs unless the user explicitly chose zero."""
        if not c.tabs_enabled or c.tabs_cleared:return []
        return list(c.tabs) if c.tabs else auto_tabs(c,cfg["tab_count"],cfg["tab_flat"],cfg["tab_ramp"])

    finish_feed=cfg["feed"]*cfg["finish_feed_pct"]/100.0
    def emit_finish_task(task,progress_value:Optional[float]=None,progress_message:str=""):
        ci,c,pts,target,tabs,order_note,object_note,trimmed,actual_allowance,wall_finish,use_onion=task
        if progress_value is not None:report(progress_value,progress_message)
        out.append(f"(Finish contour {ci}: {c.role}, order={order_note}, layer={nc_ascii_text(c.layer)}, depth={fmt(target)}, allowance={fmt(actual_allowance)}, tabs={len(tabs)}, trimmed={trimmed}{nc_ascii_text(object_note)})")
        if rapid_optimize and c.start_s<=EPS:
            pts=rotate_closed_path(pts,nearest_path_distance(pts,current_xy,True)[1])
            if c.role=="outer":
                source_tabs=resolved_tab_source(c)
                tabs=[nearest_path_distance(pts,point_at(c.points,s,True)[0],True)[1] for s in source_tabs]
        if wall_finish:label="microtab outer finish" if c.role=="outer" else "inner wall finish"
        else:label="onion-skin cleanup"
        emit_phase(c,pts,[machine_z(target)],tabs,finish_feed,label+" - nominal wall/full depth")

    prepared_routes=prepare_gcode_routes(
        ordered,cfg,stock,extra,lambda value,message:report(18+value*.20,message))
    finish_tasks=[]
    if any(staged_finish_for(c,min(max(c.target_depth if c.target_depth is not None else stock+extra,.01),stock+extra),stock,cfg) for c in ordered):
        out.append("(Stage 1: complete internal features before outer-profile cutting)")
    for (ci,target,pts,removed_count),c in zip(prepared_routes,ordered):
        report(38+42*ci/max(len(ordered),1),f"G-code 조립 {ci}/{len(ordered)}")
        if c.closed:
            if c.start_s>EPS:
                start_point=point_at(c.points,c.start_s,True)[0]
                pts=rotate_closed_path(pts,nearest_path_distance(pts,start_point,True)[1])
            elif rapid_optimize:
                pts=rotate_closed_path(pts,nearest_path_distance(pts,current_xy,True)[1])
        elif rapid_optimize and len(pts)>=2 and dist(current_xy,pts[-1])<dist(current_xy,pts[0]):
            pts.reverse()
        tabs=[];source_tabs=[]
        if c.closed and c.role=="outer" and c.tabs_enabled and target>=stock-EPS:
            source_tabs=resolved_tab_source(c)
            tabs=[nearest_path_distance(pts,point_at(c.points,s,True)[0],True)[1] for s in source_tabs]
        wall_finish=wall_finish_for(c,target,stock,cfg);use_onion=onion_skin_for(c,target,stock,cfg)
        finish=wall_finish or use_onion
        order_note=str(c.cut_order) if c.cut_order is not None else "auto"
        object_note=f", object={nc_ascii_text(c.object_name)}, instance={c.instance_id}" if c.object_name else ""
        out.append(f"(Contour {ci}: {c.role}, order={order_note}, layer={nc_ascii_text(c.layer)}, depth={fmt(target)}, tabs={len(tabs)}, safety_check={'excluded' if c.safety_excluded else 'enabled'}, wall_finish={'yes' if wall_finish else 'no'}, onion_skin={'yes' if use_onion else 'no'}, trimmed={removed_count}{object_note})")
        if finish:
            rough,actual_allowance=rough_route_for(c,pts,cfg) if wall_finish else (list(pts),0.0)
            if cfg.get("auto_trim") and self_intersection_count(rough):rough,_,_=trim_small_self_loops(rough)
            rough_target=rough_target_for(target,stock,cfg,use_onion)
            rough_depths=[machine_z(rough_target*i/passes) for i in range(1,passes+1)]
            rough_tabs=[]
            if c.role=="outer" and tabs and not use_onion:
                rough_tabs=[nearest_path_distance(rough,point_at(c.points,s,True)[0],True)[1] for s in source_tabs]
            emit_phase(c,rough,rough_depths,rough_tabs,cfg["feed"],
                       f"rough - axial remain {fmt(max(0.0,target-rough_target))} mm, radial remain {fmt(actual_allowance)} mm")
            finish_task=(ci,c,pts,target,tabs,order_note,object_note,removed_count,actual_allowance,wall_finish,use_onion)
            # Completing each internal wall now preserves the safe holes-first
            # order.  Only outer finishing/onion cleanup is deferred.
            if c.role=="inner":emit_finish_task(finish_task)
            else:finish_tasks.append(finish_task)
        else:
            depths=[machine_z(target*i/passes) for i in range(1,passes+1)]
            emit_phase(c,pts,depths,tabs,cfg["feed"],"standard cut")
    if finish_tasks:
        out.append("(Stage 2: outer wall finishing and/or onion-skin cleanup; microtabs retained)")
        for finish_index,task in enumerate(finish_tasks,1):
            emit_finish_task(task,82+15*finish_index/max(len(finish_tasks),1),
                             f"외곽 정삭 생성 {finish_index}/{len(finish_tasks)}")
    out += end_lines+[""]
    report(100,"G-code 생성 완료")
    return "\n".join(nc_ascii_line(line) for line in out)


def machining_report(contours: List[Contour], cfg: dict,
                     progress:Optional[Callable[[float,str],None]]=None
                     ) -> Tuple[float, float, float, float]:
    """Return job metres/minutes and accumulated metres/minutes after this job."""
    passes=1 if cfg["full_depth"] else max(1,cfg["passes"]);cut_mm=0.0;cut_min=0.0;plunge_min=0.0
    stock=cfg["stock"]
    active=[x for x in contours if x.enabled]
    for report_index,c in enumerate(active,1):
        if progress:progress(report_index/max(len(active),1)*100.0,
                             f"가공 거리 계산 {report_index}/{len(active)}")
        target=min(max(c.target_depth if c.target_depth is not None else stock+cfg["extra"],.01),stock+cfg["extra"])
        if c.closed and len(c.points)>=3:
            route,_,_=compensated_route(c,cfg["tool_d"],cfg.get("auto_trim",False));route_len=path_length(route,True)
            plan=lead_plan(c,route,cfg["lead"])
            lead_one=(math.pi*.5*dist(plan.entry,plan.center)) if plan.center is not None else dist(plan.entry,route[0])
        else:route=list(c.points);route_len=c.length;lead_one=0.0
        wall_finish=wall_finish_for(c,target,stock,cfg);use_onion=onion_skin_for(c,target,stock,cfg)
        if wall_finish or use_onion:
            rough,_=rough_route_for(c,route,cfg) if wall_finish else (list(route),0.0);rough_len=path_length(rough,True)
            rough_plan=lead_plan(c,rough,cfg["lead"])
            rough_lead=(math.pi*.5*dist(rough_plan.entry,rough_plan.center)) if rough_plan.center is not None else dist(rough_plan.entry,rough[0])
            rough_mm=rough_len*passes+rough_lead*(passes+1);finish_mm=route_len+lead_one*2
            cut_mm+=rough_mm+finish_mm
            cut_min+=rough_mm/max(cfg["feed"],EPS)+finish_mm/max(cfg["feed"]*cfg["finish_feed_pct"]/100.0,EPS)
            rough_target=rough_target_for(target,stock,cfg,use_onion)
            plunge_min+=sum(cfg["safe_z"]+rough_target*i/passes for i in range(1,passes+1))/max(cfg["plunge"],EPS)
            plunge_min+=(cfg["safe_z"]+target)/max(cfg["plunge"],EPS)
        else:
            phase_mm=route_len*passes+lead_one*(passes+1);cut_mm+=phase_mm
            cut_min+=phase_mm/max(cfg["feed"],EPS)
            plunge_min+=sum(cfg["safe_z"]+target*i/passes for i in range(1,passes+1))/max(cfg["plunge"],EPS)
    cut_min+=plunge_min;job_m=cut_mm/1000.0
    return (job_m,cut_min,cfg.get("accum_distance_m",0.0)+job_m,cfg.get("accum_time_min",0.0)+cut_min)


@dataclass
class Move3D:
    start: Tuple[float,float,float]
    end: Tuple[float,float,float]
    rapid: bool
    seconds: float


def parse_gcode_moves(code: str, rapid_feed: float = 3000.0) -> List[Move3D]:
    """Parse the GRBL subset emitted by this app into timed 3D moves."""
    pos=[0.0,0.0,0.0]; motion=0; feed=800.0; moves=[]
    for raw in code.splitlines():
        # Both parenthesized and semicolon-to-EOL comments are common in CNC
        # programs.  Coordinates mentioned in a comment must never become a
        # simulated machine move.
        line=re.sub(r";.*$","",raw)
        line=re.sub(r"\([^)]*\)","",line).strip().upper()
        if not line:continue
        words=re.findall(r"([A-Z])\s*(-?(?:\d+(?:\.\d*)?|\.\d+))",line)
        values={k:float(v) for k,v in words}
        if "G" in values and int(values["G"]) in (0,1,2,3):motion=int(values["G"])
        if "F" in values:feed=max(values["F"],EPS)
        if not any(k in values for k in ("X","Y","Z")):continue
        new=[values.get("X",pos[0]),values.get("Y",pos[1]),values.get("Z",pos[2])]
        if motion in (2,3) and ("I" in values or "J" in values):
            cx=pos[0]+values.get("I",0.0);cy=pos[1]+values.get("J",0.0)
            radius=math.hypot(pos[0]-cx,pos[1]-cy);a0=math.atan2(pos[1]-cy,pos[0]-cx);a1=math.atan2(new[1]-cy,new[0]-cx)
            sweep=a1-a0
            if motion==2:
                while sweep>=0:sweep-=2*math.pi
            else:
                while sweep<=0:sweep+=2*math.pi
            segments=max(6,int(math.ceil(abs(sweep)*max(radius,1.0)/.6)));prev=list(pos)
            for i in range(1,segments+1):
                f=i/segments;q=[cx+radius*math.cos(a0+sweep*f),cy+radius*math.sin(a0+sweep*f),pos[2]+(new[2]-pos[2])*f]
                length=math.sqrt(sum((q[j]-prev[j])**2 for j in range(3)))
                if length>EPS:moves.append(Move3D(tuple(prev),tuple(q),False,length/feed*60.0))
                prev=q
            pos=new;continue
        length=math.sqrt(sum((new[i]-pos[i])**2 for i in range(3)))
        if length>EPS:
            rate=rapid_feed if motion==0 else feed
            moves.append(Move3D(tuple(pos),tuple(new),motion==0,length/rate*60.0))
        pos=new
    return moves


def point_in_triangle_2d(p: Point, a: Point, b: Point, c: Point) -> bool:
    def side(q:Point,r:Point,s:Point)->float:return (q[0]-s[0])*(r[1]-s[1])-(r[0]-s[0])*(q[1]-s[1])
    d1,d2,d3=side(p,a,b),side(p,b,c),side(p,c,a)
    return not ((d1<0 or d2<0 or d3<0) and (d1>0 or d2>0 or d3>0))


class ProgressDialog(tk.Toplevel):
    """Delayed determinate progress window for synchronous CAD/CAM work."""
    def __init__(self,parent,title:str="연산 중"):
        super().__init__(parent)
        self.withdraw();self.title(title);self.resizable(False,False)
        self.protocol("WM_DELETE_WINDOW",lambda:None)
        self.value=tk.DoubleVar(value=0.0);self.percent=tk.StringVar(value="0%")
        self.message=DisplayStringVar(value="준비 중...");self._show_job=None;self._closed=False
        self._last_percent=-1;self._last_pump=0.0
        body=ttk.Frame(self,padding=18);body.pack(fill="both",expand=True)
        top=ttk.Frame(body);top.pack(fill="x")
        ttk.Label(top,textvariable=self.message).pack(side="left")
        ttk.Label(top,textvariable=self.percent,font=("Arial",11,"bold")).pack(side="right")
        ttk.Progressbar(body,mode="determinate",maximum=100,variable=self.value,length=360).pack(fill="x",pady=(10,2))
        self.transient(parent);self._show_job=self.after(140,self._show)

    def _show(self):
        self._show_job=None
        if self._closed or not self.winfo_exists():return
        self.update_idletasks()
        parent=self.master
        try:
            x=parent.winfo_rootx()+max(0,(parent.winfo_width()-self.winfo_reqwidth())//2)
            y=parent.winfo_rooty()+max(0,(parent.winfo_height()-self.winfo_reqheight())//2)
            self.geometry(f"+{x}+{y}")
        except tk.TclError:pass
        self.deiconify();self.lift()
        # Progress callbacks pump Tk events so the window can repaint.  Make
        # the dialog modal while it is visible to prevent a second import or
        # G-code job from being started re-entrantly during that event pump.
        try:self.grab_set()
        except tk.TclError:pass

    def set_progress(self,value:float,message:str=""):
        if self._closed:return
        value=max(0.0,min(100.0,float(value)));whole=int(round(value))
        self.value.set(value);self.percent.set(f"{whole}%")
        if message:self.message.set(message)
        now=time.monotonic()
        if whole==self._last_percent and value<100 and now-self._last_pump<.08:return
        self._last_percent=whole;self._last_pump=now
        try:self.update_idletasks();self.update()
        except tk.TclError:pass

    def close(self):
        if self._closed:return
        self._closed=True
        if self._show_job is not None:
            try:self.after_cancel(self._show_job)
            except tk.TclError:pass
            self._show_job=None
        try:self.grab_release()
        except tk.TclError:pass
        try:self.destroy()
        except tk.TclError:pass


class OcctNativeStepView:
    """GPU-backed OCCT/AIS viewer embedded in a native Tk child window."""
    def __init__(self,canvas:tk.Canvas,model:StepModel):
        if sys.platform!="win32" or model.shape is None:
            raise RuntimeError("Windows OCCT 표시창을 사용할 수 없습니다.")
        # OCP ships as one native extension in the Windows EXE. Importing the
        # exported module objects avoids PyInstaller requiring separate OCP.AIS
        # / OCP.V3d Python module entries.
        from OCP import AIS,Aspect,OpenGl,Quantity,TopAbs,V3d,WNT
        AIS_ColoredShape=AIS.AIS_ColoredShape;AIS_DisplayMode=AIS.AIS_DisplayMode
        AIS_InteractiveContext=AIS.AIS_InteractiveContext;AIS_Shape=AIS.AIS_Shape
        Aspect_DisplayConnection=Aspect.Aspect_DisplayConnection
        Aspect_TypeOfTriedronPosition=Aspect.Aspect_TypeOfTriedronPosition
        OpenGl_GraphicDriver=OpenGl.OpenGl_GraphicDriver
        Quantity_Color=Quantity.Quantity_Color;Quantity_TOC_RGB=Quantity.Quantity_TOC_RGB
        TopAbs_FACE=TopAbs.TopAbs_FACE;V3d_Viewer=V3d.V3d_Viewer;WNT_Window=WNT.WNT_Window

        canvas.update_idletasks();hwnd=int(canvas.winfo_id())
        capsule_new=ctypes.pythonapi.PyCapsule_New
        capsule_new.restype=ctypes.py_object
        capsule_new.argtypes=(ctypes.c_void_p,ctypes.c_char_p,ctypes.c_void_p)
        hwnd_capsule=capsule_new(ctypes.c_void_p(hwnd),None,None)
        self.canvas=canvas;self.model=model;self.window=WNT_Window(hwnd_capsule)
        self.connection=Aspect_DisplayConnection();self.driver=OpenGl_GraphicDriver(self.connection)
        self.driver.SetVerticalSync(True)
        self.viewer=V3d_Viewer(self.driver);self.viewer.SetDefaultLights();self.viewer.SetLightOn()
        self.view=self.viewer.CreateView();self.view.SetWindow(self.window)
        if not self.window.IsMapped():self.window.Map()
        self.context=AIS_InteractiveContext(self.viewer);self.ais=AIS_ColoredShape(model.shape)
        black=Quantity_Color(0.018,0.025,0.032,Quantity_TOC_RGB)
        white=Quantity_Color(0.86,0.96,1.0,Quantity_TOC_RGB)
        body=Quantity_Color(0.22,0.26,0.30,Quantity_TOC_RGB)
        green=Quantity_Color(0.12,0.95,0.62,Quantity_TOC_RGB)
        self.view.SetBackgroundColor(black)
        params=self.view.ChangeRenderingParams();params.NbMsaaSamples=4;params.IsAntialiasingEnabled=True
        drawer=self.context.DefaultDrawer();drawer.SetFaceBoundaryDraw(True)
        drawer.FaceBoundaryAspect().SetColor(white);drawer.FaceBoundaryAspect().SetWidth(2.6)
        self.context.SetColor(self.ais,body,False)
        self.context.SetDisplayMode(self.ais,AIS_DisplayMode.AIS_Shaded,False)
        selection=self.context.SelectionStyle();selection.SetColor(green)
        selection.SetDisplayMode(AIS_DisplayMode.AIS_Shaded)
        self.context.Display(self.ais,False)
        self.context.Activate(self.ais,AIS_Shape.SelectionMode_s(TopAbs_FACE),True)
        self.view.TriedronDisplay(Aspect_TypeOfTriedronPosition.Aspect_TOTP_RIGHT_LOWER,white,.085)
        self.origin_triad=None
        try:
            from OCP import Geom,gp
            axis=Geom.Geom_Axis2Placement(gp.gp_Ax2(gp.gp_Pnt(0.0,0.0,0.0),
                                                    gp.gp_Dir(0.0,0.0,1.0),gp.gp_Dir(1.0,0.0,0.0)))
            self.origin_triad=AIS.AIS_Trihedron(axis)
            vertices=model.vertices or [(0.0,0.0,0.0),(10.0,10.0,10.0)]
            span=max(max(p[i] for p in vertices)-min(p[i] for p in vertices) for i in range(3))
            self.origin_triad.SetSize(max(3.0,span*.14))
        except Exception:
            self.origin_triad=None
        self.sync_transform(False)
        # The Tk child can already have consumed its first Configure/Expose
        # event before OCCT attaches to the HWND.  Synchronise the native
        # window now; otherwise some drivers present the first frame only when
        # a later mouse move, wheel or click calls into the viewer.
        self.present(True)

    @staticmethod
    def matrix_trsf(matrix):
        from OCP import gp
        gp_Trsf=gp.gp_Trsf
        t=gp_Trsf();t.SetValues(matrix[0][0],matrix[0][1],matrix[0][2],matrix[0][3],
                                matrix[1][0],matrix[1][1],matrix[1][2],matrix[1][3],
                                matrix[2][0],matrix[2][1],matrix[2][2],matrix[2][3])
        return t

    def sync_transform(self,redraw=True):
        from OCP import TopLoc
        TopLoc_Location=TopLoc.TopLoc_Location
        # OCCT keeps selection/highlight presentations in their old location
        # unless they are cleared before changing an AIS object's transform.
        # That produced a green ghost of the selected face after XYZ0 presets.
        try:self.context.ClearSelected(False)
        except Exception:pass
        try:self.context.ClearDetected(False)
        except Exception:pass
        self.context.SetLocation(self.ais,TopLoc_Location(self.matrix_trsf(self.model.matrix)))
        if redraw:self.view.Redraw()

    def show_work_origin(self,visible=True):
        if self.origin_triad is None:return
        try:
            if visible:
                self.context.Display(self.origin_triad,False)
                try:self.context.Deactivate(self.origin_triad)
                except Exception:pass
            else:self.context.Erase(self.origin_triad,False)
            self.view.Redraw()
        except Exception:pass

    def set_selection_mode(self,mode):
        from OCP import AIS,TopAbs
        AIS_Shape=AIS.AIS_Shape;TopAbs_FACE=TopAbs.TopAbs_FACE;TopAbs_VERTEX=TopAbs.TopAbs_VERTEX
        self.context.Deactivate(self.ais)
        if mode in ("face","vertex"):
            shape_type=TopAbs_FACE if mode=="face" else TopAbs_VERTEX
            self.context.Activate(self.ais,AIS_Shape.SelectionMode_s(shape_type),True)
        self.view.Redraw()

    def clear_selection(self):self.context.ClearSelected(True)

    def set_feature_colors(self,features):
        from OCP import Quantity
        Quantity_Color=Quantity.Quantity_Color;Quantity_TOC_RGB=Quantity.Quantity_TOC_RGB
        self.ais.ClearCustomAspects()
        for face_index,rgb in features:
            topo=self.model.faces[face_index].topo_shape
            if topo is not None:self.ais.SetCustomColor(topo,Quantity_Color(rgb[0],rgb[1],rgb[2],Quantity_TOC_RGB))
        self.context.Redisplay(self.ais,True,False)

    def pick(self,x,y):
        self.context.MoveTo(int(x),int(y),self.view,False);self.context.Select(True);self.context.InitSelected()
        return self.context.SelectedShape() if self.context.HasSelectedShape() else None

    def hover(self,x,y):self.context.MoveTo(int(x),int(y),self.view,True)
    def start_rotation(self,x,y):self.view.StartRotation(int(x),int(y))
    def rotate(self,x,y):self.view.Rotation(int(x),int(y))
    def pan(self,dx,dy):self.view.Pan(int(dx),int(-dy),1.0,True)
    def zoom(self,factor):self.view.SetZoom(float(factor),True)
    def present(self,fit=False):
        self.canvas.update_idletasks()
        try:self.window.DoResize()
        except Exception:pass
        self.view.MustBeResized()
        try:self.context.UpdateCurrentViewer()
        except Exception:pass
        if fit:self.view.FitAll(.04,False)
        try:self.view.Invalidate()
        except Exception:pass
        self.view.Redraw()

    def resize(self):self.present(False)
    def redraw(self):self.view.Redraw()
    def fit(self):self.present(True)
    def set_projection(self,azimuth,elevation):
        az=math.radians(azimuth);el=math.radians(elevation)
        vx,vy,vz=math.sin(az)*math.sin(el),math.cos(az)*math.sin(el),math.cos(el)
        self.view.SetProj(vx,vy,vz)
        # SetProj keeps the previous camera roll. CAD top/bottom views need a
        # deterministic screen-up vector or an aligned model appears tilted.
        if abs(vz)>.98:self.view.SetUp(0.0,1.0,0.0)
        else:self.view.SetUp(0.0,0.0,1.0)
        self.view.SetTwist(0.0)
        self.view.FitAll(.04,True)

    def screen_to_xy(self,x,y):
        px,py,pz,dx,dy,dz=self.view.ConvertWithProj(int(x),int(y))
        if abs(dz)<EPS:return px,py
        t=-pz/dz;return px+t*dx,py+t*dy

    def selected_face_index(self,shape):
        if shape is None:return None
        for i,face in enumerate(self.model.faces):
            topo=face.topo_shape
            if topo is not None and (shape.IsSame(topo) or shape.IsPartner(topo)):return i
        return None

    def selected_vertex_index(self,shape):
        if shape is None:return None
        try:
            from OCP import BRep,TopoDS
            BRep_Tool=BRep.BRep_Tool;TopoDS_NS=TopoDS.TopoDS
            p=BRep_Tool.Pnt_s(TopoDS_NS.Vertex_s(shape));q=(float(p.X()),float(p.Y()),float(p.Z()))
            return min(range(len(self.model.vertices)),key=lambda i:v3_len(v3_sub(self.model.vertices[i],q)))
        except Exception:return None


class StepSetupDialog(tk.Toplevel):
    """Interactive STEP work-coordinate setup without a second GUI dependency."""
    def __init__(self,parent,model:StepModel,on_apply,on_cancel=None):
        super().__init__(parent);self.title(f"CFRP Router CAM V{APP_VERSION} - STEP 작업좌표계")
        self.geometry("1180x820");self.minsize(920,650);self.model=model;self.on_apply=on_apply;self.on_cancel=on_cancel
        self.selected_face:Optional[int]=None;self.selected_faces:List[int]=[];self.selected_vertex:Optional[int]=None
        self.face_aligned=False;self.work_origin_set=False
        self.mode=tk.StringVar(value="face");self.az=math.radians(-35);self.el=math.radians(28)
        self.zoom=1.0;self.panx=self.pany=0.0;self.drag=None;self.rendered=[];self.screen_scale=1.0
        self.step_draw_job=None;self.step_exact_job=None;self.fast_render=False
        self.native_prime_jobs=[]
        self.native_view=None;self.native_pending=sys.platform=="win32" and model.shape is not None;self.native_error=""
        self.pick_faces=[];self.face_loop_cache={};self.raw_wire_loop_cache={};self.wire_loop_cache={};self.mesh_cache_key=None;self.mesh_cache=[];self.planar_view=tk.BooleanVar(value=False)
        self.rotation=tk.DoubleVar(value=0.0);self.preset=tk.StringVar(value="좌하단")
        bar=ttk.Frame(self,padding=6);bar.pack(fill="x")
        ttk.Radiobutton(bar,text="① 가공면 선택 (Ctrl 다중)",variable=self.mode,value="face",command=self.mode_changed).pack(side="left")
        ttk.Button(bar,text="선택면 → +Z / Z0",command=self.align_face).pack(side="left",padx=4)
        ttk.Radiobutton(bar,text="② 원점 꼭짓점",variable=self.mode,value="vertex",command=self.mode_changed).pack(side="left",padx=(10,0))
        ttk.Button(bar,text="선택점 → XYZ0",command=self.set_vertex_origin).pack(side="left",padx=4)
        ttk.Radiobutton(bar,text="③ XY 끌기",variable=self.mode,value="move",command=self.mode_changed).pack(side="left",padx=(10,0))
        ttk.Button(bar,text="취소",command=self.cancel).pack(side="right")
        ttk.Button(bar,text="CAM으로 가져오기",command=self.commit,style="Accent.TButton").pack(side="right",padx=6)
        ttk.Button(bar,text="초기화",command=self.reset).pack(side="right")
        second=ttk.Frame(self,padding=(6,0,6,6));second.pack(fill="x")
        ttk.Label(second,text="Z 회전 °").pack(side="left")
        ttk.Entry(second,width=8,textvariable=self.rotation).pack(side="left",padx=3)
        ttk.Button(second,text="회전 적용",command=self.apply_rotation).pack(side="left")
        ttk.Button(second,text="−90°",command=lambda:self.rotate_fixed(-90)).pack(side="left",padx=(6,2))
        ttk.Button(second,text="+90°",command=lambda:self.rotate_fixed(90)).pack(side="left")
        ttk.Label(second,text="원점 프리셋").pack(side="left",padx=(18,3))
        ttk.Combobox(second,width=9,state="readonly",textvariable=self.preset,
                     values=("좌하단","좌상단","우하단","우상단","중앙")).pack(side="left")
        ttk.Button(second,text="적용",command=self.apply_preset).pack(side="left",padx=3)
        ttk.Button(second,text="반대면",command=lambda:self.set_view(0,180)).pack(side="right")
        ttk.Button(second,text="Top",command=lambda:self.set_view(0,0)).pack(side="right",padx=3)
        ttk.Button(second,text="등각",command=lambda:self.set_view(-35,28)).pack(side="right")
        ttk.Label(second,text="OCCT GPU 음영 + 외곽선",foreground="#dce7ef").pack(side="right",padx=(0,10))
        self.status=DisplayStringVar(value="가공할 평면을 클릭한 뒤 ‘선택면 → +Z / Z0’을 누르세요.")
        ttk.Label(self,textvariable=self.status,padding=(8,3)).pack(fill="x")
        self.canvas=tk.Canvas(self,bg="#11161c",highlightthickness=0);self.canvas.pack(fill="both",expand=True)
        self.canvas.bind("<Configure>",self.canvas_configure);self.canvas.bind("<Motion>",self.hover_move);self.canvas.bind("<ButtonPress-1>",self.left_press)
        self.canvas.bind("<B1-Motion>",self.left_move);self.canvas.bind("<ButtonRelease-1>",self.left_release)
        self.canvas.bind("<ButtonPress-2>",self.pan_start);self.canvas.bind("<B2-Motion>",self.pan_move);self.canvas.bind("<ButtonRelease-2>",self.pan_end)
        self.canvas.bind("<ButtonPress-3>",self.orbit_start);self.canvas.bind("<B3-Motion>",self.orbit_move);self.canvas.bind("<ButtonRelease-3>",self.orbit_end)
        self.canvas.bind("<MouseWheel>",self.wheel)
        foot=ttk.Frame(self,padding=7);foot.pack(fill="x")
        ttk.Label(foot,text="좌클릭: 단일 선택 · Ctrl+클릭: 면 추가/해제 · 좌/우 드래그: 회전 · 휠 버튼 드래그: 화면 이동 · 휠: 확대/축소").pack(side="left")
        self.protocol("WM_DELETE_WINDOW",self.cancel);self.transient(parent);self.grab_set();self.after_idle(self.init_native_view)

    def init_native_view(self):
        if not self.native_pending:
            self.queue_draw(True);return
        try:
            self.native_view=OcctNativeStepView(self.canvas,self.model)
            self.native_view.set_selection_mode(self.mode.get())
            self.status.set("OCCT GPU 뷰어 · 좌클릭 단일 선택 / Ctrl+클릭 면 추가·해제")
        except Exception as exc:
            self.native_error=f"{type(exc).__name__}: {exc}";self.native_view=None
            self.status.set("GPU 뷰어 초기화 실패 · 호환 뷰어로 표시합니다: "+self.native_error)
        finally:self.native_pending=False
        if self.native_view:
            # Present once after OCCT creation, once after Tk has committed the
            # dialog geometry, and once after Windows has mapped the child.
            # Only the first delayed pass changes the camera fit, so immediate
            # user zoom/rotation is not reset by the later redraws.
            for delay,fit in ((0,True),(70,False),(220,False)):
                job=self.after(delay,lambda use_fit=fit:self.prime_native_view(use_fit))
                self.native_prime_jobs.append(job)
        else:self.queue_draw(True)

    def prime_native_view(self,fit=False):
        if not self.native_view or not self.winfo_exists():return
        try:
            if fit:self.native_view.fit()
            else:self.native_view.resize()
        except Exception:pass

    def canvas_configure(self,e=None):
        if self.native_pending:return
        if self.native_view:
            try:self.native_view.resize()
            except Exception:pass
        else:self.queue_draw(True)

    def hover_move(self,e):
        if self.native_view and self.drag is None and self.mode.get() in ("face","vertex"):
            try:self.native_view.hover(e.x,e.y)
            except Exception:pass

    def cancel(self):
        for job in self.native_prime_jobs:
            try:self.after_cancel(job)
            except tk.TclError:pass
        self.native_prime_jobs.clear()
        callback=self.on_cancel;self.on_cancel=None
        self.destroy()
        if callback:callback()

    def transformed_vertices(self)->List[Point3]:return [mat_apply(self.model.matrix,p) for p in self.model.vertices]
    def transformed_mesh(self):
        key=tuple(round(v,9) for row in self.model.matrix for v in row)
        if key!=self.mesh_cache_key:
            cached=[]
            for face in self.model.faces:
                tv=[mat_apply(self.model.matrix,p) for p in face.vertices]
                cached.append((tv,[(tri,triangle_normal(tv[tri[0]],tv[tri[1]],tv[tri[2]])[0]) for tri in face.triangles]))
            self.mesh_cache_key=key;self.mesh_cache=cached
        return self.mesh_cache
    def transformed_face_center(self,index:int)->Point3:return mat_apply(self.model.matrix,self.model.faces[index].center)
    def transformed_face_normal(self,index:int)->Point3:return v3_unit(mat_apply(self.model.matrix,self.model.faces[index].normal,True))
    def planar_face_loops(self,index:int)->Optional[List[List[Point3]]]:
        key=(index,tuple(round(v,9) for row in self.model.matrix for v in row))
        if key in self.face_loop_cache:return self.face_loop_cache[key]
        face=self.model.faces[index];verts=[mat_apply(self.model.matrix,p) for p in face.vertices]
        if len(verts)<3:self.face_loop_cache[key]=None;return None
        center=self.transformed_face_center(index);normal=self.transformed_face_normal(index)
        span=max(max(p[k] for p in verts)-min(p[k] for p in verts) for k in range(3))
        planar=max(abs(v3_dot(v3_sub(p,center),normal)) for p in verts)<=max(.04,span*.0002)
        loops=self.wire_face_loops(index) if planar else None
        if not loops:loops=None
        self.face_loop_cache[key]=loops;return loops
    def wire_face_loops(self,index:int)->List[List[Point3]]:
        key=(index,tuple(round(v,9) for row in self.model.matrix for v in row))
        if key not in self.wire_loop_cache:
            if index not in self.raw_wire_loop_cache:
                self.raw_wire_loop_cache[index]=face_boundary_loops(self.model.faces[index],mat_identity())
            self.wire_loop_cache[key]=[[mat_apply(self.model.matrix,p) for p in loop]
                                       for loop in self.raw_wire_loop_cache[index]]
        return self.wire_loop_cache[key]
    def active_face_indices(self)->List[int]:
        if self.selected_faces:return list(self.selected_faces)
        return [self.selected_face] if self.selected_face is not None else []
    def select_face(self,index:int,additive:bool=False):
        if additive:
            if index in self.selected_faces:
                self.selected_faces.remove(index)
                if self.selected_face==index:self.selected_face=self.selected_faces[-1] if self.selected_faces else None
            else:
                self.selected_faces.append(index);self.selected_face=index
        else:
            self.selected_faces=[index];self.selected_face=index
        self.selected_vertex=None;self.face_aligned=False
        if self.selected_face is None:
            self.status.set("선택된 가공면이 없습니다.")
        else:
            n=self.transformed_face_normal(self.selected_face)
            self.status.set(f"가공면 {len(self.selected_faces)}개 선택 · 기준면 {self.selected_face+1} · 법선 ({n[0]:.3f}, {n[1]:.3f}, {n[2]:.3f})")
        self.refresh_native_feature_colors()
    def face_selection_error(self)->Optional[str]:
        indices=self.active_face_indices()
        if not indices:return "가공면을 먼저 선택하세요."
        ref=indices[0];ref_normal=self.transformed_face_normal(ref);ref_center=self.transformed_face_center(ref)
        for index in indices[1:]:
            normal=self.transformed_face_normal(index);center=self.transformed_face_center(index)
            if v3_dot(normal,ref_normal)<STEP_FACE_NORMAL_DOT:
                return "선택한 면들의 방향이 서로 다릅니다. 같은 가공 방향의 면만 선택하세요."
            if abs(v3_dot(v3_sub(center,ref_center),ref_normal))>.05:
                return "선택한 면들의 높이가 서로 다릅니다. 같은 높이의 가공면만 선택하세요."
        return None
    def refresh_native_feature_colors(self):
        if not self.native_view:return
        selected=self.active_face_indices()
        if not selected:self.native_view.set_feature_colors([]);return
        feature_map={index:(.10,.78,.48) for index in selected}
        if self.face_aligned:
            for selected_face in selected:
                loops=self.wire_face_loops(selected_face)
                if not loops:continue
                ordered=sorted(loops,key=lambda loop:abs(signed_area([(p[0],p[1]) for p in loop])),reverse=True)
                holes=[[(p[0],p[1]) for p in loop] for loop in ordered[1:]]
                selected_normal=self.transformed_face_normal(selected_face)
                selected_center=self.transformed_face_center(selected_face)
                palette=((.08,.30,.42),(.13,.42,.56),(.48,.35,.10),(.48,.20,.38),(.20,.30,.55))
                rank=0
                for fi in range(len(self.model.faces)):
                    if fi in selected:continue
                    normal=self.transformed_face_normal(fi)
                    if v3_dot(normal,selected_normal)<.985:continue
                    center=self.transformed_face_center(fi)
                    depth=v3_dot(v3_sub(selected_center,center),selected_normal)
                    if depth<=.04 or not any(point_in_poly((center[0],center[1]),hole) for hole in holes):continue
                    feature_map.setdefault(fi,palette[rank%len(palette)]);rank+=1
        self.native_view.set_feature_colors(list(feature_map.items()))
    def origin_candidate_indices(self)->List[int]:
        pts=self.transformed_vertices()
        if self.selected_face is None:return list(range(len(pts)))
        center=self.transformed_face_center(self.selected_face);normal=self.transformed_face_normal(self.selected_face)
        return [i for i,p in enumerate(pts) if abs(v3_dot(v3_sub(p,center),normal))<=.05]
    def data_bounds(self):
        pts=self.transformed_vertices()
        if not pts:pts=[(0,0,0),(1,1,1)]
        return tuple(min(p[i] for p in pts) for i in range(3))+tuple(max(p[i] for p in pts) for i in range(3))
    def project(self,p:Point3,bounds)->Tuple[float,float,float]:
        minx,miny,minz,maxx,maxy,maxz=bounds;cx=(minx+maxx)/2;cy=(miny+maxy)/2;cz=(minz+maxz)/2
        x,y,z=p[0]-cx,p[1]-cy,p[2]-cz;ca,sa=math.cos(self.az),math.sin(self.az)
        x1=x*ca-y*sa;y1=x*sa+y*ca;ce,se=math.cos(self.el),math.sin(self.el)
        sy=y1*ce-z*se;depth=y1*se+z*ce
        w=max(self.canvas.winfo_width(),100);h=max(self.canvas.winfo_height(),100)
        span=max(maxx-minx,maxy-miny,maxz-minz,1);self.screen_scale=min(w,h)*.72/span*self.zoom
        return w/2+self.panx+x1*self.screen_scale,h/2+self.pany-sy*self.screen_scale,depth
    def view_direction(self)->Point3:
        sa,ca=math.sin(self.az),math.cos(self.az);se,ce=math.sin(self.el),math.cos(self.el)
        return sa*se,ca*se,ce
    def set_view(self,az,el):
        self.az=math.radians(az);self.el=math.radians(el);self.panx=self.pany=0
        if self.native_view:self.native_view.set_projection(az,el)
        else:self.draw()
    def schedule_exact_draw(self,delay=140):
        if self.step_exact_job is not None:
            try:self.after_cancel(self.step_exact_job)
            except tk.TclError:pass
        def run():
            self.step_exact_job=None
            if self.drag is not None:return
            self.fast_render=False;self.draw()
        self.step_exact_job=self.after(delay,run)
    def queue_draw(self,fast=True):
        if self.native_pending:return
        if self.native_view:self.native_view.redraw();return
        if fast:self.fast_render=True
        if self.step_draw_job is not None:return
        def run():
            self.step_draw_job=None;self.draw()
            if self.fast_render and self.drag is None:self.schedule_exact_draw()
        self.step_draw_job=self.after(16,run)
    def finish_interaction_draw(self):
        if self.native_view:self.native_view.redraw();return
        if self.step_draw_job is not None:
            try:self.after_cancel(self.step_draw_job)
            except tk.TclError:pass
            self.step_draw_job=None
        if self.step_exact_job is not None:
            try:self.after_cancel(self.step_exact_job)
            except tk.TclError:pass
            self.step_exact_job=None
        self.fast_render=False;self.draw()
    def mode_changed(self):
        if self.native_view:self.native_view.set_selection_mode(self.mode.get())
        if self.mode.get()=="move":self.set_view(0,0);self.status.set("모델을 좌클릭 드래그하여 작업 XY에서 이동하세요.")
        elif self.mode.get()=="vertex":self.status.set("원점으로 사용할 꼭짓점을 클릭하세요.");self.draw()
        else:self.face_aligned=False;self.status.set("가공할 평면을 클릭하세요. 여러 면은 Ctrl+클릭으로 추가/해제합니다.");self.draw()
    def wheel(self,e):
        if self.native_view:self.native_view.zoom(1.15 if e.delta>0 else 1/1.15);return
        self.zoom=max(.15,min(15,self.zoom*(1.15 if e.delta>0 else 1/1.15)));self.queue_draw(True)
    def orbit_start(self,e):
        if self.native_view:self.native_view.start_rotation(e.x,e.y);self.drag=("orbit_native",e.x,e.y);return
        self.drag=("orbit",e.x,e.y,self.az,self.el)
    def orbit_end(self,e):
        if self.drag and self.drag[0] in ("orbit","orbit_native"):self.drag=None;self.finish_interaction_draw()
    def orbit_move(self,e):
        if self.drag and self.drag[0]=="orbit_native":self.native_view.rotate(e.x,e.y);return
        if not self.drag or self.drag[0]!="orbit":return
        _,x,y,az,el=self.drag;self.az=az+(e.x-x)*.01;self.el=el+(e.y-y)*.01;self.queue_draw()
    def pan_start(self,e):
        if self.native_view:self.drag=("pan_native",e.x,e.y);return
        self.drag=("pan",e.x,e.y,self.panx,self.pany)
    def pan_end(self,e):
        if self.drag and self.drag[0] in ("pan","pan_native"):self.drag=None;self.finish_interaction_draw()
    def pan_move(self,e):
        if self.drag and self.drag[0]=="pan_native":
            _,x,y=self.drag;self.native_view.pan(e.x-x,e.y-y);self.drag=("pan_native",e.x,e.y);return
        if not self.drag or self.drag[0]!="pan":return
        _,x,y,px,py=self.drag;self.panx=px+e.x-x;self.pany=py+e.y-y;self.queue_draw()
    def left_press(self,e):
        if self.mode.get()=="move":
            if self.native_view:
                self.drag=("move_native",copy.deepcopy(self.model.matrix),self.native_view.screen_to_xy(e.x,e.y));return
            self.drag=("move",e.x,e.y,copy.deepcopy(self.model.matrix),self.panx,self.pany);return
        if self.native_view:self.native_view.start_rotation(e.x,e.y);self.drag=("pick_native",e.x,e.y);return
        self.drag=("pick",e.x,e.y,self.az,self.el)
    def pick_at(self,e):
        additive=bool(getattr(e,"state",0)&0x0004)
        if self.native_view:
            shape=self.native_view.pick(e.x,e.y)
            if self.mode.get()=="face":
                index=self.native_view.selected_face_index(shape)
                if index is not None:
                    self.select_face(index,additive)
            else:
                index=self.native_view.selected_vertex_index(shape)
                if index is not None:
                    self.selected_vertex=index;p=self.transformed_vertices()[index]
                    self.status.set(f"꼭짓점 선택: X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f}")
            self.native_view.redraw();return
        if self.mode.get()=="face":
            hits=[]
            for depth,fi,outer,holes in self.pick_faces:
                if point_in_poly((e.x,e.y),outer) and not any(point_in_poly((e.x,e.y),h) for h in holes):
                    hits.append((depth,fi))
            if not hits:
                hits=[(x[0],x[1]) for x in self.rendered if point_in_triangle_2d((e.x,e.y),x[2][0],x[2][1],x[2][2])]
            if hits:
                self.select_face(max(hits,key=lambda x:x[0])[1],additive);self.draw()
        else:
            b=self.data_bounds();best=None
            vertices=self.transformed_vertices()
            for i in self.origin_candidate_indices():
                p=vertices[i]
                x,y,z=self.project(p,b);d=math.hypot(e.x-x,e.y-y)
                if best is None or d<best[0]:best=(d,i)
            if best and best[0]<=18:
                self.selected_vertex=best[1];p=self.transformed_vertices()[best[1]]
                self.status.set(f"꼭짓점 선택: X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f}");self.draw()
    def left_move(self,e):
        if not self.drag:return
        if self.drag[0]=="move_native":
            _,base,start=self.drag;now=self.native_view.screen_to_xy(e.x,e.y);dx=now[0]-start[0];dy=now[1]-start[1]
            self.model.matrix=mat_mul(mat_translate(dx,dy,0),base);self.face_loop_cache.clear();self.wire_loop_cache.clear()
            self.native_view.sync_transform();self.status.set(f"XY 이동: ΔX {dx:.3f}  ΔY {dy:.3f} mm");return
        if self.drag[0]=="pick_native":
            _,x,y=self.drag
            if math.hypot(e.x-x,e.y-y)>=4:self.drag=("orbit_left_native",x,y)
        if self.drag[0]=="orbit_left_native":self.native_view.rotate(e.x,e.y);return
        if self.drag[0]=="move":
            _,x,y,base,px,py=self.drag;screen_dx=e.x-x;screen_dy=e.y-y
            dx=screen_dx/max(self.screen_scale,EPS);dy=-screen_dy/max(self.screen_scale,EPS)
            self.model.matrix=mat_mul(mat_translate(dx,dy,0),base);self.panx=px+screen_dx;self.pany=py+screen_dy
            self.face_loop_cache.clear();self.wire_loop_cache.clear();self.queue_draw()
            self.status.set(f"XY 이동: ΔX {dx:.3f}  ΔY {dy:.3f} mm");return
        if self.drag[0]=="pick":
            _,x,y,az,el=self.drag
            if math.hypot(e.x-x,e.y-y)>=4:self.drag=("orbit_left",x,y,az,el)
        if self.drag[0]=="orbit_left":
            _,x,y,az,el=self.drag;self.az=az+(e.x-x)*.01;self.el=el+(e.y-y)*.01;self.queue_draw()
    def left_release(self,e):
        final_draw=bool(self.drag and self.drag[0] in ("orbit_left","move","pick","orbit_left_native","move_native","pick_native"))
        if self.drag and self.drag[0]=="pick_native":self.pick_at(e)
        if self.drag and self.drag[0]=="pick":self.pick_at(e)
        self.drag=None
        if final_draw:self.finish_interaction_draw()
    def align_face(self):
        error=self.face_selection_error()
        if error:messagebox.showerror("STEP 좌표계",error,parent=self);return
        normal=self.transformed_face_normal(self.selected_face);rot=rotation_from_to(normal,(0,0,1))
        self.model.matrix=mat_mul(rot,self.model.matrix)
        center=self.transformed_face_center(self.selected_face);self.model.matrix=mat_mul(mat_translate(0,0,-center[2]),self.model.matrix)
        self.face_aligned=True;self.work_origin_set=False;self.face_loop_cache.clear();self.wire_loop_cache.clear()
        self.selected_vertex=None;self.mode.set("vertex")
        if self.native_view:
            self.native_view.set_selection_mode("vertex");self.native_view.sync_transform(False)
            self.native_view.show_work_origin(False);self.refresh_native_feature_colors()
        self.set_view(0,0)
        self.status.set(f"선택면 {len(self.active_face_indices())}개를 +Z/Z0으로 정렬했습니다. 이제 원점 꼭짓점을 클릭하세요.")
    def set_vertex_origin(self):
        if self.selected_vertex is None:messagebox.showinfo("STEP 원점","원점 꼭짓점을 먼저 선택하세요.",parent=self);return
        p=self.transformed_vertices()[self.selected_vertex]
        self.model.matrix=mat_mul(mat_translate(-p[0],-p[1],-p[2]),self.model.matrix);self.face_loop_cache.clear();self.wire_loop_cache.clear()
        self.work_origin_set=True
        if self.native_view:
            self.native_view.sync_transform(False);self.native_view.show_work_origin(True);self.native_view.fit()
        else:self.draw()
        self.status.set("선택 꼭짓점을 X0 Y0 Z0으로 설정했습니다.")
    def apply_rotation(self):
        try:angle=float(self.rotation.get())
        except (ValueError,tk.TclError):messagebox.showerror("회전","각도를 숫자로 입력하세요.",parent=self);return
        self.model.matrix=mat_mul(mat_rotate_z(angle),self.model.matrix);self.face_loop_cache.clear();self.wire_loop_cache.clear();self.draw();self.status.set(f"작업 Z축 기준 {angle:g}° 회전했습니다.")
    def rotate_fixed(self,angle):self.rotation.set(angle);self.apply_rotation()
    def apply_preset(self):
        pts=self.transformed_vertices();origin_pts=pts
        if self.active_face_indices():
            selected_outer=[]
            for face_index in self.active_face_indices():
                loops=self.wire_face_loops(face_index)
                if loops:selected_outer.extend(max(loops,key=lambda loop:abs(signed_area([(p[0],p[1]) for p in loop]))))
            if selected_outer:origin_pts=selected_outer
        xs=[p[0] for p in origin_pts];ys=[p[1] for p in origin_pts]
        name=self.preset.get()
        x=min(xs) if name in ("좌하단","좌상단","Lower-left","Upper-left") else max(xs) if name in ("우하단","우상단","Lower-right","Upper-right") else (min(xs)+max(xs))/2
        y=min(ys) if name in ("좌하단","우하단","Lower-left","Lower-right") else max(ys) if name in ("좌상단","우상단","Upper-left","Upper-right") else (min(ys)+max(ys))/2
        z=self.transformed_face_center(self.selected_face)[2] if self.selected_face is not None else min(p[2] for p in pts)
        self.model.matrix=mat_mul(mat_translate(-x,-y,-z),self.model.matrix);self.face_loop_cache.clear();self.wire_loop_cache.clear()
        self.work_origin_set=True
        if self.native_view:self.native_view.sync_transform(False);self.native_view.show_work_origin(True)
        if self.selected_face is not None and self.face_aligned:self.set_view(0,0)
        else:self.draw()
        basis="선택면 전체 최외곽" if self.selected_face is not None else "모델 최외곽"
        self.status.set(f"{name} 프리셋: {basis}의 X/Y 끝값을 XYZ0으로 설정했습니다.")
    def reset(self):
        self.model.matrix=mat_identity();self.selected_face=None;self.selected_faces=[];self.selected_vertex=None;self.face_aligned=False;self.work_origin_set=False;self.planar_view.set(False)
        self.face_loop_cache.clear();self.wire_loop_cache.clear();self.zoom=1
        if self.native_view:
            self.native_view.clear_selection();self.native_view.set_feature_colors([]);self.native_view.sync_transform(False);self.native_view.show_work_origin(False)
        self.set_view(-35,28);self.status.set("좌표계를 초기화했습니다.")
    def commit(self):
        error=self.face_selection_error()
        if error:messagebox.showerror("STEP 가져오기",error,parent=self);return
        if any(self.transformed_face_normal(index)[2]<STEP_FACE_NORMAL_DOT for index in self.active_face_indices()):
            messagebox.showerror("STEP 가져오기","선택면이 작업 +Z와 평행하지 않습니다. ‘선택면 → +Z / Z0’을 먼저 누르세요.",parent=self);return
        if not self.work_origin_set:
            messagebox.showerror("STEP 가져오기","작업 원점이 설정되지 않았습니다. 원점 꼭지점을 적용하거나 원점 프리셋을 선택하세요.",parent=self);return
        progress=ProgressDialog(self,"STEP 2D/깊이 변환")
        try:
            contours,stock,depths,added=step_faces_to_2d_features(
                self.model,self.active_face_indices(),self.model.matrix,progress.set_progress)
        except Exception as exc:
            progress.close()
            messagebox.showerror("STEP 가져오기",str(exc),parent=self);return
        progress.close()
        self.on_cancel=None
        self.on_apply(contours,self.model.filename,self.selected_face+1,copy.deepcopy(self.model.matrix),stock,depths,added);self.destroy()
    def draw(self):
        if not self.winfo_exists():return
        if self.native_pending:return
        if self.native_view:
            self.native_view.sync_transform();return
        self.canvas.configure(bg="#070a0d");self.canvas.delete("all")
        b=self.data_bounds();self.rendered=[];self.pick_faces=[];view_dir=self.view_direction()
        minx,miny,minz,maxx,maxy,maxz=b;cx=(minx+maxx)/2;cy=(miny+maxy)/2;cz=(minz+maxz)/2
        ca,sa=math.cos(self.az),math.sin(self.az);ce,se=math.cos(self.el),math.sin(self.el)
        width=max(self.canvas.winfo_width(),100);height=max(self.canvas.winfo_height(),100)
        span=max(maxx-minx,maxy-miny,maxz-minz,1);scale=min(width,height)*.72/span*self.zoom;self.screen_scale=scale
        def project_fast(p:Point3)->Tuple[float,float,float]:
            x,y,z=p[0]-cx,p[1]-cy,p[2]-cz;x1=x*ca-y*sa;y1=x*sa+y*ca
            sy=y1*ce-z*se;depth=y1*se+z*ce
            return width/2+self.panx+x1*scale,height/2+self.pany-sy*scale,depth
        def depth_plane(q):
            x0,y0,z0=q[0];x1,y1,z1=q[1];x2,y2,z2=q[2]
            dx1,dy1=x1-x0,y1-y0;dx2,dy2=x2-x0,y2-y0;det=dx1*dy2-dx2*dy1
            if abs(det)<1e-7:return None
            aa=((z1-z0)*dy2-(z2-z0)*dy1)/det;bb=(dx1*(z2-z0)-dx2*(z1-z0))/det
            return aa,bb,z0-aa*x0-bb*y0

        planar_projected={}
        for fi in range(len(self.model.faces)):
            loops=self.planar_face_loops(fi)
            if not loops:continue
            projected=[]
            for loop in loops:
                q=[project_fast(p) for p in loop];screen=[(p[0],p[1]) for p in q]
                if len(screen)>=3:projected.append((screen,q,sum(p[2] for p in q)/len(q)))
            if not projected:continue
            projected.sort(key=lambda item:abs(signed_area(item[0])),reverse=True)
            plane=None;outer_q=projected[0][1]
            for qi in range(1,len(outer_q)-1):
                plane=depth_plane((outer_q[0],outer_q[qi],outer_q[qi+1]))
                if plane is not None:break
            if plane is None:continue
            planar_projected[fi]=(projected[0][0],[item[0] for item in projected[1:]],projected[0][2],plane)

        # Selected machining plane stays filled, and parallel recessed floors
        # (counterbores/pockets) receive a depth colour without changing renderer.
        depth_labels=[];selected_face_set=set(self.active_face_indices())
        if self.selected_face is not None:
            selected_normal=self.transformed_face_normal(self.selected_face)
            selected_center=self.transformed_face_center(self.selected_face);depth_faces=[]
            selected_projection=planar_projected.get(self.selected_face);selected_holes=selected_projection[1] if selected_projection else []
            palette=("#164b66","#245f78","#6b5424","#70405f","#3d557c")
            for fi,(outer,holes,screen_depth,plane) in planar_projected.items():
                face_normal=self.transformed_face_normal(fi)
                if v3_dot(face_normal,view_dir)<=.015 or v3_dot(face_normal,selected_normal)<.985:continue
                face_depth=v3_dot(v3_sub(selected_center,self.transformed_face_center(fi)),selected_normal)
                if face_depth<-.04:continue
                if fi!=self.selected_face:
                    fc=project_fast(self.transformed_face_center(fi))
                    if not any(point_in_poly((fc[0],fc[1]),hole) for hole in selected_holes):continue
                depth_faces.append((face_depth,screen_depth,fi,outer,holes))
            present={item[2] for item in depth_faces}
            for fi in selected_face_set-present:
                projected=planar_projected.get(fi)
                if projected and v3_dot(self.transformed_face_normal(fi),view_dir)>.015:
                    outer,holes,screen_depth,plane=projected
                    depth_faces.append((0.0,screen_depth,fi,outer,holes))
            depth_faces.sort(key=lambda item:item[0])
            depth_rank={d:i for i,d in enumerate(sorted({round(x[0],3) for x in depth_faces if x[0]>.04}))}
            for face_depth,screen_depth,fi,outer,holes in depth_faces:
                selected=fi in selected_face_set
                color="#2ca879" if selected else palette[depth_rank.get(round(face_depth,3),0)%len(palette)]
                self.canvas.create_polygon(*[v for p in outer for v in p],fill=color,outline="")
                for hole in holes:self.canvas.create_polygon(*[v for p in hole for v in p],fill="#070a0d",outline="")
                if selected or face_depth>.04:
                    lx=sum(p[0] for p in outer)/len(outer);ly=sum(p[1] for p in outer)/len(outer)
                    if not selected:ly+=16+14*depth_rank.get(round(face_depth,3),0)
                    depth_labels.append((lx,ly,f"면 {fi+1}" if selected else f"Z-{face_depth:.3f}"))

        interacting=bool(self.drag) or self.fast_render

        # Build a screen-space depth grid from front-facing mesh triangles.
        # Triangles are never drawn; they only hide boundary lines behind solids.
        # While manipulating the view, planar occluders remain exact and curved
        # mesh occluders are sampled. Releasing the mouse schedules one exact pass.
        cell=64 if interacting else 40;depth_grid={};depth_eps=span*1e-5
        def add_to_grid(record,bx0,by0,bx1,by1):
            bx0=max(-cell,bx0);by0=max(-cell,by0);bx1=min(width+cell,bx1);by1=min(height+cell,by1)
            if bx1<0 or by1<0 or bx0>width or by0>height:return
            for gx in range(math.floor(bx0/cell),math.floor(bx1/cell)+1):
                for gy in range(math.floor(by0/cell),math.floor(by1/cell)+1):depth_grid.setdefault((gx,gy),[]).append(record)
        for fi,(outer,holes,screen_depth,plane) in planar_projected.items():
            if v3_dot(self.transformed_face_normal(fi),view_dir)<=1e-6:continue
            add_to_grid(("poly",fi,outer,holes,plane),min(p[0] for p in outer),min(p[1] for p in outer),
                        max(p[0] for p in outer),max(p[1] for p in outer))
        mesh=self.transformed_mesh()
        nonplanar_triangles=sum(len(triangles) for fi,(tv,triangles) in enumerate(mesh) if fi not in planar_projected)
        triangle_budget=700 if interacting else 12000
        triangle_stride=max(1,math.ceil(nonplanar_triangles/triangle_budget))
        triangle_serial=0
        for fi,(tv,triangles) in enumerate(mesh):
            if fi in planar_projected:continue
            for tri,normal in triangles:
                triangle_serial+=1
                if interacting and triangle_serial%triangle_stride:continue
                a,bp,cp=tv[tri[0]],tv[tri[1]],tv[tri[2]]
                if v3_dot(normal,view_dir)<=1e-6:continue
                q=[project_fast(a),project_fast(bp),project_fast(cp)];plane=depth_plane(q)
                if plane is None:continue
                pts=((q[0][0],q[0][1]),(q[1][0],q[1][1]),(q[2][0],q[2][1]))
                add_to_grid(("tri",fi,pts,plane),min(p[0] for p in pts),min(p[1] for p in pts),
                            max(p[0] for p in pts),max(p[1] for p in pts))
        def hidden_at(x,y,z,owner):
            for record in depth_grid.get((math.floor(x/cell),math.floor(y/cell)),()):
                kind,other=record[0],record[1]
                if other==owner:continue
                if kind=="tri":
                    triangle,plane=record[2],record[3]
                    if not point_in_triangle_2d((x,y),*triangle):continue
                else:
                    outer,holes,plane=record[2],record[3],record[4]
                    if not point_in_poly((x,y),outer) or any(point_in_poly((x,y),hole) for hole in holes):continue
                if plane[0]*x+plane[1]*y+plane[2]>z+depth_eps:return True
            return False

        # Draw only true CAD face boundaries. Long edges are split so nearer
        # triangles can hide just the covered portion instead of the whole edge.
        step_px=52 if interacting else 12
        for fi in range(len(self.model.faces)):
            selected=fi in selected_face_set;color="#8fffd3" if selected else "#dcf4ff";line_width=4 if selected else 3
            for loop in self.wire_face_loops(fi):
                q=[project_fast(p) for p in loop]
                if len(q)<2:continue
                run=[]
                for a,bp in zip(q,q[1:]+q[:1]):
                    pieces=max(1,int(math.ceil(math.hypot(bp[0]-a[0],bp[1]-a[1])/step_px)))
                    for piece in range(pieces):
                        f0=piece/pieces;f1=(piece+1)/pieces
                        p0=(a[0]+(bp[0]-a[0])*f0,a[1]+(bp[1]-a[1])*f0,a[2]+(bp[2]-a[2])*f0)
                        p1=(a[0]+(bp[0]-a[0])*f1,a[1]+(bp[1]-a[1])*f1,a[2]+(bp[2]-a[2])*f1)
                        mx,my,mz=(p0[0]+p1[0])/2,(p0[1]+p1[1])/2,(p0[2]+p1[2])/2
                        if hidden_at(mx,my,mz,fi):
                            if len(run)>=4:self.canvas.create_line(*run,fill=color,width=line_width)
                            run=[];continue
                        if not run:run=[p0[0],p0[1]]
                        run.extend((p1[0],p1[1]))
                if len(run)>=4:self.canvas.create_line(*run,fill=color,width=line_width)

        # Planar face polygons remain available for reliable machining-face picking.
        for fi,(outer,holes,screen_depth,plane) in planar_projected.items():
            if v3_dot(self.transformed_face_normal(fi),view_dir)>.015:self.pick_faces.append((screen_depth,fi,outer,holes))
        for lx,ly,label in depth_labels:
            self.canvas.create_text(lx,ly,text=label,fill="#ffffff",font=("Arial",11,"bold"))
        # Work origin triad stays at the selected XYZ0 after the selection mode closes.
        if self.work_origin_set:
            origin=(0,0,0);axis_size=max(b[3]-b[0],b[4]-b[1],b[5]-b[2],1)*.12
            colors=((axis_size,0,0,"#ff4f4f","X"),(0,axis_size,0,"#5ee36c","Y"),(0,0,axis_size,"#5aa7ff","Z"))
            ox,oy,_=self.project(origin,b)
            for x,y,z,color,label in colors:
                ex,ey,_=self.project((x,y,z),b);self.canvas.create_line(ox,oy,ex,ey,fill=color,width=4,arrow="last");self.canvas.create_text(ex+7,ey-7,text=label,fill=color,font=("Arial",11,"bold"))
        if self.mode.get()=="vertex":
            vertices=self.transformed_vertices()
            for i in self.origin_candidate_indices():
                p=vertices[i]
                x,y,_=self.project(p,b);r=6 if i==self.selected_vertex else 3
                self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="#ffb13b" if i==self.selected_vertex else "#f4e9b2",outline="white" if i==self.selected_vertex else "")



class Toolpath3D(tk.Toplevel):
    # Glasbey-style order: adjacent depths are deliberately far apart in hue.
    # Additional depths reuse these hues with light/dark variants.
    DEPTH_COLORS=("#00D9FF","#FFB000","#FF4FC3","#7DFF4F","#8A63FF","#FF4B45",
                  "#00E5A0","#FFE04A","#4385FF","#D65CFF","#FF7A24","#B7F000")
    TAB_LINE_COLOR="#FFD21A"
    TAB_LINE_WIDTH=3

    def __init__(self,parent,moves:List[Move3D],cfg:dict):
        super().__init__(parent);self.title(f"CFRP Router CAM V{APP_VERSION} - 3D Toolpath Simulation");self.geometry("1100x760")
        self.moves=moves;self.cfg=cfg;self.az=math.radians(-35);self.el=math.radians(-35)
        self.zoom=1.0;self.panx=self.pany=0.0;self.drag=None;self.playing=False;self.sim_time=0.0
        self._last_tick=None;self._timeline_internal=False
        self.draw_job=None;self.move_items:List[Optional[int]]=[];self.depth_items:List[Optional[int]]=[]
        self.rendered_done=0
        self.speed=tk.DoubleVar(value=20.0);self.show_rapid=tk.BooleanVar(value=True)
        self.sim_mode=tk.StringVar(value="깊이맵")
        self.total_time=sum(m.seconds for m in moves);self.cumulative=[];run=0.0
        for m in moves:run+=m.seconds;self.cumulative.append(run)
        self.bounds=self.data_bounds();self.tab_move_indices=self.collect_tab_move_indices()
        self.depth_levels=self.collect_depth_levels()
        bar=ttk.Frame(self,padding=5);bar.pack(fill="x")
        ttk.Button(bar,text="▶ 재생",command=self.play).pack(side="left")
        ttk.Button(bar,text="⏸ 일시정지",command=self.pause).pack(side="left",padx=3)
        ttk.Button(bar,text="■ 처음",command=self.stop).pack(side="left")
        ttk.Label(bar,text="속도").pack(side="left",padx=(12,3))
        ttk.Combobox(bar,width=6,state="readonly",textvariable=self.speed,values=(1,5,10,20,50,100)).pack(side="left")
        self.rapid_check=ttk.Checkbutton(bar,text="급속이동 표시",variable=self.show_rapid,command=self.draw)
        self.rapid_check.pack(side="left",padx=10)
        ttk.Label(bar,text="표시 방식").pack(side="left",padx=(4,3))
        mode_box=ttk.Combobox(bar,width=9,state="readonly",textvariable=self.sim_mode,values=("공구경로","깊이맵"))
        mode_box.pack(side="left");mode_box.bind("<<ComboboxSelected>>",self.mode_changed)
        for label,view in (("등각",(-35,-35)),("Top",(0,0)),("Front",(0,-90))):
            ttk.Button(bar,text=label,command=lambda v=view:self.set_view(*v)).pack(side="right",padx=2)
        self.info=DisplayStringVar(value="")
        ttk.Label(self,textvariable=self.info,padding=(7,2)).pack(fill="x")
        self.timeline=tk.DoubleVar(value=0.0)
        self.slider=ttk.Scale(self,from_=0,to=max(self.total_time,.001),variable=self.timeline,command=self.scrub)
        self.slider.pack(fill="x",padx=7,pady=(0,4))
        viewer=ttk.Frame(self);viewer.pack(fill="both",expand=True)
        self.legend=tk.Canvas(viewer,width=145,bg="#0d1217",highlightthickness=0)
        self.legend.bind("<Configure>",lambda e:self.draw_depth_legend())
        self.canvas=tk.Canvas(viewer,bg="#11161c",highlightthickness=0);self.canvas.pack(side="left",fill="both",expand=True)
        self.canvas.bind("<Configure>",self.request_draw);self.canvas.bind("<ButtonPress-1>",self.rotate_start)
        self.canvas.bind("<B1-Motion>",self.rotate_move);self.canvas.bind("<ButtonPress-2>",self.pan_start)
        self.canvas.bind("<B2-Motion>",self.pan_move);self.canvas.bind("<MouseWheel>",self.wheel)
        self.protocol("WM_DELETE_WINDOW",self.close);self.mode_changed();self.after(30,self.tick)

    def close(self):self.playing=False;self.destroy()
    def set_view(self,az,el):
        self.az=math.radians(az);self.el=math.radians(el);self.panx=self.pany=0.0;self.zoom=1.0;self.request_draw()
    def play(self):
        if self.sim_time>=self.total_time-EPS:
            self.sim_time=0.0;self._set_timeline(0.0);self.update_frame()
        self._last_tick=time.monotonic();self.playing=True
    def pause(self):self.playing=False;self._last_tick=None
    def stop(self):
        self.playing=False;self._last_tick=None;self.sim_time=0.0
        self._set_timeline(0.0);self.update_frame()
    def _set_timeline(self,value:float):
        self._timeline_internal=True
        try:self.timeline.set(value)
        finally:self._timeline_internal=False
    def scrub(self,value):
        # A user-controlled seek owns the timeline.  Pausing here prevents the
        # periodic playback tick from fighting the slider thumb.
        if getattr(self,"_timeline_internal",False):return
        self.playing=False;self._last_tick=None
        self.sim_time=max(0.0,min(float(value),self.total_time));self.update_frame()
    def rotate_start(self,e):self.drag=(e.x,e.y,self.az,self.el)
    def rotate_move(self,e):
        x,y,az,el=self.drag;self.az=az+(e.x-x)*.01;self.el=max(-math.pi/2,min(math.pi/2,el+(e.y-y)*.01));self.request_draw()
    def pan_start(self,e):self.drag=(e.x,e.y,self.panx,self.pany)
    def pan_move(self,e):
        x,y,px,py=self.drag;self.panx=px+e.x-x;self.pany=py+e.y-y;self.request_draw()
    def wheel(self,e):
        old=self.zoom;new=max(.15,min(12,old*(1.15 if e.delta>0 else 1/1.15)))
        if abs(new-old)<EPS:return
        # Keep the model point currently below the cursor at the same screen
        # position instead of pulling every zoom operation toward the center.
        ratio=new/old;w=max(self.canvas.winfo_width(),100);h=max(self.canvas.winfo_height(),100)
        dx=e.x-w/2;dy=e.y-h/2
        self.panx=dx-ratio*(dx-self.panx);self.pany=dy-ratio*(dy-self.pany)
        self.zoom=new
        # Scale the existing scene immediately around the pointer, then do one
        # exact projection after the wheel burst.  Rebuilding thousands of
        # lines on every wheel notch made zoom feel delayed even though the
        # anchor math itself was correct.
        self.canvas.scale("all",e.x,e.y,ratio,ratio)
        if self.draw_job is not None:
            try:self.after_cancel(self.draw_job)
            except tk.TclError:pass
        self.draw_job=self.after(90,self._run_draw)
    def request_draw(self,*_):
        if self.draw_job is None and self.winfo_exists():self.draw_job=self.after(16,self._run_draw)
    def _run_draw(self):self.draw_job=None;self.draw()
    def mode_changed(self,*_):
        depth=self.sim_mode.get() in ("깊이맵","Depth map")
        if depth:
            if not self.legend.winfo_manager():self.legend.pack(side="left",fill="y",before=self.canvas)
            self.rapid_check.state(["disabled"]);self.draw_depth_legend()
        else:
            if self.legend.winfo_manager():self.legend.pack_forget()
            self.rapid_check.state(["!disabled"])
        self.draw()

    def move_depth(self,m:Move3D)->float:
        top=self.cfg["stock"] if self.cfg.get("z_origin")=="Bottom" else 0.0
        return max(0.0,min(float(self.cfg["stock"]),top-min(m.start[2],m.end[2])))

    def collect_tab_move_indices(self)->set:
        """Find tab ramps and their flat crest so they can be redrawn on top."""
        marked=set();stock=float(self.cfg["stock"])
        def xy_length(move:Move3D)->float:
            return math.hypot(move.end[0]-move.start[0],move.end[1]-move.start[1])
        def connected(a:Move3D,b:Move3D)->bool:
            return math.sqrt(sum((a.end[k]-b.start[k])**2 for k in range(3)))<=.02
        for index,move in enumerate(self.moves):
            if move.rapid or xy_length(move)<EPS or abs(move.start[2]-move.end[2])<=.01:continue
            shallow_z=max(move.start[2],move.end[2])
            top=stock if self.cfg.get("z_origin")=="Bottom" else 0.0
            shallow_depth=max(0.0,min(stock,top-shallow_z))
            if shallow_depth>=stock-EPS:continue
            marked.add(index)
            # A crest is often split at every original DXF/STEP vertex.  Walk
            # the whole connected constant-Z run on both sides of the ramp;
            # checking only one neighbour leaves black gaps in curved tabs.
            for step in (-1,1):
                adjacent=index+step;previous=move
                while 0<=adjacent<len(self.moves):
                    other=self.moves[adjacent]
                    if other.rapid or xy_length(other)<EPS or abs(other.start[2]-other.end[2])>.01:break
                    if abs(other.start[2]-shallow_z)>.02:break
                    is_connected=connected(other,previous) if step<0 else connected(previous,other)
                    if not is_connected:break
                    marked.add(adjacent);previous=other;adjacent+=step
        return marked

    def tab_move_runs(self,limit:Optional[int]=None)->List[List[int]]:
        """Return completed tab moves as connected polylines, not paint dabs."""
        stop=len(self.moves) if limit is None else max(0,min(int(limit),len(self.moves)))
        indices=sorted(index for index in self.tab_move_indices if 0<=index<stop)
        runs:List[List[int]]=[]
        for index in indices:
            if runs and index==runs[-1][-1]+1:
                previous=self.moves[runs[-1][-1]];current=self.moves[index]
                gap=math.sqrt(sum((previous.end[k]-current.start[k])**2 for k in range(3)))
                if gap<=.02:
                    runs[-1].append(index);continue
            runs.append([index])
        return runs

    def collect_depth_levels(self)->List[float]:
        histogram:Dict[float,float]={};stock=float(self.cfg["stock"])
        tab_indices=getattr(self,"tab_move_indices",set())
        for index,move in enumerate(self.moves):
            if index in tab_indices:continue
            if move.rapid or abs(move.start[2]-move.end[2])>.01:continue
            length=math.hypot(move.end[0]-move.start[0],move.end[1]-move.start[1])
            depth=self.move_depth(move)
            if length<EPS or depth<EPS:continue
            key=stock if depth>=stock-EPS else round(depth,2)
            histogram[key]=histogram.get(key,0.0)+length
        if not histogram:return [stock]
        # Every real flat cutting depth receives a legend cell.  Length-based
        # filtering used to hide short counterbores/pockets in large jobs.
        return sorted(histogram)

    def color_for_depth(self,depth:float)->str:
        stock=float(self.cfg["stock"])
        if depth>=stock-EPS:return "#050607"
        non_through=[d for d in self.depth_levels if d<stock-EPS]
        if not non_through:return self.DEPTH_COLORS[0]
        index=min(range(len(non_through)),key=lambda i:abs(non_through[i]-depth))
        base=self.DEPTH_COLORS[index%len(self.DEPTH_COLORS)]
        cycle=index//len(self.DEPTH_COLORS)
        if cycle==0:return base
        rgb=[int(base[i:i+2],16) for i in (1,3,5)]
        strength=min(.58,.15*((cycle+1)//2))
        if cycle%2:
            rgb=[round(v+(255-v)*strength) for v in rgb]
        else:rgb=[round(v*(1.0-strength)) for v in rgb]
        return "#%02X%02X%02X"%tuple(rgb)

    def draw_depth_legend(self):
        if not hasattr(self,"legend") or not self.legend.winfo_exists():return
        self.legend.delete("all");w=max(self.legend.winfo_width(),145);h=max(self.legend.winfo_height(),300)
        self.legend.create_text(w/2,22,text="가공 깊이",fill="#e8f0f7",font=("Arial",11,"bold"))
        stock=max(float(self.cfg.get("stock",0.0)),0.0)
        rows=[(0.0,"#2a343d","표면 0.00")]
        for depth in self.depth_levels:
            label=f"관통 ≥{stock:.2f}" if depth>=stock-EPS else f"{depth:.2f} mm"
            rows.append((depth,self.color_for_depth(depth),label))
        x0,x1=16,50;y0=47;available=max(40,h-y0-24);cell=max(7,min(44,available/max(len(rows),1)))
        label_font=("Arial",8 if len(rows)>18 else 9,"bold")
        for index,(_,color,label) in enumerate(rows):
            y=y0+index*cell
            gap=1 if cell<14 else 4
            self.legend.create_rectangle(x0,y,x1,y+cell-gap,fill=color,outline="#d8e1e9",width=1)
            self.legend.create_text(x1+10,y+(cell-gap)/2,text=label,fill="#d8e1e9",anchor="w",font=label_font)
    def tick(self):
        if not self.winfo_exists():return
        if self.playing:
            now=time.monotonic();last=self._last_tick
            self._last_tick=now
            if last is not None:self.sim_time+=max(0.0,now-last)*self.speed.get()
            if self.sim_time>=self.total_time:
                self.sim_time=self.total_time;self.playing=False;self._last_tick=None
            self._set_timeline(self.sim_time);self.update_frame()
        self.after(30,self.tick)

    def data_bounds(self):
        pts=[p for m in self.moves for p in (m.start,m.end)]
        return tuple(min(p[i] for p in pts) for i in range(3))+tuple(max(p[i] for p in pts) for i in range(3))
    def project(self,p,bounds):
        minx,miny,minz,maxx,maxy,maxz=bounds;cx=(minx+maxx)/2;cy=(miny+maxy)/2;cz=(minz+maxz)/2
        x,y,z=p[0]-cx,p[1]-cy,p[2]-cz;ca,sa=math.cos(self.az),math.sin(self.az)
        x1=x*ca-y*sa;y1=x*sa+y*ca;ce,se=math.cos(self.el),math.sin(self.el)
        sy=y1*ce-z*se
        w=max(self.canvas.winfo_width(),100);h=max(self.canvas.winfo_height(),100)
        span=max(maxx-minx,maxy-miny,maxz-minz,1);scale=min(w,h)*.72/span*self.zoom
        return w/2+self.panx+x1*scale,h/2+self.pany-sy*scale
    def draw(self):
        if not self.moves or not self.winfo_exists():return
        self.canvas.delete("all");b=self.bounds;minx,miny,minz,maxx,maxy,maxz=b
        margin=max(maxx-minx,maxy-miny,1)*.04
        top=self.cfg["stock"] if self.cfg.get("z_origin")=="Bottom" else 0.0
        bottom=0.0 if self.cfg.get("z_origin")=="Bottom" else -self.cfg["stock"]
        corners=[(minx-margin,miny-margin,top),(maxx+margin,miny-margin,top),(maxx+margin,maxy+margin,top),(minx-margin,maxy+margin,top)]
        xy=[v for p in corners for v in self.project(p,b)];self.canvas.create_polygon(*xy,fill="#202a32",outline="#65727d",width=2)
        for p,q in zip(corners,corners[1:]+corners[:1]):
            pb=(p[0],p[1],bottom);qb=(q[0],q[1],bottom)
            self.canvas.create_line(*self.project(p,b),*self.project(pb,b),fill="#46515a")
            self.canvas.create_line(*self.project(pb,b),*self.project(qb,b),fill="#46515a")
        path_mode=self.sim_mode.get() in ("공구경로","Toolpath");self.move_items=[]
        for m in self.moves:
            if not path_mode or (m.rapid and not self.show_rapid.get()):self.move_items.append(None);continue
            item=self.canvas.create_line(*self.project(m.start,b),*self.project(m.end,b),
                                         fill="#303841",dash=(3,4),width=1)
            self.move_items.append(item)
        self.depth_items=[None]*len(self.moves)
        self.depth_layer_tags={}
        legend="빨강: 절삭 · 회색 점선: 급속 · 노랑: 현재 공구" if path_mode else "왼쪽 색상: 제거 깊이 · 검정: 관통 · 밝은 노랑: 남은 탭"
        self.canvas.create_text(12,12,text=legend,fill="#d9e2ea",anchor="nw")
        self.rendered_done=0;self.update_frame()

    def _depth_style(self,m:Move3D)->Optional[Tuple[str,float,Tuple[float,float,float],Tuple[float,float,float]]]:
        if m.rapid:return None
        xy_length=math.hypot(m.end[0]-m.start[0],m.end[1]-m.start[1])
        if xy_length<EPS:return None
        top=self.cfg["stock"] if self.cfg.get("z_origin")=="Bottom" else 0.0
        depth=self.move_depth(m)
        if depth<EPS:return None
        color=self.color_for_depth(depth)
        minx,miny,minz,maxx,maxy,maxz=self.bounds
        width=max(self.canvas.winfo_width(),100);height=max(self.canvas.winfo_height(),100)
        span=max(maxx-minx,maxy-miny,maxz-minz,1.0)
        scale=min(width,height)*.72/span*self.zoom
        line_width=max(2.0,float(self.cfg.get("tool_d",2.0))*scale)
        a=(m.start[0],m.start[1],top);b=(m.end[0],m.end[1],top)
        return color,line_width,a,b

    def _add_depth_item(self,index:int):
        if self.sim_mode.get() not in ("깊이맵","Depth map") or self.depth_items[index] is not None:return
        style=self._depth_style(self.moves[index])
        if style is None:return
        color,width,a,b=style
        depth=self.move_depth(self.moves[index]);depth_tag=self._depth_layer_tag(depth)
        item=self.canvas.create_line(*self.project(a,self.bounds),*self.project(b,self.bounds),
                                     fill=color,width=width,capstyle="round",tags=("removed",depth_tag))
        self.depth_items[index]=item
        path_item=self.move_items[index] if index<len(self.move_items) else None
        if path_item is not None:
            try:self.canvas.tag_lower(item,path_item)
            except tk.TclError:pass

    def _depth_layer_tag(self,depth:float)->str:
        if not hasattr(self,"depth_layer_tags"):self.depth_layer_tags={}
        # Match the 0.01 mm depth resolution used by the legend.  This keeps
        # tessellated tab ramps from creating hundreds of one-item layers.
        key=round(float(depth),2)
        if key not in self.depth_layer_tags:
            self.depth_layer_tags[key]=f"removed_depth_{len(self.depth_layer_tags)}"
        return self.depth_layer_tags[key]

    def _restack_depth_layers(self):
        # Canvas items normally stack in creation order, which can let a later
        # shallow pass paint over a previous through-cut.  Raise layers from
        # shallow to deep so maximum material removal always remains visible.
        for depth in sorted(getattr(self,"depth_layer_tags",{})):
            self.canvas.tag_raise(self.depth_layer_tags[depth])

    def _remove_depth_item(self,index:int):
        item=self.depth_items[index] if index<len(self.depth_items) else None
        if item is not None:self.canvas.delete(item);self.depth_items[index]=None

    def _redraw_tab_lines(self,done:int):
        """Draw each remaining tab as one fixed-width centreline.

        The depth map itself is drawn at cutter diameter.  Using that same
        width for every tessellated tab segment produced yellow blobs and
        visible joints on curves, so the overlay is deliberately independent
        of cutter diameter and zoom scale.
        """
        self.canvas.delete("tab_remaining")
        if self.sim_mode.get() not in ("깊이맵","Depth map"):return
        top=self.cfg["stock"] if self.cfg.get("z_origin")=="Bottom" else 0.0
        for run in self.tab_move_runs(done):
            points=[self.moves[run[0]].start]
            points.extend(self.moves[index].end for index in run)
            projected=[]
            for point in points:
                projected.extend(self.project((point[0],point[1],top),self.bounds))
            if len(projected)>=4:
                self.canvas.create_line(*projected,fill=self.TAB_LINE_COLOR,
                                        width=self.TAB_LINE_WIDTH,capstyle="round",
                                        joinstyle="round",tags="tab_remaining")

    def _set_move_style(self,index:int,finished:bool):
        item=self.move_items[index] if index<len(self.move_items) else None
        if item is None:return
        m=self.moves[index]
        if finished:
            self.canvas.itemconfigure(item,fill="#8996a3" if m.rapid else "#ff6257",
                                      dash=(5,4) if m.rapid else (),width=1 if m.rapid else 2)
        else:self.canvas.itemconfigure(item,fill="#303841",dash=(3,4),width=1)

    def update_frame(self):
        if not self.moves or not self.move_items or not self.winfo_exists():return
        done=bisect.bisect_right(self.cumulative,self.sim_time+EPS)
        if done>self.rendered_done:
            for index in range(self.rendered_done,done):
                self._add_depth_item(index);self._set_move_style(index,True)
        elif done<self.rendered_done:
            for index in range(done,self.rendered_done):
                self._remove_depth_item(index);self._set_move_style(index,False)
        self.rendered_done=done
        self.canvas.delete("dynamic")
        self._redraw_tab_lines(done)
        elapsed=min(self.sim_time,self.total_time)
        if done>=len(self.moves):current=self.moves[-1].end
        else:
            m=self.moves[done];startt=self.cumulative[done]-m.seconds
            fraction=max(0.0,min(1.0,(self.sim_time-startt)/max(m.seconds,EPS)))
            current=tuple(m.start[k]+(m.end[k]-m.start[k])*fraction for k in range(3))
            depth_style=self._depth_style(m) if self.sim_mode.get() in ("깊이맵","Depth map") else None
            if fraction>EPS and depth_style is not None:
                color,width,a,_=depth_style;top=a[2];partial=(current[0],current[1],top)
                is_tab=done in self.tab_move_indices
                if is_tab:color=self.TAB_LINE_COLOR;width=self.TAB_LINE_WIDTH
                depth_tag=self._depth_layer_tag(self.move_depth(m))
                tags=("dynamic",depth_tag,"tab_remaining") if is_tab else ("dynamic",depth_tag)
                self.canvas.create_line(*self.project(a,self.bounds),*self.project(partial,self.bounds),
                                        fill=color,width=width,capstyle="round",tags=tags)
            if self.sim_mode.get() in ("공구경로","Toolpath") and fraction>EPS and (not m.rapid or self.show_rapid.get()):
                self.canvas.create_line(*self.project(m.start,self.bounds),*self.project(current,self.bounds),
                                        fill="#aab4bf" if m.rapid else "#ffd447",
                                        dash=(5,4) if m.rapid else (),width=3,tags="dynamic")
        self._restack_depth_layers()
        try:self.canvas.tag_raise("tab_remaining")
        except tk.TclError:pass
        x,y=self.project(current,self.bounds)
        self.canvas.create_oval(x-6,y-6,x+6,y+6,fill="#ffe26a",outline="white",width=2,tags="dynamic")
        shank=(current[0],current[1],current[2]+max(self.cfg["stock"],5.0))
        sx,sy=self.project(shank,self.bounds);self.canvas.create_line(sx,sy,x,y,fill="#c7d0d8",width=5,tags="dynamic")
        self.canvas.create_text(x+10,y-12,text=f"X{current[0]:.2f} Y{current[1]:.2f} Z{current[2]:.2f}",
                                fill="white",anchor="w",tags="dynamic")
        self.info.set(f"{self.sim_mode.get()} | 이동 {done}/{len(self.moves)}   시간 {elapsed:.1f}/{self.total_time:.1f}초   Z+ 윗면 / 아래쪽 바닥·탭   좌드래그: 회전 · 가운데드래그: 이동 · 휠: 확대")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._configure_theme()
        language = saved_interface_language()
        self._language_was_prompted = language is None
        if language is None:
            self.withdraw()
            language = choose_interface_language(self)
        self.language = language
        global CURRENT_LANGUAGE
        CURRENT_LANGUAGE = language
        self.deiconify()
        self.title(f"CFRP Router CAM V{APP_VERSION} - 2D/2.5D / Mach3")
        self.geometry("1280x800")
        self.minsize(980, 650)
        self.contours: List[Contour] = []
        self.part_objects: List[PartObject] = []
        self.next_object_id = 1
        self.pending_imports: List[str] = []
        self.filename = ""
        self.gcode = ""
        self.gcode_parts:List[Tuple[str,str]] = []
        self.gcode_split_mode = False
        self.gcode_job_minutes = 0.0
        self.gcode_signature = None
        self.undo_stack: List[Tuple[str, dict]] = []
        self.redo_stack: List[Tuple[str, dict]] = []
        self.manual_mode = False
        self.join_mode = False
        self.join_first: Optional[Contour] = None
        self.start_mode = False
        self.origin_mode = False
        self.measure_mode = False
        self.measure_start: Optional[Point] = None
        self.measurement = None
        self.view_initialized = False
        self.pan_anchor = None
        self.view_redraw_job = None
        self.view_transform_job = None
        self.view_interacting = False
        self.pending_view_scale = 1.0
        self.pending_view_tx = self.pending_view_ty = 0.0
        self.preview_cache = {}
        self.preview_order_cache_key = None
        self.preview_order_cache:List[Contour] = []
        self.collision_cache_key = None
        self.collision_cache:Dict[int,List[str]] = {}
        self.nest_source:Optional[List[Contour]] = None
        self.nest_active = False
        self.manual_array_mode = False
        self.manual_array_selected:Optional[Tuple[int,int]] = None
        self.manual_array_drag = None
        self.canvas_selection_drag = None
        self.sheet_size:Optional[Tuple[float,float]] = None
        self.view_only: Optional[List[Contour]] = None
        self.ui_font_size = 10
        self.tree_sort_col: Optional[str] = None
        self.tree_sort_reverse = False
        self.selected: Optional[Contour] = None
        self.selected_contours:List[Contour] = []
        self.syncing_tree_selection=False
        self._update_queue=queue.Queue()
        self._update_check_running=False
        self._update_download_running=False
        self._update_manual=False
        self._update_progress:Optional[ProgressDialog]=None
        self.step_matrix: Optional[List[List[float]]] = None
        self.view = (1.0, 0.0, 0.0)
        self.vars = {}
        self._build()
        self.load_settings()
        self.protocol("WM_DELETE_WINDOW",self.on_close)
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-Z>", self.undo)
        self.bind_all("<Control-y>", self.redo)
        self.bind_all("<Control-Y>", self.redo)
        self.bind_all("<Escape>",self.clear_measurement)
        self.bind_all("<KeyPress-r>",self.rotate_manual_array_selected)
        self.bind_all("<KeyPress-R>",self.rotate_manual_array_selected)
        if getattr(sys,"frozen",False):self.after(1800,self.start_update_check)

    def var(self, key, value, cls=tk.DoubleVar):
        self.vars[key] = cls(value=value)
        return self.vars[key]

    def _configure_theme(self):
        bg="#0b1220";panel="#101a2d";field="#08101f";border="#22304a"
        text="#e8eef8";muted="#91a0b8";button="#17233a";hover="#243553";accent="#00cfa6"
        self.configure(bg=bg)
        style=ttk.Style(self)
        try:style.theme_use("clam")
        except tk.TclError:pass
        style.configure(".",background=bg,foreground=text,font=("Segoe UI",10))
        style.configure("TFrame",background=bg)
        style.configure("TLabel",background=bg,foreground=text)
        style.configure("TButton",background=button,foreground=text,bordercolor=border,lightcolor=button,
                        darkcolor=button,relief="flat",borderwidth=1,padding=(9,6),font=("Segoe UI",9,"bold"))
        style.map("TButton",background=[("pressed","#0c8f78"),("active",hover),("disabled","#111827")],
                  foreground=[("disabled","#526078")],bordercolor=[("active","#3a4c6d"),("focus",accent)])
        style.configure("Accent.TButton",background="#009f83",foreground="#f5fffd",bordercolor="#00d4ad",
                        lightcolor="#009f83",darkcolor="#009f83",padding=(10,6))
        style.map("Accent.TButton",background=[("pressed","#007963"),("active","#00b997")],bordercolor=[("focus","#54f5d5")])
        style.configure("TCheckbutton",background=bg,foreground=text,padding=(2,3),indicatorbackground=field,indicatorforeground=accent)
        style.map("TCheckbutton",background=[("active",bg)],foreground=[("disabled","#526078")],
                  indicatorbackground=[("selected",accent),("active",hover)])
        style.configure("TRadiobutton",background=bg,foreground=text,padding=(2,3),indicatorbackground=field)
        style.map("TRadiobutton",background=[("active",bg)],indicatorbackground=[("selected",accent)])
        for widget in ("TEntry","TSpinbox","TCombobox"):
            style.configure(widget,fieldbackground=field,background=field,foreground=text,insertcolor=text,
                            bordercolor=border,lightcolor=border,darkcolor=border,arrowcolor=muted,padding=5)
            style.map(widget,fieldbackground=[("readonly",field),("focus",field)],foreground=[("readonly",text)],
                      bordercolor=[("focus",accent)])
        style.configure("TLabelframe",background=panel,bordercolor=border,lightcolor=border,darkcolor=border,
                        relief="flat",borderwidth=1,padding=5)
        style.configure("TLabelframe.Label",background=panel,foreground="#c9d6ea",font=("Segoe UI",10,"bold"))
        style.configure("TNotebook",background=bg,borderwidth=0,tabmargins=(0,4,0,0))
        style.configure("TNotebook.Tab",background="#111b2e",foreground=muted,padding=(10,6),borderwidth=0)
        style.map("TNotebook.Tab",background=[("selected",panel),("active",hover)],foreground=[("selected",accent),("active",text)])
        style.configure("Treeview",background=field,fieldbackground=field,foreground=text,bordercolor=border,
                        rowheight=24,relief="flat")
        style.map("Treeview",background=[("selected","#154c52")],foreground=[("selected","#f3fffd")])
        style.configure("Treeview.Heading",background="#17233a",foreground="#cbd7e9",relief="flat",padding=(6,5),font=("Segoe UI",9,"bold"))
        style.map("Treeview.Heading",background=[("active",hover)])
        style.configure("TScrollbar",background="#1b2942",troughcolor=field,bordercolor=field,arrowcolor=muted,relief="flat")
        style.configure("TSeparator",background=border)
        style.configure("TPanedwindow",background=bg)
        style.configure("Horizontal.TScale",background=bg,troughcolor=field)
        self.option_add("*TCombobox*Listbox.background",field)
        self.option_add("*TCombobox*Listbox.foreground",text)
        self.option_add("*TCombobox*Listbox.selectBackground","#154c52")
        self.option_add("*TCombobox*Listbox.selectForeground","#f3fffd")

    def _build(self):
        top = ttk.Frame(self, padding=6); top.pack(fill="x")
        ttk.Button(top, text="DXF 열기", command=self.open_dxf).pack(side="left")
        ttk.Button(top, text="STEP 열기", command=self.open_step).pack(side="left", padx=4)
        ttk.Button(top, text="여러 파일 추가", command=self.add_multiple_files).pack(side="left", padx=4)
        ttk.Button(top, text="예제 사각형", command=self.example).pack(side="left", padx=4)
        ttk.Button(top, text="G-code 생성", command=self.make_gcode,style="Accent.TButton").pack(side="left", padx=4)
        ttk.Button(top, text="G-code 저장", command=self.save_gcode).pack(side="left")
        ttk.Button(top, text="3D 시뮬레이션", command=self.open_3d,style="Accent.TButton").pack(side="left", padx=4)
        ttk.Button(top, text="되돌리기 (Ctrl+Z)", command=self.undo).pack(side="left", padx=4)
        ttk.Button(top, text="다시 실행 (Ctrl+Y)", command=self.redo).pack(side="left", padx=2)
        ttk.Button(top, text="화면 맞춤", command=self.fit_view).pack(side="left", padx=2)
        ttk.Button(top, text="경로 안전검사", command=self.run_path_check).pack(side="left", padx=2)
        self.measure_btn=ttk.Button(top,text="거리 측정: OFF",command=self.toggle_measure)
        self.measure_btn.pack(side="left",padx=2)
        ttk.Button(top,text="측정 지우기",command=self.clear_measurement).pack(side="left",padx=2)
        self.var("show_grid",True,tk.BooleanVar)
        ttk.Checkbutton(top,text="그리드",variable=self.vars["show_grid"],command=self.redraw).pack(side="left",padx=3)
        self.status = DisplayStringVar(value="DXF 또는 STEP을 열어 주세요 (단위: mm)")
        ttk.Label(top, textvariable=self.status).pack(side="left", padx=12)

        pan = ttk.Panedwindow(self, orient="horizontal"); pan.pack(fill="both", expand=True)
        control_holder = ttk.Frame(pan); pan.add(control_holder, weight=0)
        control_canvas = tk.Canvas(control_holder, width=285,bg="#0b1220",highlightthickness=0)
        control_scroll = ttk.Scrollbar(control_holder, orient="vertical", command=control_canvas.yview)
        control_canvas.configure(yscrollcommand=control_scroll.set)
        control_scroll.pack(side="right", fill="y"); control_canvas.pack(side="left", fill="both", expand=True)
        controls = ttk.Frame(control_canvas, padding=8)
        control_window = control_canvas.create_window((0,0), window=controls, anchor="nw")
        controls.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        control_canvas.bind("<Configure>", lambda e: control_canvas.itemconfigure(control_window, width=e.width))
        control_canvas.bind("<MouseWheel>", lambda e: control_canvas.yview_scroll(int(-e.delta/120), "units"))
        center = ttk.Frame(pan); pan.add(center, weight=3)
        right = ttk.Frame(pan); pan.add(right, weight=2)

        rows = [
            ("공구 지름 (mm)", "tool_d", 2.0), ("RPM", "rpm", 22000.0),
            ("Feed XY (mm/min)", "feed", 800.0), ("Plunge (mm/min)", "plunge", 200.0),
            ("판 두께 (mm)", "stock", 3.0), ("관통 여유 (mm)", "extra", 0.1),
            ("안전 Z (mm)", "safe_z", 10.0), ("Lead in/out (mm)", "lead", 1.0),
            ("패스 수", "passes", 1),
        ]
        for r, (label, key, val) in enumerate(rows):
            ttk.Label(controls, text=label).grid(row=r, column=0, sticky="w", pady=2)
            cls = tk.IntVar if key in ("passes", "tab_count") else tk.DoubleVar
            ttk.Entry(controls, width=12, textvariable=self.var(key, val, cls)).grid(row=r, column=1, padx=5)
        r = len(rows)
        ttk.Separator(controls).grid(row=r,columnspan=2,sticky="ew",pady=(7,5));r+=1
        ttk.Label(controls,text="탭 설정 / 배치").grid(row=r,columnspan=2,sticky="w");r+=1
        for label,key,val,cls in (("탭 개수/외곽","tab_count",3,tk.IntVar),
                                  ("마이크로탭 길이 (mm)","tab_flat",1.0,tk.DoubleVar),
                                  ("탭 잔여두께 (mm)","tab_remain",0.20,tk.DoubleVar),
                                  ("탭 ramp (mm)","tab_ramp",0.35,tk.DoubleVar)):
            ttk.Label(controls,text=label).grid(row=r,column=0,sticky="w",pady=2)
            ttk.Entry(controls,width=12,textvariable=self.var(key,val,cls)).grid(row=r,column=1,padx=5);r+=1
        ttk.Label(controls,text="탭 형상").grid(row=r,column=0,sticky="w")
        self.var("tab_shape","Flat+ramp",tk.StringVar)
        ttk.Combobox(controls,width=11,state="readonly",textvariable=self.vars["tab_shape"],
                     values=("Flat+ramp","Triangle")).grid(row=r,column=1);r+=1
        ttk.Button(controls,text="자동 탭 다시 배치",command=self.apply_auto_tabs).grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        self.manual_btn=ttk.Button(controls,text="수동 탭 추가: OFF",command=self.toggle_manual)
        self.manual_btn.grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        ttk.Button(controls,text="수동 탭 모두 지우기",command=self.clear_tabs).grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        ttk.Label(controls,text="미리보기에서 외곽선을 클릭해\n수동 탭을 추가합니다.",foreground="#91a0b8").grid(row=r,columnspan=2,sticky="w",pady=5);r+=1
        ttk.Separator(controls).grid(row=r,columnspan=2,sticky="ew",pady=(5,7));r+=1
        ttk.Label(controls, text="Z축 원점").grid(row=r, column=0, sticky="w")
        self.var("z_origin", "Top", tk.StringVar)
        ttk.Combobox(controls, width=11, state="readonly", textvariable=self.vars["z_origin"],
                     values=("Top", "Bottom")).grid(row=r, column=1); r += 1
        ttk.Label(controls, text="XY 작업 원점").grid(row=r, column=0, sticky="w")
        self.var("xy_origin", "좌하단", tk.StringVar)
        ttk.Combobox(controls, width=11, state="readonly", textvariable=self.vars["xy_origin"],
                     values=("좌하단","좌상단","우상단","우하단","중앙","DXF 원점","선택점")).grid(row=r, column=1); r += 1
        self.origin_btn = ttk.Button(controls, text="DXF XY 원점 선택: OFF", command=self.toggle_origin)
        self.origin_btn.grid(row=r, columnspan=2, sticky="ew", pady=2); r += 1
        self.var("climb", True, tk.BooleanVar); self.var("full_depth", True, tk.BooleanVar)
        ttk.Checkbutton(controls, text="Climb milling", variable=self.vars["climb"]).grid(row=r, columnspan=2, sticky="w", pady=4); r += 1
        self.var("rapid_optimize",True,tk.BooleanVar)
        ttk.Checkbutton(controls,text="급속이송 최소화 (홀 묶음)",variable=self.vars["rapid_optimize"],
                        command=self.redraw).grid(row=r,columnspan=2,sticky="w");r+=1
        ttk.Checkbutton(controls, text="Full-depth 1 pass", variable=self.vars["full_depth"]).grid(row=r, columnspan=2, sticky="w"); r += 1
        self.var("m8_enabled",False,tk.BooleanVar)
        ttk.Checkbutton(controls,text="절삭유/에어 사용 (M8 ON → M9 OFF)",variable=self.vars["m8_enabled"]).grid(row=r,columnspan=2,sticky="w",pady=(2,1));r+=1
        self.var("machine_home_enabled",False,tk.BooleanVar)
        ttk.Checkbutton(controls,text="홈 사용: 종료 후 G53 주차",variable=self.vars["machine_home_enabled"]).grid(row=r,columnspan=2,sticky="w",pady=(2,1));r+=1
        for label,key,val in (("G53 주차 X","machine_park_x",10.0),
                              ("G53 주차 Y","machine_park_y",10.0),
                              ("G53 주차 Z","machine_park_z",-2.0)):
            ttk.Label(controls,text=label).grid(row=r,column=0,sticky="w",pady=2)
            ttk.Entry(controls,width=12,textvariable=self.var(key,val)).grid(row=r,column=1,padx=5);r+=1
        self.var("wall_finish",True,tk.BooleanVar)
        ttk.Checkbutton(controls,text="황삭 측면여유 → 벽면 정삭",variable=self.vars["wall_finish"],command=self.redraw).grid(row=r,columnspan=2,sticky="w",pady=(4,1));r+=1
        self.var("onion_skin_enabled",True,tk.BooleanVar)
        ttk.Checkbutton(controls,text="외곽 관통부 어니언스킨",variable=self.vars["onion_skin_enabled"],command=self.redraw).grid(row=r,columnspan=2,sticky="w");r+=1
        ttk.Label(controls,text="정삭 적용 범위").grid(row=r,column=0,sticky="w",pady=2)
        self.var("finish_scope","전체",tk.StringVar)
        ttk.Combobox(controls,width=11,state="readonly",textvariable=self.vars["finish_scope"],
                     values=("전체","외곽만","내부홀만")).grid(row=r,column=1,padx=5);r+=1
        for label,key,val in (("어니언스킨 잔여 (mm)","onion_skin",.20),
                              ("황삭 측면 여유 (mm)","finish_allowance",.12),
                              ("정삭 Feed (%)","finish_feed_pct",80.0)):
            ttk.Label(controls,text=label).grid(row=r,column=0,sticky="w",pady=2)
            ttk.Entry(controls,width=12,textvariable=self.var(key,val)).grid(row=r,column=1,padx=5);r+=1
        ttk.Label(controls, text="기존 누적거리 (m)").grid(row=r, column=0, sticky="w")
        ttk.Entry(controls, width=12, textvariable=self.var("accum_distance_m", 0.0)).grid(row=r, column=1); r += 1
        ttk.Label(controls, text="기존 누적시간 (분)").grid(row=r, column=0, sticky="w")
        ttk.Entry(controls, width=12, textvariable=self.var("accum_time_min", 0.0)).grid(row=r, column=1); r += 1
        ttk.Label(controls, text="라인 복구 허용오차 (mm)").grid(row=r, column=0, sticky="w")
        ttk.Entry(controls, width=12, textvariable=self.var("gap_tol", 0.20)).grid(row=r, column=1); r += 1
        ttk.Button(controls, text="끊긴 라인 복구", command=self.heal_lines).grid(row=r, columnspan=2, sticky="ew", pady=2); r += 1
        self.join_btn = ttk.Button(controls, text="두 라인 선택 연결: OFF", command=self.toggle_join)
        self.join_btn.grid(row=r, columnspan=2, sticky="ew", pady=2); r += 1
        ttk.Separator(controls).grid(row=r,columnspan=2,sticky="ew",pady=7);r+=1
        ttk.Label(controls,text="자동 어레이 / 판재 배치").grid(row=r,columnspan=2,sticky="w");r+=1
        for label,key,val,cls in (("판재 X (mm)","sheet_w",500.0,tk.DoubleVar),
                                  ("판재 Y (mm)","sheet_h",500.0,tk.DoubleVar),
                                  ("가공물 간격 (mm)","array_gap",3.0,tk.DoubleVar),
                                  ("가장자리 여유 (mm)","array_edge",3.0,tk.DoubleVar),
                                  ("단일 객체 수량 (0=최대)","array_qty",0,tk.IntVar)):
            ttk.Label(controls,text=label).grid(row=r,column=0,sticky="w",pady=2)
            ttk.Entry(controls,width=12,textvariable=self.var(key,val,cls)).grid(row=r,column=1,padx=5);r+=1
        self.var("array_rotate",True,tk.BooleanVar)
        ttk.Checkbutton(controls,text="90° 회전 배치 허용",variable=self.vars["array_rotate"]).grid(row=r,columnspan=2,sticky="w");r+=1
        self.var("array_auto_rotate",False,tk.BooleanVar)
        ttk.Checkbutton(controls,text="자동 회전 최적화 (5° 단위)",variable=self.vars["array_auto_rotate"]).grid(row=r,columnspan=2,sticky="w");r+=1
        ttk.Button(controls,text="판재에 자동 어레이",command=self.auto_nest).grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        self.manual_array_btn=ttk.Button(controls,text="수동 어레이 시작 (드래그 / R 회전)",command=self.toggle_manual_array)
        self.manual_array_btn.grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        ttk.Button(controls,text="어레이 해제",command=self.clear_nest).grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        ttk.Separator(controls).grid(row=r, columnspan=2, sticky="ew", pady=8); r += 1
        ttk.Label(controls, text="선택 윤곽 설정").grid(row=r, columnspan=2, sticky="w"); r += 1
        self.selection_label = DisplayStringVar(value="선택 없음")
        ttk.Label(controls, textvariable=self.selection_label, foreground="#00cfa6").grid(row=r, columnspan=2, sticky="w"); r += 1
        self.sel_depth = tk.StringVar(value="")
        ttk.Label(controls, text="깊이 mm (빈칸=관통)").grid(row=r, column=0, sticky="w")
        ttk.Entry(controls, width=12, textvariable=self.sel_depth).grid(row=r, column=1); r += 1
        self.sel_order = tk.StringVar(value="")
        ttk.Label(controls, text="가공 순번 (빈칸=자동)").grid(row=r, column=0, sticky="w")
        ttk.Entry(controls, width=12, textvariable=self.sel_order).grid(row=r, column=1); r += 1
        self.sel_role = tk.StringVar(value="auto")
        ttk.Label(controls, text="내부/외부").grid(row=r, column=0, sticky="w")
        ttk.Combobox(controls, width=11, state="readonly", textvariable=self.sel_role,
                     values=("auto", "inner", "outer")).grid(row=r, column=1); r += 1
        self.sel_tabs = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="이 윤곽에 탭 허용", variable=self.sel_tabs).grid(row=r, columnspan=2, sticky="w"); r += 1
        self.sel_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="이 윤곽 가공에 포함", variable=self.sel_enabled).grid(row=r, columnspan=2, sticky="w"); r += 1
        self.sel_safety_excluded=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text="이 윤곽 안전검사 제외",variable=self.sel_safety_excluded).grid(row=r,columnspan=2,sticky="w");r+=1
        ttk.Button(controls,text="목록 다중선택 검사 제외/복원",command=self.toggle_selected_safety).grid(row=r,columnspan=2,sticky="ew",pady=2);r+=1
        ttk.Button(controls, text="선택 설정 적용", command=self.apply_selection).grid(row=r, columnspan=2, sticky="ew")
        r += 1
        self.start_btn = ttk.Button(controls, text="절삭 시작점 선택: OFF", command=self.toggle_start)
        self.start_btn.grid(row=r, columnspan=2, sticky="ew", pady=2); r += 1
        self.var("show_toolpath", True, tk.BooleanVar)
        ttk.Checkbutton(controls, text="공구 보정경로/순서 표시", variable=self.vars["show_toolpath"],
                        command=self.redraw).grid(row=r, columnspan=2, sticky="w")
        r += 1
        self.var("auto_trim", True, tk.BooleanVar)
        ttk.Checkbutton(controls,text="꼬인 작은 루프 자동 잘라내기",variable=self.vars["auto_trim"],
                        command=self.redraw).grid(row=r,columnspan=2,sticky="w")

        self.canvas = tk.Canvas(center,bg="#08101f",highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.canvas_press)
        self.canvas.bind("<B1-Motion>", self.canvas_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_left_release)
        self.canvas.bind("<MouseWheel>", self.canvas_zoom)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        self.canvas.bind("<ButtonRelease-2>", self.pan_end)
        ttk.Label(center, text="클릭: 단일 선택  |  좌→우 드래그: 창 안 윤곽  |  우→좌 드래그: 걸친 윤곽  |  Ctrl/Shift: 선택 추가").pack(fill="x")

        right_pan = ttk.Panedwindow(right, orient="vertical"); right_pan.pack(fill="both", expand=True)
        object_frame=ttk.LabelFrame(right_pan,text="파일별 객체 / 배치 수량",padding=4)
        right_pan.add(object_frame,weight=1)
        self.object_tree=ttk.Treeview(object_frame,columns=("name","qty","contours"),show="headings",height=5,selectmode="browse")
        for col,title,width in (("name","객체",150),("qty","수량",45),("contours","윤곽",45)):
            self.object_tree.heading(col,text=title);self.object_tree.column(col,width=width,anchor="w" if col=="name" else "center",stretch=col=="name")
        object_scroll=ttk.Scrollbar(object_frame,orient="vertical",command=self.object_tree.yview)
        self.object_tree.configure(yscrollcommand=object_scroll.set);object_scroll.pack(side="right",fill="y")
        self.object_tree.pack(fill="both",expand=True);self.object_tree.bind("<<TreeviewSelect>>",self.object_tree_select)
        object_bar=ttk.Frame(object_frame);object_bar.pack(fill="x",pady=(4,0))
        ttk.Label(object_bar,text="선택 수량").pack(side="left")
        self.object_qty=tk.IntVar(value=1)
        ttk.Spinbox(object_bar,from_=0,to=1000,width=6,textvariable=self.object_qty).pack(side="left",padx=3)
        ttk.Button(object_bar,text="적용",command=self.apply_object_quantity).pack(side="left")
        ttk.Button(object_bar,text="객체 삭제",command=self.remove_selected_object).pack(side="right")
        order_frame = ttk.LabelFrame(right_pan, text="가공 순서 / 윤곽 목록", padding=4)
        right_pan.add(order_frame, weight=1)
        order_buttons=ttk.Frame(order_frame); order_buttons.pack(fill="x")
        ttk.Button(order_buttons,text="선택 윤곽만 보기",command=self.show_tree_selection).pack(side="left",fill="x",expand=True)
        ttk.Button(order_buttons,text="전체 보기",command=self.show_all_contours).pack(side="left",fill="x",expand=True,padx=(4,0))
        ttk.Button(order_frame,text="선택→PART1 / 나머지→PART2 G-code 생성",
                   command=lambda:self.make_gcode(split_selected=True),style="Accent.TButton").pack(fill="x",pady=(4,0))
        ttk.Label(order_frame,text="‘윤곽’ 셀 클릭: 자동/내부/외부 바로 선택",foreground="#91a0b8").pack(anchor="w",pady=(4,3))
        self.tree_role_var=tk.StringVar(value="자동")
        columns=("seq","manual","type","layer","depth","safety")
        self.order_tree=ttk.Treeview(order_frame,columns=columns,show="headings",selectmode="extended",height=7)
        for col,title,width in (("seq","순서",45),("manual","지정",45),("type","윤곽",55),("layer","Layer",90),("depth","깊이",55),("safety","검사",48)):
            self.order_tree.heading(col,text=title,command=lambda c=col:self.sort_order_tree(c)); self.order_tree.column(col,width=width,anchor="center",stretch=False)
        order_scroll=ttk.Scrollbar(order_frame,orient="vertical",command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=order_scroll.set)
        order_scroll.pack(side="right",fill="y"); self.order_tree.pack(fill="both",expand=True)
        self.order_tree.bind("<<TreeviewSelect>>",self.tree_select)
        self.order_tree.bind("<Button-1>",self.tree_cell_click,add="+")

        notebook = ttk.Notebook(right_pan); right_pan.add(notebook, weight=2)
        preview_tab = ttk.Frame(notebook); post_tab = ttk.Frame(notebook); help_tab = ttk.Frame(notebook); settings_tab=ttk.Frame(notebook)
        notebook.add(preview_tab, text="G-code 미리보기"); notebook.add(post_tab, text="START / END"); notebook.add(help_tab, text="Z 설정 도움말"); notebook.add(settings_tab,text="설정")
        self.text = tk.Text(preview_tab, wrap="none", font=("Consolas", 9), undo=False)
        self.text.configure(bg="#08101f",fg="#dce7f5",insertbackground="#dce7f5",selectbackground="#154c52",
                            selectforeground="#f3fffd",relief="flat",borderwidth=0,padx=8,pady=8)
        sy = ttk.Scrollbar(preview_tab, orient="vertical", command=self.text.yview)
        sx = ttk.Scrollbar(preview_tab, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x"); self.text.pack(fill="both", expand=True)
        ttk.Label(post_tab, text="START G-code (비워두면 안전 기본값 사용)").pack(anchor="w", padx=6, pady=(6,0))
        self.start_text = tk.Text(post_tab, height=11, font=("Consolas", 9))
        self.start_text.configure(bg="#08101f",fg="#dce7f5",insertbackground="#dce7f5",selectbackground="#154c52",
                                  selectforeground="#f3fffd",relief="flat",borderwidth=0,padx=8,pady=8)
        self.start_text.pack(fill="both", expand=True, padx=6)
        self.start_text.insert("1.0",DEFAULT_START_CODE)
        ttk.Label(post_tab, text="END G-code").pack(anchor="w", padx=6, pady=(6,0))
        self.end_text = tk.Text(post_tab, height=8, font=("Consolas", 9))
        self.end_text.configure(bg="#08101f",fg="#dce7f5",insertbackground="#dce7f5",selectbackground="#154c52",
                                selectforeground="#f3fffd",relief="flat",borderwidth=0,padx=8,pady=8)
        self.end_text.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.end_text.insert("1.0",DEFAULT_END_CODE)
        help_text = (
            "Z축 기준 단면도\n\n"
            "          안전 Z (공구 이동 높이)\n"
            "        ─ ─ ─ ─ ─ ─ ─ ─\n"
            "TOP 0 → ┌────────────────┐  가공물 윗면\n"
            "        │   CFRP 판 두께  │\n"
            "BOTTOM →└────────────────┘  가공물 바닥/희생판 윗면\n"
            "          ↓ 관통여유 0.1 mm\n\n"
            "Top 원점: 윗면 Z0, 아래쪽 절삭은 음수입니다.\n"
            "  3T + 관통여유 0.1 → 최종 Z-3.1\n\n"
            "Bottom 원점: 가공물 바닥 Z0입니다.\n"
            "  가공물 윗면 Z3.0, 최종 관통 Z-0.1\n"
            "  안전 Z 10.0이면 기계 좌표 Z13.0으로 이동합니다.\n\n"
            "절삭유/에어 체크 시 시작부에 M8, 종료부 M30 전에 M9가 자동 추가됩니다.\n\n"
            "기본은 홈 미사용입니다: G54 선택 → Mach3 Zero X/Y와 Z 프로브로 원점을 다시 잡습니다.\n"
            "홈 사용 체크 시 종료 후 G53 Z 주차를 먼저 실행하고, 그 다음 G53 X/Y 주차로 이동합니다.\n\n"
            "탭 잔여두께는 가공물 바닥에서 남길 두께입니다.\n"
            "어니언스킨 정삭: 외곽 황삭에서 바닥/측면 여유를 남긴 뒤\n"
            "정규 치수 전 깊이 패스로 제거하고 마이크로탭만 유지합니다.\n"
            "내부 홀·포켓은 먼저 일반 방식으로 가공합니다.\n\n"
            "여러 파일 추가: 각 파일이 별도 객체가 됩니다.\n"
            "오른쪽 객체 목록에서 파일별 수량을 지정한 뒤 자동 어레이하세요.\n"
            "수동 어레이: 수량 지정 → 수동 어레이 시작 → 객체 드래그 이동, R키 90° 회전.\n"
            "2분할 가공: 미리보기에서 PART1 윤곽을 창 선택한 뒤 2분할 생성 버튼을 누릅니다.\n"
            "저장하면 *_PART1.nc와 *_PART2.nc가 함께 생성되며, PART2 전에 엔드밀 교체 후 Z만 다시 설정합니다.\n"
            "공구·어레이·탭·원점·START/END 설정은 종료 시 자동 저장됩니다.\n"
            "\nSTEP 작업 순서:\n"
            "  1) STEP 열기 → 가공면 선택 → 선택면을 +Z/Z0 정렬\n"
            "  2) 꼭짓점 또는 원점 프리셋으로 XYZ0 설정\n"
            "  3) 필요하면 XY 끌기 및 Z축 회전 후 CAM으로 가져오기\n"
            "  STEP은 선택한 평면의 외곽·홀을 2.5D 윤곽으로 변환합니다.\n"
            "실가공 전 공중 드라이런으로 Z 방향을 반드시 확인하세요."
        )
        if CURRENT_LANGUAGE == "en":
            help_text = (
                "Z-axis reference section\n\n"
                "          Safe Z (rapid travel height)\n"
                "        - - - - - - - -\n"
                "TOP 0 -> Stock top surface\n"
                "BOTTOM -> Stock bottom / spoilboard top\n"
                "          Through allowance below the stock\n\n"
                "Top origin: stock top is Z0; downward cuts use negative Z.\n"
                "  3.0 mm stock + 0.1 mm allowance -> final Z-3.1\n\n"
                "Bottom origin: stock bottom is Z0.\n"
                "  Stock top is Z+3.0 and final through cut is Z-0.1.\n"
                "  Safe Z 10.0 moves to work Z+13.0 for 3.0 mm stock.\n\n"
                "Coolant/Air adds M8 near the start and M9 before M30.\n\n"
                "Default mode does not require homing: select G54, then set Mach3 Zero X/Y and probe Z.\n"
                "With homing enabled, the program parks G53 Z first, then G53 X/Y.\n\n"
                "Tab remaining thickness is measured upward from the stock bottom.\n"
                "Onion-skin finishing leaves bottom/wall allowance during roughing, then removes it\n"
                "with a nominal full-depth finish pass while preserving microtabs.\n\n"
                "Add Files creates one object per file. Set quantities in the object list, then array.\n"
                "For split machining, window-select PART1 contours and use the split button.\n"
                "Saving creates *_PART1.nc and *_PART2.nc. Before PART2, replace the tool and re-zero Z only.\n"
                "Tool, array, tab, origin and START/END settings are saved automatically.\n\n"
                "STEP workflow:\n"
                "  1) Open STEP, select machining faces and align the selected faces to +Z/Z0.\n"
                "  2) Set XYZ0 with a vertex or origin preset.\n"
                "  3) If needed, drag XY and rotate Z before importing into CAM.\n"
                "Always verify the Z direction with an air-cut before machining."
            )
        ttk.Label(help_tab, text=help_text, justify="left", padding=12).pack(anchor="nw")
        language_box=ttk.LabelFrame(settings_tab,text="언어 설정",padding=12);language_box.pack(fill="x",padx=10,pady=10)
        self.language_var=tk.StringVar(value="한국어" if self.language=="ko" else "English")
        ttk.Combobox(language_box,state="readonly",values=("한국어","English"),
                     textvariable=self.language_var,width=14).pack(side="left",fill="x",expand=True)
        ttk.Button(language_box,text="언어 적용",command=self.apply_language).pack(side="left",padx=(8,0))
        ttk.Label(language_box,text="재시작 후 적용됩니다.").pack(side="left",padx=8)
        font_box=ttk.LabelFrame(settings_tab,text="화면 글자 크기",padding=12); font_box.pack(fill="x",padx=10,pady=(0,10))
        ttk.Label(font_box,text="글자 크기 (8~20)").grid(row=0,column=0,sticky="w")
        self.font_size_var=tk.IntVar(value=10)
        ttk.Spinbox(font_box,from_=8,to=20,width=8,textvariable=self.font_size_var).grid(row=0,column=1,padx=8)
        ttk.Button(font_box,text="글자 크기 적용",command=self.apply_font_size).grid(row=1,column=0,columnspan=2,sticky="ew",pady=(8,0))
        ttk.Label(settings_tab,text="버튼, 입력칸, 윤곽 목록, G-code 미리보기에 적용됩니다.",padding=10).pack(anchor="w")
        update_box=ttk.LabelFrame(settings_tab,text="프로그램 업데이트",padding=12);update_box.pack(fill="x",padx=10,pady=(0,10))
        ttk.Label(update_box,text=f"현재 버전: V{APP_VERSION}\n새 버전은 다운로드 검증 후 기존 EXE를 자동 교체합니다.",justify="left").pack(anchor="w")
        ttk.Button(update_box,text="지금 업데이트 확인",command=lambda:self.start_update_check(manual=True)).pack(fill="x",pady=(8,0))

    def apply_language(self):
        selected=str(self.language_var.get()).strip()
        language="en" if selected.lower()=="english" else "ko"
        self.language=language
        try:self.save_settings()
        except (OSError,ValueError,TypeError,tk.TclError) as exc:
            messagebox.showerror("설정 오류",str(exc));return
        messagebox.showinfo("언어 설정","재시작 후 적용됩니다.")

    def config(self) -> dict:
        cfg = {k: v.get() for k, v in self.vars.items()}
        cfg["start_code"] = self.start_text.get("1.0", "end").strip()
        cfg["end_code"] = self.end_text.get("1.0", "end").strip()
        if (cfg["tool_d"] <= 0 or cfg["stock"] <= 0 or cfg["feed"] <= 0 or
                cfg["plunge"] <= 0 or cfg["rpm"] <= 0 or cfg["safe_z"] <= 0):
            raise ValueError("공구, 판 두께, RPM, Feed, Plunge, 안전 Z는 0보다 커야 합니다.")
        if cfg["passes"] < 1:
            raise ValueError("패스 수는 1 이상이어야 합니다.")
        if (cfg["lead"] < 0 or cfg["tab_count"] < 0 or cfg["tab_flat"] < 0 or
                cfg["tab_ramp"] < 0):
            raise ValueError("Lead, 탭 개수, 탭 길이와 ramp는 음수가 될 수 없습니다.")
        if cfg["extra"] < 0 or cfg["tab_remain"] < 0 or cfg["tab_remain"] >= cfg["stock"]:
            raise ValueError("관통 여유와 탭 잔여두께 값을 확인하세요.")
        if cfg["onion_skin"]<0 or cfg["onion_skin"]>=cfg["stock"] or cfg["finish_allowance"]<0:
            raise ValueError("어니언스킨 잔여량과 황삭 측면 여유 값을 확인하세요.")
        if cfg["finish_feed_pct"]<=0 or cfg["finish_feed_pct"]>100:
            raise ValueError("정삭 Feed는 0 초과 100% 이하로 설정하세요.")
        if cfg["accum_distance_m"] < 0 or cfg["accum_time_min"] < 0:
            raise ValueError("누적 거리와 누적 시간은 음수가 될 수 없습니다.")
        if cfg["gap_tol"] < 0:
            raise ValueError("라인 복구 허용오차는 음수가 될 수 없습니다.")
        if cfg["sheet_w"]<=0 or cfg["sheet_h"]<=0:
            raise ValueError("판재 X/Y 크기는 0보다 커야 합니다.")
        if cfg["array_gap"]<0 or cfg["array_edge"]<0 or cfg["array_qty"]<0:
            raise ValueError("어레이 간격, 가장자리 여유, 수량은 음수가 될 수 없습니다.")
        return cfg

    def job_signature(self,cfg:dict):
        machining_keys=("tool_d","rpm","feed","plunge","stock","extra","safe_z","lead","passes",
                        "tab_count","tab_flat","tab_remain","tab_ramp","z_origin","xy_origin","climb",
                        "full_depth","rapid_optimize","m8_enabled","wall_finish","onion_skin_enabled","finish_scope","onion_skin",
                        "finish_allowance","finish_feed_pct","tab_shape","auto_trim","accum_distance_m",
                        "accum_time_min","machine_home_enabled","machine_park_x","machine_park_y","machine_park_z",
                        "start_code","end_code")
        contour_key=tuple((tuple((round(x,7),round(y,7)) for x,y in c.points),c.closed,c.role,
                           tuple(round(s,7) for s in c.tabs),c.layer,c.target_depth,c.tabs_enabled,
                           c.tabs_cleared,c.enabled,c.safety_excluded,round(c.start_s,7),c.cut_order)
                          for c in self.contours)
        return hash((contour_key,tuple((key,repr(cfg.get(key))) for key in machining_keys)))

    def executable_dir(self)->str:
        """Return the folder the user launched the app/source from."""
        return application_directory()

    def portable_settings_path(self)->str:
        return os.path.join(self.executable_dir(),SETTINGS_FILENAME)

    def appdata_settings_path(self)->str:
        base=os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base,SETTINGS_APPDATA_DIR,SETTINGS_FILENAME)

    def settings_path(self)->str:
        """Prefer portable settings, then read the legacy AppData settings."""
        portable=self.portable_settings_path()
        if os.path.isfile(portable):return portable
        legacy=self.appdata_settings_path()
        if os.path.isfile(legacy):return legacy
        return portable

    def load_settings(self):
        try:
            loaded_path=self.settings_path()
            with open(loaded_path,"r",encoding="utf-8") as f:data=json.load(f)
            loaded_language=str(data.get("language",getattr(self,"language","ko"))).strip().lower()
            if loaded_language in SUPPORTED_LANGUAGES:self.language=loaded_language
            for key,value in data.get("vars",{}).items():
                if key in self.vars:
                    self.vars[key].set(localized_enum_value(value) if key in ("xy_origin","finish_scope") else value)
            if "start_code" in data:
                start_code=str(data["start_code"]).strip()
                if start_code in (LEGACY_DEFAULT_START_CODE,V101_DEFAULT_START_CODE,
                                  V102_DEFAULT_START_CODE,V103_DEFAULT_START_CODE):
                    start_code=DEFAULT_START_CODE
                    if abs(float(data.get("vars",{}).get("safe_z",10.0))-3.0)<EPS:self.vars["safe_z"].set(10.0)
                self.start_text.delete("1.0","end");self.start_text.insert("1.0",start_code)
            if "end_code" in data:
                end_code=str(data["end_code"]).strip()
                if end_code==LEGACY_DEFAULT_END_CODE:end_code=DEFAULT_END_CODE
                self.end_text.delete("1.0","end");self.end_text.insert("1.0",end_code)
            self.font_size_var.set(int(data.get("font_size",10)));self.apply_font_size(silent=True)
            # V1.03 and older stored settings under AppData.  On the first
            # V1.04 launch, copy those values beside the EXE when possible so
            # the application folder can be moved to another CNC computer as
            # a self-contained portable folder.
            if os.path.normcase(os.path.abspath(loaded_path))!=os.path.normcase(os.path.abspath(self.portable_settings_path())):
                try:self.save_settings()
                except (OSError,ValueError,TypeError,tk.TclError):pass
            elif getattr(self,"_language_was_prompted",False):
                try:self.save_settings()
                except (OSError,ValueError,TypeError,tk.TclError):pass
            self.status.set("저장된 설정을 불러왔습니다. DXF 또는 STEP을 열어 주세요.")
        except FileNotFoundError:
            # Create a settings file automatically on first launch.  If the
            # EXE folder is read-only, save_settings() falls back to AppData.
            try:self.save_settings()
            except (OSError,ValueError,TypeError,tk.TclError):pass
        except (OSError,ValueError,TypeError,json.JSONDecodeError,tk.TclError):
            pass

    def write_settings_file(self,path:str,data:dict):
        folder=os.path.dirname(path)
        os.makedirs(folder,exist_ok=True)
        temp_path=path+".tmp"
        try:
            with open(temp_path,"w",encoding="utf-8") as f:
                json.dump(data,f,ensure_ascii=False,indent=2)
                f.flush();os.fsync(f.fileno())
            os.replace(temp_path,path)
        except OSError:
            try:
                if os.path.isfile(temp_path):os.remove(temp_path)
            except OSError:pass
            raise

    def save_settings(self):
        data={"version":APP_VERSION,"language":getattr(self,"language","ko"),
              "vars":{k:v.get() for k,v in self.vars.items()},
              "font_size":int(self.font_size_var.get()),
              "start_code":self.start_text.get("1.0","end").strip(),
              "end_code":self.end_text.get("1.0","end").strip()}
        portable=self.portable_settings_path()
        try:
            self.write_settings_file(portable,data)
        except OSError as portable_error:
            fallback=self.appdata_settings_path()
            if os.path.normcase(os.path.abspath(fallback))==os.path.normcase(os.path.abspath(portable)):
                raise
            try:self.write_settings_file(fallback,data)
            except OSError:raise portable_error

    def on_close(self):
        try:self.save_settings()
        except (OSError,ValueError,TypeError,tk.TclError):pass
        self.destroy()

    def start_update_check(self,manual=False):
        if not getattr(sys,"frozen",False):
            if manual:messagebox.showinfo("업데이트", "업데이트 확인은 배포용 EXE에서 작동합니다.")
            return
        if self._update_check_running or self._update_download_running:
            if manual:messagebox.showinfo("업데이트", "이미 업데이트를 확인하거나 다운로드하고 있습니다.")
            return
        self._update_check_running=True;self._update_manual=bool(manual)
        if manual:self.status.set("최신 버전 확인 중...")
        def worker():
            try:self._update_queue.put(("manifest",fetch_update_manifest(),bool(manual)))
            except Exception as exc:self._update_queue.put(("check_error",str(exc),bool(manual)))
        threading.Thread(target=worker,daemon=True).start();self.after(250,self._poll_update_events)

    def _poll_update_events(self):
        try:
            while True:
                kind,payload,manual=self._update_queue.get_nowait()
                if kind=="manifest":
                    self._update_check_running=False
                    if payload is None:
                        if manual:messagebox.showinfo("업데이트",f"현재 V{APP_VERSION}이 최신 버전입니다.")
                    else:self._offer_update(payload)
                elif kind=="check_error":
                    self._update_check_running=False
                    if manual:messagebox.showwarning("업데이트 확인 실패",f"최신 버전을 확인하지 못했습니다.\n\n{payload}")
                elif kind=="downloaded":
                    self._update_download_running=False
                    if self._update_progress:self._update_progress.set_progress(100,"업데이트 다운로드 완료");self._update_progress.close();self._update_progress=None
                    self._launch_update_replacement(payload)
                elif kind=="download_error":
                    self._update_download_running=False
                    if self._update_progress:self._update_progress.close();self._update_progress=None
                    messagebox.showerror("업데이트 실패",f"새 버전을 내려받거나 검증하지 못했습니다.\n기존 프로그램은 변경되지 않았습니다.\n\n{payload}")
        except queue.Empty:pass
        if (self._update_check_running or self._update_download_running) and self.winfo_exists():self.after(250,self._poll_update_events)

    def _offer_update(self,info:dict):
        note=f"\n\n변경 내용:\n{info['message']}" if info.get("message") else ""
        if messagebox.askyesno("새 버전 발견",
                               f"CFRP Router CAM V{info['version']}이 있습니다.{note}\n\n"
                               "지금 업데이트하면 새 EXE를 검증한 뒤 현재 프로그램을 종료하고 기존 EXE를 자동 교체합니다.\n"
                               "업데이트할까요?"):
            self._download_update(info)

    def _download_update(self,info:dict):
        folder=self.executable_dir();destination=os.path.join(folder,UPDATE_TEMP_FILENAME)
        self._update_download_running=True
        self._update_progress=ProgressDialog(self,"프로그램 업데이트")
        self._update_progress.set_progress(10,f"V{info['version']} 다운로드·검증 중")
        def worker():
            try:
                download_verified_update(info["download_url"],destination,info["sha256"])
                self._update_queue.put(("downloaded",(destination,info),False))
            except Exception as exc:self._update_queue.put(("download_error",str(exc),False))
        threading.Thread(target=worker,daemon=True).start();self.after(250,self._poll_update_events)

    def _launch_update_replacement(self,payload):
        source,info=payload;target=os.path.abspath(sys.executable)
        try:
            self.save_settings()
            subprocess.Popen([source,"--apply-update",target,str(os.getpid()),info["sha256"]],
                             cwd=os.path.dirname(target),close_fds=True)
        except Exception as exc:
            messagebox.showerror("업데이트 실행 실패",f"기존 프로그램은 변경되지 않았습니다.\n\n{exc}")
            return
        self.destroy()

    def _history_state(self)->dict:
        """Capture geometry together with the array state that owns it."""
        try:xy_origin=self.vars["xy_origin"].get()
        except (KeyError,tk.TclError):xy_origin=None
        return {"contours":copy.deepcopy(self.contours),
                "part_objects":copy.deepcopy(self.part_objects),
                "next_object_id":self.next_object_id,
                "nest_source":copy.deepcopy(self.nest_source),
                "nest_active":self.nest_active,"sheet_size":self.sheet_size,
                "filename":self.filename,"xy_origin":xy_origin}

    def _restore_history_state(self,state:dict):
        self.contours=copy.deepcopy(state["contours"])
        self.part_objects=copy.deepcopy(state.get("part_objects",self.part_objects))
        self.next_object_id=state.get("next_object_id",self.next_object_id)
        self.nest_source=copy.deepcopy(state.get("nest_source"))
        self.nest_active=bool(state.get("nest_active",False))
        self.sheet_size=state.get("sheet_size")
        self.filename=state.get("filename",self.filename)
        if state.get("xy_origin") is not None:self.vars["xy_origin"].set(state["xy_origin"])

    def push_undo(self, action: str):
        self.undo_stack.append((action,self._history_state()))
        self.redo_stack.clear()
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

    def undo(self, event=None):
        if not self.undo_stack:
            self.status.set("되돌릴 작업이 없습니다.")
            return "break"
        action, state = self.undo_stack.pop()
        self.redo_stack.append((action,self._history_state()))
        if len(self.redo_stack)>30:self.redo_stack.pop(0)
        self._restore_history_state(state)
        self.selected = None;self.selected_contours=[]; self.join_first = None; self.view_only=None
        self.selection_label.set("선택 없음")
        self.view_initialized=False;self.preview_cache.clear();self.collision_cache_key=None
        self.redraw();self.refresh_object_tree()
        self.status.set(f"되돌림 완료: {action}")
        return "break"

    def redo(self,event=None):
        if not self.redo_stack:
            self.status.set("다시 실행할 작업이 없습니다.")
            return "break"
        action,state=self.redo_stack.pop()
        self.undo_stack.append((action,self._history_state()))
        if len(self.undo_stack)>30:self.undo_stack.pop(0)
        self._restore_history_state(state)
        self.selected=None;self.selected_contours=[];self.join_first=None;self.view_only=None
        self.selection_label.set("선택 없음")
        self.view_initialized=False;self.preview_cache.clear();self.collision_cache_key=None
        self.redraw();self.refresh_object_tree();self.status.set(f"다시 실행 완료: {action}")
        return "break"

    def make_part_object(self,contours:Sequence[Contour],filename:str,stock:Optional[float]=None,
                         display_name:Optional[str]=None,layout_group:str="")->PartObject:
        group=copy.deepcopy(list(contours));classify_contours(group)
        object_id=self.next_object_id;self.next_object_id+=1
        name=display_name or os.path.splitext(os.path.basename(filename))[0] or f"객체 {object_id}"
        for c in group:
            if c.closed and c.forced_role=="auto":c.forced_role=c.role
            c.object_id=object_id;c.object_name=name;c.instance_id=1
        normalized,_,_,origin=normalized_contour_group(group)
        for c in normalized:c.object_id=object_id;c.object_name=name;c.instance_id=1
        return PartObject(object_id,name,normalized,1,filename,stock,origin,True,False,layout_group)

    def reset_job_view(self):
        self.nest_source=None;self.nest_active=False;self.sheet_size=None;self.preview_cache.clear()
        self.manual_array_mode=False;self.manual_array_selected=None;self.manual_array_drag=None
        if hasattr(self,"manual_array_btn"):self.manual_array_btn.configure(text="수동 어레이 시작 (드래그 / R 회전)")
        self.measure_start=None;self.measurement=None;self.undo_stack.clear();self.redo_stack.clear();self.view_only=None
        self.selected=None;self.selected_contours=[];self.view_initialized=False

    def rebuild_object_preview(self):
        nested=[]
        try:gap=max(10.0,float(self.vars["array_gap"].get()))
        except (KeyError,ValueError,tk.TclError):gap=10.0
        offsets=part_preview_offsets(self.part_objects,gap)
        for part in self.part_objects:
            group=copy.deepcopy(part.contours)
            dx,dy=offsets.get(part.object_id,part.display_offset)
            for c in group:
                c.points=[(x+dx,y+dy) for x,y in c.points]
                c.bridges=[((a[0]+dx,a[1]+dy),(b[0]+dx,b[1]+dy)) for a,b in c.bridges]
                c.object_id=part.object_id;c.object_name=part.name;c.instance_id=1;c.cut_order=None
            nested.extend(group)
        self.contours=nested;classify_contours(self.contours);self.preview_cache.clear()
        self.sheet_size=None;self.nest_active=False;self.nest_source=None;self.view_only=None
        self.manual_array_mode=False;self.manual_array_selected=None;self.manual_array_drag=None
        if hasattr(self,"manual_array_btn"):self.manual_array_btn.configure(text="수동 어레이 시작 (드래그 / R 회전)")
        self.selected=None;self.selected_contours=[];self.view_initialized=False;self.measure_start=None;self.measurement=None
        # Rebuilding the object preview (for example after adding a file or
        # undoing an array) must not replace user-positioned or explicitly
        # cleared tabs.  Only fill tabs that have never been decided.
        self.apply_auto_tabs(record=False,preserve_existing=True)

    def set_single_part(self,contours:Sequence[Contour],filename:str,stock:Optional[float]=None,
                        display_name:Optional[str]=None,layout_group:str=""):
        self.part_objects=[];self.next_object_id=1
        self.part_objects.append(self.make_part_object(contours,filename,stock,display_name,layout_group));self.filename=filename
        if stock is not None:self.vars["stock"].set(round(stock,4))
        self.reset_job_view();self.rebuild_object_preview();self.refresh_object_tree()

    def add_part_object(self,contours:Sequence[Contour],filename:str,stock:Optional[float]=None,
                        display_name:Optional[str]=None,layout_group:str=""):
        if self.nest_active:self.rebuild_object_preview()
        elif self.part_objects:self.sync_part_sources_from_preview()
        self.part_objects.append(self.make_part_object(contours,filename,stock,display_name,layout_group))
        if len(self.part_objects)==1:self.filename=filename
        else:self.filename="multi_job"
        if stock is not None and len(self.part_objects)==1:self.vars["stock"].set(round(stock,4))
        self.rebuild_object_preview();self.refresh_object_tree()

    def sync_part_sources_from_preview(self):
        if self.nest_active:return
        classify_contours(self.contours)
        for part in self.part_objects:
            group=[copy.deepcopy(c) for c in self.contours if c.object_id==part.object_id and c.instance_id in (0,1)]
            if not group:continue
            for c in group:
                if c.closed and c.forced_role=="auto":c.forced_role=c.role
                c.object_name=part.name;c.instance_id=1
            normalized,_,_,origin=normalized_contour_group(group)
            part.contours=normalized;part.display_offset=origin

    def refresh_object_tree(self):
        if not hasattr(self,"object_tree"):return
        selected=self.object_tree.selection();selected_id=selected[0] if selected else None
        self.object_tree.delete(*self.object_tree.get_children())
        for part in self.part_objects:
            iid=f"o{part.object_id}";tag=f"obj{part.object_id}"
            self.object_tree.insert("","end",iid=iid,values=(part.name,part.quantity,len(part.contours)),tags=(tag,))
            self.object_tree.tag_configure(tag,foreground=OBJECT_TREE_COLORS[(part.object_id-1)%len(OBJECT_TREE_COLORS)])
        if selected_id and self.object_tree.exists(selected_id):self.object_tree.selection_set(selected_id)

    def object_tree_select(self,event=None):
        items=self.object_tree.selection()
        if not items:return
        object_id=int(items[0][1:]);part=next((p for p in self.part_objects if p.object_id==object_id),None)
        if part:self.object_qty.set(part.quantity)

    def apply_object_quantity(self):
        items=self.object_tree.selection()
        if not items:messagebox.showinfo("객체 수량","객체 목록에서 파일을 선택하세요.");return
        try:quantity=int(self.object_qty.get())
        except (ValueError,tk.TclError):quantity=-1
        if quantity<0 or quantity>1000:messagebox.showerror("객체 수량","수량은 0~1000으로 입력하세요.");return
        object_id=int(items[0][1:]);part=next((p for p in self.part_objects if p.object_id==object_id),None)
        if part:
            part.quantity=quantity;part.quantity_set=True;self.refresh_object_tree();self.object_tree.selection_set(f"o{object_id}")
            self.status.set(f"{part.name} 배치 수량: {quantity}개")

    def remove_selected_object(self):
        items=self.object_tree.selection()
        if not items:messagebox.showinfo("객체 삭제","객체 목록에서 파일을 선택하세요.");return
        object_id=int(items[0][1:]);part=next((p for p in self.part_objects if p.object_id==object_id),None)
        if part is None:return
        self.part_objects=[p for p in self.part_objects if p.object_id!=object_id]
        self.filename="multi_job" if len(self.part_objects)>1 else (self.part_objects[0].source_path if self.part_objects else "")
        self.rebuild_object_preview();self.refresh_object_tree();self.status.set(f"객체 삭제: {part.name}")

    def add_multiple_files(self):
        files=filedialog.askopenfilenames(title="DXF / STEP 여러 파일 추가",
            filetypes=[("CAD 파일","*.dxf *.step *.stp"),("DXF","*.dxf"),("STEP","*.step *.stp"),("All","*.*")])
        if not files:return
        self.pending_imports.extend(files);self.process_next_import()

    def process_next_import(self):
        if not self.pending_imports:
            self.status.set(f"여러 파일 가져오기 완료 | 객체 {len(self.part_objects)}개")
            return
        fn=self.pending_imports.pop(0);ext=os.path.splitext(fn)[1].lower()
        try:
            if ext==".dxf":
                cfg=self.config();contours=dxf_to_contours(fn,gap_tol=0.0)
                if not contours:raise ValueError("지원되는 2D 형상을 찾지 못했습니다.")
                heal_open_contours(contours,cfg["gap_tol"]);self.add_part_object(contours,fn)
                self.after(10,self.process_next_import);return
            if ext in (".step",".stp"):
                self.status.set(f"STEP 읽는 중: {os.path.basename(fn)}");self.update_idletasks()
                progress=ProgressDialog(self,"STEP 불러오기")
                try:model=load_step_model(fn,progress=progress.set_progress)
                finally:progress.close()
                def accepted(contours,filename,face_number,matrix,stock,depth_count,added_count):
                    before=len(self.part_objects)
                    parts=split_step_contour_parts(contours)
                    base_name=os.path.splitext(os.path.basename(filename))[0]
                    layout_group=os.path.normcase(os.path.abspath(filename))
                    for part_number,group in parts:
                        display_name=base_name if len(parts)==1 else f"{base_name}_P{part_number}"
                        self.add_part_object(group,filename,stock,display_name,layout_group)
                    if before==0:self.vars["stock"].set(round(stock,4))
                    self.after(10,self.process_next_import)
                StepSetupDialog(self,model,accepted,on_cancel=lambda:self.after(10,self.process_next_import))
                self.status.set(f"{os.path.basename(fn)} | 작업좌표계를 설정하세요")
                return
            raise ValueError("DXF 또는 STEP 파일만 추가할 수 있습니다.")
        except Exception as exc:
            messagebox.showerror("여러 파일 가져오기",f"{os.path.basename(fn)}\n{exc}")
            self.after(10,self.process_next_import)

    def open_dxf(self):
        fn = filedialog.askopenfilename(title="2D DXF 선택", filetypes=[("DXF", "*.dxf"), ("All", "*.*")])
        if not fn: return
        try:
            cfg = self.config()
            contours = dxf_to_contours(fn, gap_tol=0.0)
            if not contours: raise ValueError("지원되는 2D 형상을 찾지 못했습니다.")
            repaired = heal_open_contours(contours, cfg["gap_tol"]);self.set_single_part(contours,fn)
            layered = sum(c.target_depth is not None for c in contours)
            self.status.set(f"{os.path.basename(fn)} | 윤곽 {len(self.contours)}개 | 자동복구 {repaired}곳 | 레이어 깊이 {layered}개")
        except Exception as exc:
            messagebox.showerror("DXF 오류", str(exc))

    def open_step(self):
        fn=filedialog.askopenfilename(title="STEP 솔리드 선택",filetypes=[("STEP","*.step *.stp"),("All","*.*")])
        if not fn:return
        try:
            self.status.set("STEP 형상 읽는 중...");self.update_idletasks()
            progress=ProgressDialog(self,"STEP 불러오기")
            try:model=load_step_model(fn,progress=progress.set_progress)
            finally:progress.close()
            StepSetupDialog(self,model,self.accept_step_contours)
            self.status.set(f"{os.path.basename(fn)} | STEP 면 {len(model.faces)}개 | 작업좌표계를 설정하세요")
        except Exception as exc:
            self.status.set("STEP 불러오기 실패")
            messagebox.showerror("STEP 오류",str(exc))

    def accept_step_contours(self,contours:List[Contour],filename:str,face_number:int,matrix:List[List[float]],
                             stock:float,depth_count:int,added_count:int):
        parts=split_step_contour_parts(contours)
        base_name=os.path.splitext(os.path.basename(filename))[0]
        layout_group=os.path.normcase(os.path.abspath(filename))
        first_number,first_group=parts[0]
        first_name=base_name if len(parts)==1 else f"{base_name}_P{first_number}"
        self.set_single_part(first_group,filename,stock,first_name,layout_group)
        for part_number,group in parts[1:]:
            self.add_part_object(group,filename,stock,f"{base_name}_P{part_number}",layout_group)
        self.step_matrix=matrix
        self.vars["xy_origin"].set("선택점")
        self.vars["z_origin"].set("Top")
        self.status.set(f"{os.path.basename(filename)} | STEP 객체 {len(parts)}개 · 윤곽 {len(self.contours)}개 (깊이 {depth_count}, 카운터보어 추가홀 {added_count}) | 판두께 {stock:.3f} mm")

    def example(self):
        outer = Contour([(0,0),(80,0),(80,25),(0,25)], True, "example outer")
        hole = Contour([(15,8),(22,8),(22,15),(15,15)], True, "example hole")
        circle = [(60+4*math.cos(2*math.pi*i/40),12.5+4*math.sin(2*math.pi*i/40)) for i in range(40)]
        self.set_single_part([outer,hole,Contour(circle,True,"example circle")],"example")
        self.status.set("예제: 80 × 25 mm, 내부 형상 2개")

    def auto_nest(self):
        if not self.contours:
            messagebox.showinfo("자동 어레이","먼저 DXF 또는 STEP 형상을 가져오세요.");return
        try:cfg=self.config()
        except Exception as exc:messagebox.showerror("자동 어레이",str(exc));return
        progress=ProgressDialog(self,"자동 어레이")
        try:
            progress.set_progress(3,"배치 대상 분석 중")
            if not self.part_objects:
                legacy=copy.deepcopy(self.contours);self.part_objects=[self.make_part_object(legacy,self.filename or "객체 1")]
            self.sync_part_sources_from_preview()
            if cfg["array_auto_rotate"]:angles=range(0,180,5)
            elif cfg["array_rotate"]:angles=(0,90)
            else:angles=(0,)
            parts=[p for p in self.part_objects if p.enabled]
            if len(parts)==1:
                part=parts[0];quantity=part.quantity if part.quantity_set else int(cfg["array_qty"])
                if part.quantity_set and quantity<=0:raise ValueError("선택 객체의 배치 수량이 0입니다.")
                progress.set_progress(10,"회전별 크기 계산 중")
                orientations=[(angle,*rotated_group_size(part.contours,angle)) for angle in angles]
                sizes={a:(w,h) for a,w,h in orientations}
                orientation_sets=[orientations]
                if cfg["array_auto_rotate"]:
                    axial=[q for q in orientations if abs(q[0]%90)<1e-6]
                    if axial:orientation_sets.append(axial)
                raw_candidates=[]
                for candidate_index,candidate_orientations in enumerate(orientation_sets,1):
                    progress.set_progress(15+35*candidate_index/len(orientation_sets),
                                           f"배치 패턴 계산 {candidate_index}/{len(orientation_sets)}")
                    raw_candidates.append(best_oriented_array_layout(
                        cfg["sheet_w"],cfg["sheet_h"],cfg["array_gap"],cfg["array_edge"],
                        candidate_orientations,quantity))
                def layout_score(layout):
                    used_width=max((x+sizes[a][0] for a,x,y in layout),default=cfg["array_edge"])-cfg["array_edge"]
                    used_height=max((y+sizes[a][1] for a,x,y in layout),default=cfg["array_edge"])-cfg["array_edge"]
                    total_box=sum(sizes[a][0]*sizes[a][1] for a,x,y in layout)
                    angled=sum(abs(a%90)>1e-6 for a,x,y in layout)
                    return (len(layout),-used_width*used_height,-max(used_width,used_height),
                            -used_height,-used_width,-total_box,-angled)
                raw=max(raw_candidates,key=layout_score)
                placements=[NestPlacement(part.object_id,i,a,x,y,*sizes[a]) for i,(a,x,y) in enumerate(raw,1)]
                placed_counts={part.object_id:len(placements)}
                requested={part.object_id:(quantity if quantity>0 else len(placements))}
            else:
                requested={p.object_id:p.quantity for p in parts};total_requested=sum(requested.values())
                if total_requested<=0:raise ValueError("객체별 배치 수량을 1개 이상 지정하세요.")
                if total_requested>1000:raise ValueError(f"요청 수량이 {total_requested}개입니다. 합계를 1000 이하로 지정하세요.")
                placements,placed_counts=best_mixed_nesting(
                    parts,cfg["sheet_w"],cfg["sheet_h"],cfg["array_gap"],cfg["array_edge"],tuple(angles),
                    lambda value,message:progress.set_progress(10+value*.55,message))
            if not placements:raise ValueError("설정한 판재와 여유 안에 가공물이 들어가지 않습니다.")
            if len(placements)>1000:raise ValueError(f"예상 수량이 {len(placements)}개입니다. 수량을 1000 이하로 지정하세요.")
            part_by_id={p.object_id:p for p in parts}
            progress.set_progress(70,"회전된 가공물 준비 중")
            templates={(p.object_id,p.angle):oriented_contour_group(part_by_id[p.object_id].contours,p.angle)[0] for p in placements}
        except Exception as exc:
            progress.close();messagebox.showerror("자동 어레이",str(exc));return
        self.push_undo("자동 어레이")
        if not self.nest_active:self.nest_source=copy.deepcopy(self.contours)
        nested=[]
        for placement_index,placement in enumerate(placements,1):
            progress.set_progress(72+20*placement_index/max(len(placements),1),
                                  f"가공물 배치 {placement_index}/{len(placements)}")
            part=part_by_id[placement.object_id];group=copy.deepcopy(templates[(placement.object_id,placement.angle)])
            for c in group:
                c.points=[(x+placement.x,y+placement.y) for x,y in c.points]
                c.bridges=[((a[0]+placement.x,a[1]+placement.y),(b[0]+placement.x,b[1]+placement.y)) for a,b in c.bridges]
                c.cut_order=None;c.object_id=part.object_id;c.object_name=part.name;c.instance_id=placement.instance_id
                c.name=f"{c.name} · {part.name} #{placement.instance_id}"
            nested.extend(group)
        # Every template was classified before duplication.  Reclassifying all
        # copies here is quadratic and can freeze large manual arrays.
        self.contours=nested;self.nest_active=True
        self.sheet_size=(float(cfg["sheet_w"]),float(cfg["sheet_h"]));self.preview_cache.clear()
        self.measure_start=None;self.measurement=None
        self.view_only=None;self.selected=None;self.selected_contours=[];self.view_initialized=False;self.vars["xy_origin"].set(localized_enum_value("좌하단"))
        progress.set_progress(95,"기존 마이크로탭 유지 중")
        # Rotation and translation preserve path distance, so copied manual,
        # automatic, and intentionally-cleared tab states remain valid.
        self.redraw()
        used_angles=sorted({round(p.angle,3) for p in placements})
        angle_text=", ".join(f"{a:g}°" for a in used_angles)
        mode="자동 회전" if cfg["array_auto_rotate"] else ("0°/90°" if cfg["array_rotate"] else "회전 없음")
        count_text=", ".join(f"{part_by_id[oid].name} {placed_counts.get(oid,0)}/{qty}" for oid,qty in requested.items())
        self.status.set(f"자동 어레이 완료 | {len(placements)}개 | {count_text} | {mode} {angle_text} | 간격 {cfg['array_gap']:g} mm")
        progress.set_progress(100,"자동 어레이 완료");progress.close()
        missing=[f"{part_by_id[oid].name}: {placed_counts.get(oid,0)}/{qty}개" for oid,qty in requested.items() if placed_counts.get(oid,0)<qty]
        if missing:messagebox.showwarning("판재 공간 부족","다음 객체는 요청 수량을 모두 배치하지 못했습니다.\n\n"+"\n".join(missing))

    def create_manual_array(self,cfg:dict)->int:
        if not self.part_objects:
            legacy=copy.deepcopy(self.contours);self.part_objects=[self.make_part_object(legacy,self.filename or "객체 1")]
        self.sync_part_sources_from_preview()
        parts=[p for p in self.part_objects if p.enabled]
        if not parts:raise ValueError("배치할 객체가 없습니다.")
        quantities={}
        for part in parts:
            if len(parts)==1 and not part.quantity_set:
                quantity=int(cfg.get("array_qty",0)) or max(1,part.quantity)
            else:quantity=part.quantity
            quantities[part.object_id]=max(0,int(quantity))
        total=sum(quantities.values())
        if total<=0:raise ValueError("객체별 배치 수량을 1개 이상 지정하세요.")
        if total>1000:raise ValueError(f"요청 수량이 {total}개입니다. 합계를 1000 이하로 지정하세요.")
        if not self.nest_active:self.nest_source=copy.deepcopy(self.contours)
        edge=float(cfg["array_edge"]);gap=float(cfg["array_gap"]);sheet_w=float(cfg["sheet_w"])
        x=y=edge;row_h=0.0;nested=[]
        for part in parts:
            template,w,h=oriented_contour_group(part.contours,0)
            for instance_id in range(1,quantities[part.object_id]+1):
                if x>edge+EPS and x+w>sheet_w-edge+EPS:
                    x=edge;y+=row_h+gap;row_h=0.0
                group=copy.deepcopy(template)
                for c in group:
                    c.points=[(px+x,py+y) for px,py in c.points]
                    c.bridges=[((a[0]+x,a[1]+y),(b[0]+x,b[1]+y)) for a,b in c.bridges]
                    c.cut_order=None;c.object_id=part.object_id;c.object_name=part.name;c.instance_id=instance_id
                    c.name=f"{c.name} · {part.name} #{instance_id}"
                nested.extend(group);x+=w+gap;row_h=max(row_h,h)
        # Each source part is already classified before duplication. Re-running
        # nesting classification across every copy is quadratic and made large
        # manual arrays appear to freeze when editing started.
        self.contours=nested;self.nest_active=True
        self.sheet_size=(float(cfg["sheet_w"]),float(cfg["sheet_h"]));self.preview_cache.clear();self.collision_cache_key=None
        self.view_only=None;self.selected=None;self.selected_contours=[];self.view_initialized=False;self.vars["xy_origin"].set(localized_enum_value("좌하단"))
        return total

    def manual_array_layout_issues(self)->Tuple[int,int]:
        boxes=sorted(contour_group_bounds_map(self.contours).items())
        outside=0
        try:
            edge=max(0.0,float(self.vars["array_edge"].get()))
            gap=max(0.0,float(self.vars["array_gap"].get()))
        except (KeyError,ValueError,tk.TclError):edge=gap=0.0
        if self.sheet_size:
            sw,sh=self.sheet_size
            outside=sum(x0<edge-EPS or y0<edge-EPS or x1>sw-edge+EPS or y1>sh-edge+EPS
                        for _,(x0,y0,x1,y1) in boxes)
        overlap=0
        for i,(_,a) in enumerate(boxes):
            for _,b in boxes[i+1:]:
                # Count both overlaps and boxes closer than the configured
                # clearance so a manual layout cannot silently violate the
                # same spacing used by automatic nesting.
                if (a[0]<b[2]+gap-EPS and b[0]<a[2]+gap-EPS and
                        a[1]<b[3]+gap-EPS and b[1]<a[3]+gap-EPS):overlap+=1
        return outside,overlap

    def toggle_manual_array(self):
        if self.manual_array_mode:
            self.manual_array_mode=False;self.manual_array_drag=None;self.manual_array_selected=None
            self.manual_array_btn.configure(text="수동 어레이 편집 (드래그 / R 회전)")
            outside,overlap=self.manual_array_layout_issues();self.redraw()
            self.status.set(f"수동 배치 완료 | 가장자리 여유 위반 {outside}개 | 간격/겹침 위반 {overlap}쌍")
            if outside or overlap:
                messagebox.showwarning("수동 배치 확인",
                    f"가장자리 여유 위반 {outside}개\n간격 또는 겹침 위반 {overlap}쌍\n\n"
                    "배치를 다시 확인한 뒤 G-code를 생성하세요.")
            return
        if not self.contours:
            messagebox.showinfo("수동 어레이","먼저 DXF 또는 STEP 형상을 가져오세요.");return
        try:
            cfg=self.config()
            total=len({contour_group_key(c) for c in self.contours if c.object_id}) if self.nest_active else self.create_manual_array(cfg)
        except Exception as exc:
            messagebox.showerror("수동 어레이",str(exc));return
        self.manual_array_mode=True;self.manual_array_selected=None;self.manual_array_drag=None
        self.manual_mode=False;self.join_mode=False;self.join_first=None;self.start_mode=False;self.origin_mode=False;self.measure_mode=False
        self.manual_btn.configure(text="수동 탭 추가: OFF");self.join_btn.configure(text="두 라인 선택 연결: OFF")
        self.start_btn.configure(text="절삭 시작점 선택: OFF");self.origin_btn.configure(text="DXF XY 원점 선택: OFF");self.measure_btn.configure(text="거리 측정: OFF")
        self.manual_array_btn.configure(text="수동 배치 완료")
        self.redraw(refresh_tree=False);self.status.set(f"수동 어레이 편집 ON | 객체 클릭 후 드래그 이동 · R키 90° 회전 | 배치 {total}개")

    def manual_group_tag(self,key:Tuple[int,int])->str:
        return f"manual_group_{key[0]}_{key[1]}"

    def manual_group_at(self,p:Point)->Optional[Tuple[int,int]]:
        visible=self.visible_contours();bounds_by_key=contour_group_bounds_map(visible)
        inside=[]
        for key,b in bounds_by_key.items():
            if b[0]-EPS<=p[0]<=b[2]+EPS and b[1]-EPS<=p[1]<=b[3]+EPS:
                inside.append(((b[2]-b[0])*(b[3]-b[1]),key))
        if inside:return min(inside,key=lambda item:item[0])[1]
        best=None
        for c in visible:
            if not c.object_id:continue
            d,_=nearest_path_distance(c.points,p,c.closed)
            if best is None or d<best[0]:best=(d,contour_group_key(c))
        return best[1] if best and best[0]*self.view[0]<=15 else None

    def rotate_manual_array_selected(self,event=None):
        if not self.manual_array_mode or self.manual_array_selected is None:return None
        if event is not None and event.widget.winfo_class() in ("Entry","TEntry","Text","TCombobox","TSpinbox"):return None
        self.push_undo("수동 배치 90° 회전")
        rotate_contour_group(self.contours,self.manual_array_selected,90.0)
        self.preview_cache.clear();self.collision_cache_key=None;self.redraw(refresh_tree=False)
        self.status.set(f"선택 객체 #{self.manual_array_selected[1]} 90° 회전")
        return "break"

    def clear_nest(self):
        if not self.nest_active:
            messagebox.showinfo("어레이","해제할 어레이가 없습니다.");return
        self.push_undo("어레이 해제")
        self.rebuild_object_preview();self.status.set("어레이를 해제했습니다. 파일별 객체 보기로 복원했습니다.")

    def apply_auto_tabs(self, record=True, preserve_existing=False):
        try: cfg = self.config()
        except Exception as exc: messagebox.showerror("설정 오류", str(exc)); return
        if record and self.contours:
            self.push_undo("자동 탭 배치")
        classify_contours(self.contours)
        for c in self.contours:
            if preserve_existing and (c.tabs or c.tabs_cleared):continue
            c.tabs = auto_tabs(c, cfg["tab_count"], cfg["tab_flat"], cfg["tab_ramp"]) if c.role == "outer" and c.tabs_enabled else []
            c.tabs_cleared = False
        self.redraw()

    def clear_tabs(self):
        if self.contours:
            self.push_undo("탭 모두 지우기")
        for c in self.contours:
            c.tabs = []
            c.tabs_cleared = True
        self.redraw()

    def heal_lines(self):
        if not self.contours:
            messagebox.showinfo("안내", "먼저 DXF를 열어 주세요.")
            return
        try:
            self.push_undo("끊긴 라인 복구")
            repaired = heal_open_contours(self.contours, self.config()["gap_tol"])
            self.apply_auto_tabs(record=False)
            still_open = sum(not c.closed for c in self.contours)
            self.status.set(f"라인 복구 {repaired}곳 | 남은 열린 선 {still_open}개")
            if repaired == 0:
                messagebox.showinfo("라인 복구", "현재 허용오차 안에서 연결할 끝점을 찾지 못했습니다.")
        except Exception as exc:
            messagebox.showerror("라인 복구 오류", str(exc))

    def apply_selection(self):
        if self.selected is None:
            messagebox.showinfo("안내", "미리보기에서 윤곽선을 먼저 클릭하세요.")
            return
        raw = self.sel_depth.get().strip()
        raw_order = self.sel_order.get().strip()
        try:
            new_depth = None if not raw else abs(float(raw))
            if new_depth is not None and new_depth <= 0:
                raise ValueError
            new_order = None if not raw_order else int(raw_order)
            if new_order is not None and new_order < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("설정 오류", "깊이는 0보다 큰 숫자, 가공 순번은 1 이상의 정수로 입력하세요.")
            return
        self.push_undo("선택 윤곽 설정")
        self.selected.target_depth = new_depth
        self.selected.cut_order = new_order
        self.selected.forced_role = self.sel_role.get()
        self.selected.tabs_enabled = self.sel_tabs.get()
        self.selected.enabled = self.sel_enabled.get()
        self.selected.safety_excluded=self.sel_safety_excluded.get()
        classify_contours(self.contours)
        if not self.selected.tabs_enabled or self.selected.role!="outer":
            self.selected.tabs = []
            if self.selected.role!="outer":self.selected.tabs_cleared=False
        order_text=str(self.selected.cut_order) if self.selected.cut_order is not None else "자동"
        self.selection_label.set(f"{self.selected.layer} | {self.selected.role} | 순번 {order_text} | 깊이 " +
                                 (f"{self.selected.target_depth:g}" if self.selected.target_depth else "관통"))
        self.redraw()

    def toggle_manual(self):
        self.manual_mode = not self.manual_mode
        if self.manual_mode:
            self.join_mode = False; self.join_first = None
            self.join_btn.configure(text="두 라인 선택 연결: OFF")
            self.origin_mode = False; self.origin_btn.configure(text="DXF XY 원점 선택: OFF")
            self.measure_mode=False;self.measure_start=None;self.measure_btn.configure(text="거리 측정: OFF")
        self.manual_btn.configure(text=f"수동 탭 추가: {'ON' if self.manual_mode else 'OFF'}")

    def toggle_join(self):
        self.join_mode = not self.join_mode
        self.join_first = None
        if self.join_mode:
            self.manual_mode = False
            self.manual_btn.configure(text="수동 탭 추가: OFF")
            self.origin_mode = False; self.origin_btn.configure(text="DXF XY 원점 선택: OFF")
            self.measure_mode=False;self.measure_start=None;self.measure_btn.configure(text="거리 측정: OFF")
        self.join_btn.configure(text=f"두 라인 선택 연결: {'ON' if self.join_mode else 'OFF'}")
        self.status.set("연결할 첫 번째 열린 선을 클릭하세요." if self.join_mode else "두 라인 연결 모드 종료")

    def toggle_start(self):
        self.start_mode = not self.start_mode
        if self.start_mode:
            self.manual_mode = False; self.join_mode = False; self.join_first = None
            self.manual_btn.configure(text="수동 탭 추가: OFF")
            self.join_btn.configure(text="두 라인 선택 연결: OFF")
            self.origin_mode = False; self.origin_btn.configure(text="DXF XY 원점 선택: OFF")
            self.measure_mode=False;self.measure_start=None;self.measure_btn.configure(text="거리 측정: OFF")
        self.start_btn.configure(text=f"절삭 시작점 선택: {'ON' if self.start_mode else 'OFF'}")
        self.status.set("폐곡선에서 절삭을 시작할 위치를 클릭하세요." if self.start_mode else "시작점 선택 모드 종료")

    def toggle_origin(self):
        if not self.contours:
            messagebox.showinfo("XY 원점", "먼저 DXF를 열어 주세요.")
            return
        self.origin_mode = not self.origin_mode
        if self.origin_mode:
            self.manual_mode = False; self.join_mode = False; self.join_first = None; self.start_mode = False
            self.measure_mode=False;self.measure_start=None;self.measure_btn.configure(text="거리 측정: OFF")
            self.manual_btn.configure(text="수동 탭 추가: OFF")
            self.join_btn.configure(text="두 라인 선택 연결: OFF")
            self.start_btn.configure(text="절삭 시작점 선택: OFF")
        self.origin_btn.configure(text=f"DXF XY 원점 선택: {'ON' if self.origin_mode else 'OFF'}")
        self.status.set("원점으로 사용할 모서리를 클릭하세요. 가까운 꼭짓점은 자동 스냅됩니다." if self.origin_mode else "XY 원점 선택 모드 종료")

    def toggle_measure(self):
        self.measure_mode=not self.measure_mode;self.measure_start=None
        if self.measure_mode:
            self.manual_mode=False;self.join_mode=False;self.join_first=None;self.start_mode=False;self.origin_mode=False
            self.manual_btn.configure(text="수동 탭 추가: OFF");self.join_btn.configure(text="두 라인 선택 연결: OFF")
            self.start_btn.configure(text="절삭 시작점 선택: OFF");self.origin_btn.configure(text="DXF XY 원점 선택: OFF")
        else:self.measurement=None
        self.measure_btn.configure(text=f"거리 측정: {'ON' if self.measure_mode else 'OFF'}")
        self.status.set("첫 점을 클릭하세요. 선 중간 스냅 가능 · 두 번째 점 Shift+클릭은 수직거리" if self.measure_mode else "거리 측정 모드 종료")
        self.redraw()

    def clear_measurement(self,event=None):
        self.measure_start=None;self.measurement=None
        if "status" in self.__dict__:self.status.set("거리 측정을 지웠습니다.")
        if "canvas" in self.__dict__:self.redraw(refresh_tree=False)
        return "break" if event is not None else None

    def snap_measure_point(self,p:Point):
        scale=max(self.view[0],EPS);best=None
        for c in self.visible_contours():
            for q in c.points:
                d=dist(p,q)*scale
                if best is None or d<best[0]:best=(d,q,"vertex",None)
        if best and best[0]<=9:return best[1:]
        best=None
        for c in self.visible_contours():
            n=len(c.points);end=n if c.closed else n-1
            for i in range(end):
                a,b=c.points[i],c.points[(i+1)%n];vx,vy=b[0]-a[0],b[1]-a[1];den=vx*vx+vy*vy
                t=0.0 if den<EPS else max(0.0,min(1.0,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/den))
                q=(a[0]+vx*t,a[1]+vy*t);d=dist(p,q)*scale
                if best is None or d<best[0]:best=(d,q,"line",(a,b))
        if best and best[0]<=16:return best[1:]
        return p,"free",None

    def measure_click(self,p:Point,force_perpendicular:bool=False):
        q,kind,segment=self.snap_measure_point(p)
        if self.measure_start is None:
            self.measure_start=q;self.measurement=None;self.status.set(f"첫 점 X{q[0]:.3f} Y{q[1]:.3f} | 선 중간 클릭=그 위치 · Shift+선 클릭=수직");self.redraw();return
        a=self.measure_start;mode="point";unit=None
        if force_perpendicular and kind=="line" and segment is not None:
            s0,s1=segment;vx,vy=s1[0]-s0[0],s1[1]-s0[1];den=vx*vx+vy*vy
            t=0.0 if den<EPS else max(0.0,min(1.0,((a[0]-s0[0])*vx+(a[1]-s0[1])*vy)/den))
            q=(s0[0]+vx*t,s0[1]+vy*t)
            if EPS<t<1-EPS and den>EPS:mode="perpendicular";ln=math.sqrt(den);unit=(vx/ln,vy/ln)
        self.measurement={"a":a,"b":q,"mode":mode,"unit":unit};self.measure_start=None
        self.status.set(f"측정 {dist(a,q):.3f} mm | ΔX {abs(q[0]-a[0]):.3f} ΔY {abs(q[1]-a[1]):.3f}");self.redraw()

    def set_xy_origin(self, point: Point):
        candidates = [p for c in self.contours for p in c.points]
        snapped = min(candidates, key=lambda p: dist(p, point)) if candidates else point
        if dist(snapped, point) * self.view[0] > 15:
            snapped = point
        self.push_undo("DXF XY 작업 원점 변경")
        ox, oy = snapped
        for c in self.contours:
            c.points = [(x-ox, y-oy) for x, y in c.points]
            c.bridges = [((a[0]-ox, a[1]-oy), (b[0]-ox, b[1]-oy)) for a, b in c.bridges]
        self.vars["xy_origin"].set("선택점")
        self.origin_mode = False
        self.origin_btn.configure(text="DXF XY 원점 선택: OFF")
        self.view_initialized = False
        self.redraw()
        self.status.set(f"XY 작업 원점 설정 완료 | 기존 좌표 X{ox:.3f} Y{oy:.3f} → X0 Y0")

    def join_selected_lines(self, a: Contour, b: Contour):
        if a.closed or b.closed:
            messagebox.showinfo("라인 연결", "열린 선만 연결할 수 있습니다.")
            return
        self.push_undo("두 라인 선택 연결")
        if a is b:
            if dist(a.points[0], a.points[-1]) > EPS:
                a.bridges.append((a.points[-1], a.points[0]))
            a.points = clean_points(a.points, True); a.closed = True
        else:
            options = [(dist(a.points[-1], b.points[0]), False, False),
                       (dist(a.points[-1], b.points[-1]), False, True),
                       (dist(a.points[0], b.points[0]), True, False),
                       (dist(a.points[0], b.points[-1]), True, True)]
            gap, ra, rb = min(options, key=lambda x: x[0])
            pa = list(reversed(a.points)) if ra else list(a.points)
            pb = list(reversed(b.points)) if rb else list(b.points)
            bridge = (pa[-1], pb[0])
            a.points = clean_points(pa + pb, False)
            a.bridges = list(a.bridges) + list(b.bridges)
            if gap > EPS: a.bridges.append(bridge)
            self.contours.remove(b)
            self.status.set(f"두 라인 연결 완료 | 연결 전 간격 {gap:.4f} mm")
        classify_contours(self.contours); self.join_first = None; self.redraw()

    def visible_contours(self) -> List[Contour]:
        return self.view_only if self.view_only is not None else self.contours

    def update_selection_fields(self):
        c=self.selected
        if c is None:
            self.selection_label.set("선택 없음");return
        self.sel_depth.set("" if c.target_depth is None else f"{c.target_depth:g}")
        self.sel_order.set("" if c.cut_order is None else str(c.cut_order))
        self.sel_role.set(c.forced_role);self.sel_tabs.set(c.tabs_enabled);self.sel_enabled.set(c.enabled)
        self.sel_safety_excluded.set(c.safety_excluded)
        self.tree_role_var.set(ui_text({"auto":"자동","inner":"내부","outer":"외부"}.get(c.forced_role,"자동")))
        source="수동지정" if c.forced_role!="auto" else "자동인식"
        count=len(self.selected_contours)
        prefix=f"{count}개 선택 | " if count>1 else ""
        self.selection_label.set(f"{prefix}Layer {c.layer} | {c.role} ({source}) | 길이 {c.length:.1f} mm")

    def sync_order_tree_selection(self):
        if not hasattr(self,"order_tree"):return
        children=self.order_tree.get_children();top=self.order_tree.yview()[0] if children else 0.0
        self.syncing_tree_selection=True
        try:
            current=self.order_tree.selection()
            if current:self.order_tree.selection_remove(*current)
            index_by_id={id(c):i for i,c in enumerate(self.contours)}
            for c in self.selected_contours:
                index=index_by_id.get(id(c));iid=f"c{index}" if index is not None else ""
                if iid and self.order_tree.exists(iid):self.order_tree.selection_add(iid)
            if self.selected is not None:
                index=index_by_id.get(id(self.selected));iid=f"c{index}" if index is not None else ""
                if iid and self.order_tree.exists(iid):self.order_tree.focus(iid)
            if children:self.order_tree.yview_moveto(top)
        finally:self.syncing_tree_selection=False

    def set_contour_selection(self,contours:Sequence[Contour],primary:Optional[Contour]=None,sync_tree=True):
        valid_ids={id(c) for c in self.contours};seen=set();chosen=[]
        for c in contours:
            if id(c) in valid_ids and id(c) not in seen:chosen.append(c);seen.add(id(c))
        self.selected_contours=chosen
        self.selected=primary if primary is not None and any(primary is c for c in chosen) else (chosen[0] if chosen else None)
        self.update_selection_fields()
        if sync_tree:self.sync_order_tree_selection()

    def refresh_order_tree(self):
        if not hasattr(self,"order_tree"): return
        old_children=self.order_tree.get_children();old_top=self.order_tree.yview()[0] if old_children else 0.0
        editor=getattr(self,"tree_role_editor",None)
        if editor is not None and editor.winfo_exists():editor.destroy()
        self.tree_role_editor=None
        valid_ids={id(c) for c in self.contours}
        self.selected_contours=[c for c in self.selected_contours if id(c) in valid_ids]
        if self.selected is not None and not any(self.selected is c for c in self.selected_contours):
            self.selected=self.selected_contours[0] if self.selected_contours else None
        selected_ids={id(c) for c in self.selected_contours}
        self.order_tree.delete(*self.order_tree.get_children())
        active_order=ordered_contours(self.contours,bool(self.vars["rapid_optimize"].get()));actual={id(c):i for i,c in enumerate(active_order,1)}
        display=active_order+[c for c in self.contours if not c.enabled]
        if self.tree_sort_col:
            def sort_key(c):
                if self.tree_sort_col=="seq":return actual.get(id(c),10**9)
                if self.tree_sort_col=="manual":return c.cut_order if c.cut_order is not None else 10**9
                if self.tree_sort_col=="type":return "열린선" if not c.closed else c.role
                if self.tree_sort_col=="layer":return c.layer.lower()
                if self.tree_sort_col=="depth":return c.target_depth if c.target_depth is not None else 10**9
                if self.tree_sort_col=="safety":return c.safety_excluded
                return 0
            display.sort(key=sort_key,reverse=self.tree_sort_reverse)
        index_by_id={id(c):i for i,c in enumerate(self.contours)}
        for c in display:
            idx=index_by_id[id(c)]
            typ="열린선" if not c.closed else ("내부" if c.role=="inner" else "외부")
            depth=f"{c.target_depth:g}" if c.target_depth is not None else "관통"
            seq=str(actual[id(c)]) if c.enabled else "-"
            manual=str(c.cut_order) if c.cut_order is not None else "자동"
            iid=f"c{idx}"
            tags=[]
            if not c.enabled:tags.append("disabled")
            elif c.safety_excluded:tags.append("safety_excluded")
            self.order_tree.insert("", "end", iid=iid,
                                   values=(seq,ui_text(manual),ui_text(typ),c.layer,ui_text(depth),
                                           ui_text("제외" if c.safety_excluded else "검사")),tags=tuple(tags))
            if id(c) in selected_ids:self.order_tree.selection_add(iid)
        self.order_tree.tag_configure("disabled",foreground="#888888")
        self.order_tree.tag_configure("safety_excluded",foreground="#a85b00")
        if self.selected is not None:
            chosen_index=index_by_id.get(id(self.selected));chosen_iid=f"c{chosen_index}" if chosen_index is not None else ""
            if chosen_iid and self.order_tree.exists(chosen_iid):self.order_tree.focus(chosen_iid)
        if old_children:self.order_tree.yview_moveto(old_top)

    def sort_order_tree(self,col):
        if self.tree_sort_col==col:self.tree_sort_reverse=not self.tree_sort_reverse
        else:self.tree_sort_col=col;self.tree_sort_reverse=False
        self.refresh_order_tree()

    def tree_select(self,event=None):
        if self.syncing_tree_selection:return
        items=self.order_tree.selection()
        targets=[]
        for item in items:
            idx=int(item[1:])
            if 0<=idx<len(self.contours):targets.append(self.contours[idx])
        focus=self.order_tree.focus();primary=None
        if focus in items:
            idx=int(focus[1:]);primary=self.contours[idx] if 0<=idx<len(self.contours) else None
        self.set_contour_selection(targets,primary,sync_tree=False)
        self.redraw(refresh_tree=False)

    def tree_cell_click(self,event):
        if self.order_tree.identify_region(event.x,event.y)!="cell":return
        if self.order_tree.identify_column(event.x)!="#3":return
        item=self.order_tree.identify_row(event.y)
        if item:self.after_idle(lambda i=item:self.open_tree_role_editor(i))

    def toggle_selected_safety(self):
        items=list(self.order_tree.selection())
        if not items:
            messagebox.showinfo("안전검사 제외","윤곽 목록에서 하나 이상 선택하세요.");return
        targets=[]
        for iid in items:
            idx=int(iid[1:])
            if 0<=idx<len(self.contours):targets.append(self.contours[idx])
        if not targets:return
        self.push_undo("안전검사 제외 변경")
        exclude=not all(c.safety_excluded for c in targets)
        for c in targets:c.safety_excluded=exclude
        self.collision_cache_key=None
        self.sel_safety_excluded.set(exclude)
        self.status.set(f"선택 윤곽 {len(targets)}개 안전검사 {'제외' if exclude else '복원'}")
        self.redraw()

    def open_tree_role_editor(self,item):
        if not self.order_tree.exists(item):return
        if item not in self.order_tree.selection():self.order_tree.selection_set(item)
        bbox=self.order_tree.bbox(item,"#3")
        if not bbox:return
        idx=int(item[1:]);current=self.contours[idx].forced_role if 0<=idx<len(self.contours) else "auto"
        value=tk.StringVar(value={"auto":"자동","inner":"내부","outer":"외부"}.get(current,"자동"))
        editor=ttk.Combobox(self.order_tree,state="readonly",values=("자동","내부","외부"),textvariable=value)
        self.tree_role_editor=editor;editor.place(x=bbox[0],y=bbox[1],width=bbox[2],height=bbox[3]);editor.focus_set()
        editor.bind("<<ComboboxSelected>>",lambda e:self.commit_tree_role_editor(item,value.get()))
        editor.bind("<Escape>",lambda e:editor.destroy())
        def post_list():
            try:editor.tk.call("ttk::combobox::Post",editor._w)
            except tk.TclError:pass
        editor.after_idle(post_list)

    def commit_tree_role_editor(self,item,label):
        mapping={"자동":"auto","내부":"inner","외부":"outer","Auto":"auto","Inner":"inner","Outer":"outer"};new_role=mapping[label]
        items=list(self.order_tree.selection())
        if item not in items:items=[item]
        targets=[]
        for iid in items:
            idx=int(iid[1:])
            if 0<=idx<len(self.contours):targets.append(self.contours[idx])
        if not targets:return
        self.push_undo("목록 셀에서 내부/외부 변경")
        for c in targets:c.forced_role=new_role
        classify_contours(self.contours);self.selected=targets[0];self.sel_role.set(new_role);self.tree_role_var.set(label)
        self.redraw();self.status.set(f"선택 윤곽 {len(targets)}개를 {label} 판정으로 변경")

    def apply_tree_role(self):
        items=self.order_tree.selection()
        if not items:
            messagebox.showinfo("내부/외부 설정","목록에서 윤곽을 먼저 선택하세요.");return
        mapping={"자동":"auto","내부":"inner","외부":"outer","Auto":"auto","Inner":"inner","Outer":"outer"};new_role=mapping[self.tree_role_var.get()]
        targets=[]
        for item in items:
            idx=int(item[1:])
            if 0<=idx<len(self.contours):targets.append(self.contours[idx])
        if not targets:return
        self.push_undo("목록에서 내부/외부 변경")
        for c in targets:c.forced_role=new_role
        classify_contours(self.contours)
        self.selected=targets[0];self.sel_role.set(new_role)
        self.redraw();self.status.set(f"선택 윤곽 {len(targets)}개를 {self.tree_role_var.get()} 판정으로 변경")

    def show_tree_selection(self):
        items=self.order_tree.selection()
        if not items:
            messagebox.showinfo("윤곽 보기","목록에서 윤곽을 하나 이상 선택하세요.");return
        selected=[]
        for item in items:
            idx=int(item[1:])
            if 0<=idx<len(self.contours):selected.append(self.contours[idx])
        self.view_only=selected;self.view_initialized=False;self.redraw()
        self.status.set(f"선택한 윤곽 {len(selected)}개만 표시 중")

    def show_all_contours(self):
        self.view_only=None;self.view_initialized=False;self.redraw();self.status.set("전체 윤곽 표시")

    def apply_font_size(self,silent=False):
        try:size=int(self.font_size_var.get())
        except (ValueError,tk.TclError):size=10
        size=max(8,min(20,size));self.font_size_var.set(size);self.ui_font_size=size
        for name in ("TkDefaultFont","TkTextFont","TkMenuFont","TkHeadingFont"):
            try:tkfont.nametofont(name).configure(size=size)
            except tk.TclError:pass
        try:tkfont.nametofont("TkFixedFont").configure(size=size)
        except tk.TclError:pass
        self.text.configure(font=("Consolas",size));self.start_text.configure(font=("Consolas",size));self.end_text.configure(font=("Consolas",size))
        ttk.Style(self).configure("Treeview",rowheight=max(20,size+10),font=("Segoe UI",size))
        ttk.Style(self).configure("Treeview.Heading",font=("Segoe UI",size,"bold"))
        self.redraw()
        if not silent:self.status.set(f"화면 글자 크기 {size} 적용")

    def bounds(self):
        pts = [p for c in self.visible_contours() for p in c.points]
        if self.sheet_size:pts += [(0.0,0.0),self.sheet_size]
        if not pts: return (0,0,1,1)
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

    def fit_view(self):
        self.view_initialized = False
        self.redraw()

    def begin_view_interaction(self):
        if self.view_interacting:return
        self.view_interacting=True
        # Compensation paths, warnings and order labels are the expensive half
        # of a large preview.  They are recreated after the gesture, while the
        # base geometry remains responsive under the pointer.
        try:self.canvas.itemconfigure("view_detail",state="hidden")
        except tk.TclError:pass

    def queue_view_transform(self,scale=1.0,anchor=(0.0,0.0),dx=0.0,dy=0.0):
        # Compose all wheel/mouse events received during one display frame into
        # one native Canvas scale + move operation.  High-resolution wheels can
        # otherwise request dozens of full-scene transforms per second.
        if abs(scale-1.0)>EPS:
            ax,ay=anchor
            self.pending_view_tx=scale*self.pending_view_tx+(1.0-scale)*ax
            self.pending_view_ty=scale*self.pending_view_ty+(1.0-scale)*ay
            self.pending_view_scale*=scale
        self.pending_view_tx+=dx;self.pending_view_ty+=dy
        if self.view_transform_job is None:
            self.view_transform_job=self.after(16,self.apply_view_transform)

    def apply_view_transform(self):
        if self.view_transform_job is not None:
            try:self.after_cancel(self.view_transform_job)
            except tk.TclError:pass
            self.view_transform_job=None
        scale=self.pending_view_scale;tx=self.pending_view_tx;ty=self.pending_view_ty
        self.pending_view_scale=1.0;self.pending_view_tx=self.pending_view_ty=0.0
        if abs(scale-1.0)>EPS:self.canvas.scale("view_live",0,0,scale,scale)
        if abs(tx)>EPS or abs(ty)>EPS:self.canvas.move("view_live",tx,ty)

    def schedule_view_redraw(self,delay=170):
        if self.view_redraw_job is not None:
            try:self.after_cancel(self.view_redraw_job)
            except tk.TclError:pass
        self.view_redraw_job=self.after(delay,self.finish_view_redraw)

    def canvas_zoom(self, event):
        if not self.contours: return
        self.begin_view_interaction()
        old, ox, oy = self.view
        world = self.inv_transform((event.x, event.y))
        new = max(0.05, min(5000.0, old * (1.15 if event.delta > 0 else 1/1.15)))
        self.view = (new, event.x - world[0]*new, event.y + world[1]*new)
        self.view_initialized = True
        self.queue_view_transform(new/old,(event.x,event.y))
        self.schedule_view_redraw()

    def finish_view_redraw(self):
        self.view_redraw_job=None;self.redraw(refresh_tree=False)

    def pan_start(self, event):
        if self.view_redraw_job is not None:
            self.after_cancel(self.view_redraw_job);self.view_redraw_job=None
        self.apply_view_transform();self.begin_view_interaction()
        self.pan_anchor = (event.x, event.y, self.view[1], self.view[2], event.x, event.y)

    def pan_move(self, event):
        if not self.pan_anchor: return
        x, y, ox, oy, lastx, lasty = self.pan_anchor
        self.view = (self.view[0], ox + event.x-x, oy + event.y-y)
        self.view_initialized = True
        self.queue_view_transform(dx=event.x-lastx,dy=event.y-lasty)
        self.pan_anchor=(x,y,ox,oy,event.x,event.y)

    def pan_end(self,event):
        self.pan_anchor=None;self.apply_view_transform();self.schedule_view_redraw(90)

    def transform(self, p: Point) -> Point:
        scale, ox, oy = self.view
        return ox + p[0]*scale, oy - p[1]*scale

    def inv_transform(self, p: Point) -> Point:
        scale, ox, oy = self.view
        return (p[0]-ox)/scale, (oy-p[1])/scale

    def draw_grid(self):
        if not self.vars.get("show_grid") or not self.vars["show_grid"].get():return
        scale=max(self.view[0],EPS);target=65.0/scale;base=10**math.floor(math.log10(max(target,1e-9)))
        spacing=next((base*m for m in (1,2,5,10) if base*m>=target),base*10)
        w=max(self.canvas.winfo_width(),100);h=max(self.canvas.winfo_height(),100)
        xa,ya=self.inv_transform((0,h));xb,yb=self.inv_transform((w,0))
        x0,x1=sorted((xa,xb));y0,y1=sorted((ya,yb))
        ix0=int(math.floor(x0/spacing))-1;ix1=int(math.ceil(x1/spacing))+1
        iy0=int(math.floor(y0/spacing))-1;iy1=int(math.ceil(y1/spacing))+1
        if ix1-ix0>250 or iy1-iy0>250:return
        for i in range(ix0,ix1+1):
            x=i*spacing;sx,_=self.transform((x,0));major=i%5==0
            self.canvas.create_line(sx,0,sx,h,fill="#343b43" if major else "#252b31",width=1)
            if major:self.canvas.create_text(sx+3,h-4,text=f"{x:g}",fill="#68727c",anchor="sw",font=("Arial",8))
        for i in range(iy0,iy1+1):
            y=i*spacing;_,sy=self.transform((0,y));major=i%5==0
            self.canvas.create_line(0,sy,w,sy,fill="#343b43" if major else "#252b31",width=1)
            if major:self.canvas.create_text(3,sy-2,text=f"{y:g}",fill="#68727c",anchor="sw",font=("Arial",8))

    def draw_measurement(self):
        if self.measure_start is not None:
            x,y=self.transform(self.measure_start);self.canvas.create_oval(x-5,y-5,x+5,y+5,fill="#ff55e6",outline="white",width=2)
        if not self.measurement:return
        a,b=self.measurement["a"],self.measurement["b"];ax,ay=self.transform(a);bx,by=self.transform(b)
        self.canvas.create_line(ax,ay,bx,by,fill="#ff55e6",width=2)
        self.canvas.create_oval(ax-4,ay-4,ax+4,ay+4,fill="#ff55e6",outline="white")
        self.canvas.create_oval(bx-4,by-4,bx+4,by+4,fill="#ff55e6",outline="white")
        label=f"{dist(a,b):.3f} mm"
        self.canvas.create_text((ax+bx)/2+7,(ay+by)/2-7,text=label,fill="#ff9eee",anchor="sw",font=("Arial",self.ui_font_size,"bold"))
        if self.measurement["mode"]=="perpendicular" and self.measurement["unit"] is not None:
            ux,uy=self.measurement["unit"];us=(ux,-uy)
            vx,vy=ax-bx,ay-by;vl=math.hypot(vx,vy) or 1.0;vs=(vx/vl,vy/vl);k=11
            pts=(bx+us[0]*k,by+us[1]*k,bx+(us[0]+vs[0])*k,by+(us[1]+vs[1])*k,bx+vs[0]*k,by+vs[1]*k)
            self.canvas.create_line(*pts,fill="#ff9eee",width=2)

    def canvas_item_marker(self)->int:
        items=self.canvas.find_all();return int(items[-1]) if items else 0

    def tag_canvas_items_after(self,marker:int,tag:str):
        for item in self.canvas.find_all():
            if int(item)>marker:self.canvas.addtag_withtag(tag,item)

    def redraw(self,refresh_tree=True):
        if self.view_redraw_job is not None:
            try:self.after_cancel(self.view_redraw_job)
            except tk.TclError:pass
            self.view_redraw_job=None
        if self.view_transform_job is not None:
            try:self.after_cancel(self.view_transform_job)
            except tk.TclError:pass
            self.view_transform_job=None
        self.pending_view_scale=1.0;self.pending_view_tx=self.pending_view_ty=0.0
        self.view_interacting=False
        self.canvas.delete("all")
        if refresh_tree:self.refresh_order_tree();self.refresh_object_tree()
        if not self.contours: return
        x0,y0,x1,y1 = self.bounds(); w=max(self.canvas.winfo_width(),100); h=max(self.canvas.winfo_height(),100)
        if not self.view_initialized:
            scale = min((w-50)/max(x1-x0,1), (h-50)/max(y1-y0,1))
            ox = 25-x0*scale; oy = h-25+y0*scale; self.view=(scale,ox,oy)
            self.view_initialized = True
        self.draw_grid()
        if self.sheet_size:
            sw,sh=self.sheet_size;x0s,y0s=self.transform((0,0));x1s,y1s=self.transform((sw,sh))
            self.canvas.create_rectangle(x0s,y1s,x1s,y0s,outline="#9aa8b5",width=3,dash=(8,5))
            self.canvas.create_text(x0s+8,y1s+8,text=f"판재 {sw:g} × {sh:g} mm",fill="#b7c4cf",anchor="nw",font=("Arial",self.ui_font_size,"bold"))
        all_visible=self.visible_contours()
        selected_ids={id(c) for c in self.selected_contours}
        # Do not create thousands of off-screen Canvas objects after zooming
        # into one part of a large array.  A small margin prevents geometry
        # flicker while the next pan gesture begins.
        margin=90
        va=self.inv_transform((-margin,h+margin));vb=self.inv_transform((w+margin,-margin))
        vx0,vx1=sorted((va[0],vb[0]));vy0,vy1=sorted((va[1],vb[1]))
        def intersects_view(contour:Contour)->bool:
            if not contour.points:return False
            cx0=min(p[0] for p in contour.points);cx1=max(p[0] for p in contour.points)
            cy0=min(p[1] for p in contour.points);cy1=max(p[1] for p in contour.points)
            return cx1>=vx0 and cx0<=vx1 and cy1>=vy0 and cy0<=vy1
        visible=[c for c in all_visible if intersects_view(c)]
        if len(self.part_objects)>1 or self.nest_active:
            groups={}
            for c in all_visible:
                if not c.object_id:continue
                groups.setdefault((c.object_id,c.instance_id or 1,c.object_name),[]).extend(c.points)
            if len(groups)<=100:
                for (object_id,instance_id,name),pts in groups.items():
                    if not pts:continue
                    gx0=min(p[0] for p in pts);gy0=min(p[1] for p in pts);gx1=max(p[0] for p in pts);gy1=max(p[1] for p in pts)
                    sx0,sy0=self.transform((gx0,gy0));sx1,sy1=self.transform((gx1,gy1));color=OBJECT_COLORS[(object_id-1)%len(OBJECT_COLORS)]
                    key=(object_id,instance_id);tag=self.manual_group_tag(key);chosen=self.manual_array_mode and key==self.manual_array_selected
                    self.canvas.create_rectangle(sx0,sy1,sx1,sy0,outline="#42e695" if chosen else color,
                                                 width=3 if chosen else 1,dash=() if chosen else (3,4),tags=(tag,))
                    self.canvas.create_text(sx0+4,sy1+4,text=f"{name} #{instance_id}",fill="#42e695" if chosen else color,
                                            anchor="nw",font=("Arial",max(8,self.ui_font_size-1),"bold"),tags=(tag,))
        for c in visible:
            group_tag=self.manual_group_tag(contour_group_key(c)) if c.object_id else ""
            xy=[]
            for p in c.points + ([c.points[0]] if c.closed else []): xy.extend(self.transform(p))
            group_chosen=self.manual_array_mode and c.object_id and contour_group_key(c)==self.manual_array_selected
            color = "#42e695" if id(c) in selected_ids or group_chosen else ("#666666" if not c.enabled else ("#4aa8ff" if c.role=="inner" else "#ffd84d"))
            self.canvas.create_line(*xy, fill=color, width=3 if id(c) in selected_ids else 2,tags=(group_tag,) if group_tag else ())
            for a,b in c.bridges:
                ax,ay=self.transform(a); bx,by=self.transform(b)
                self.canvas.create_line(ax,ay,bx,by,fill="#d66bff",width=4,tags=(group_tag,) if group_tag else ())
            for s in c.tabs:
                p,_,_=point_at(c.points,s,c.closed); x,y=self.transform(p)
                self.canvas.create_oval(x-5,y-5,x+5,y+5,fill="#ff9f1c",outline="",tags=(group_tag,) if group_tag else ())
            if c.closed and c.start_s > EPS:
                p,_,_=point_at(c.points,c.start_s,True); x,y=self.transform(p)
                self.canvas.create_polygon(x,y-7,x-6,y+5,x+6,y+5,fill="#ff4fd8",outline="white",tags=(group_tag,) if group_tag else ())
        self.canvas.addtag_all("view_live")
        detail_marker=self.canvas_item_marker()
        if not self.manual_array_mode and self.vars.get("show_toolpath") and self.vars["show_toolpath"].get():
            try: preview_radius = self.vars["tool_d"].get()/2
            except (tk.TclError, ValueError): preview_radius = 1.0
            auto_trim_value=bool(self.vars.get("auto_trim") and self.vars["auto_trim"].get())
            geometry_signature=hash(tuple((id(c),c.enabled,c.safety_excluded,c.closed,c.role,c.target_depth,
                tuple((round(x,5),round(y,5)) for x,y in c.points)) for c in self.contours))
            collision_key=(round(preview_radius*2,6),auto_trim_value,geometry_signature)
            if collision_key!=self.collision_cache_key:
                # Interactive redraw must never spawn worker processes while a
                # part is being dragged. Explicit safety/G-code checks use all cores.
                self.collision_cache=tool_sweep_collisions(
                    self.contours,preview_radius*2,auto_trim_value,use_parallel=False)
                self.collision_cache_key=collision_key
            visible_ids={id(c) for c in visible}
            if len(self.preview_cache)>max(512,len(self.contours)*8):self.preview_cache.clear()
            rapid_order=bool(self.vars["rapid_optimize"].get())
            order_signature=hash(tuple((id(c),c.cut_order,round(c.start_s,6),c.enabled)
                                       for c in self.contours))
            order_key=(geometry_signature,order_signature,rapid_order)
            if order_key!=self.preview_order_cache_key:
                self.preview_order_cache=ordered_contours(self.contours,rapid_order)
                self.preview_order_cache_key=order_key
            preview_order=self.preview_order_cache
            show_order_numbers=len(preview_order)<=60
            for number, c in enumerate(preview_order, 1):
                if id(c) not in visible_ids: continue
                if not c.closed:
                    xy=[]
                    for p in c.points: xy.extend(self.transform(p))
                    self.canvas.create_line(*xy,fill="#ff6363",dash=(4,3),width=1)
                    if show_order_numbers:
                        x,y=self.transform(c.points[0]); self.canvas.create_text(x+9,y-9,text=str(number),fill="white",font=("Arial",self.ui_font_size,"bold"))
                    continue
                auto_trim=auto_trim_value
                anchor=c.points[0]
                relative_points=tuple((round(x-anchor[0],7),round(y-anchor[1],7)) for x,y in c.points)
                cache_key=(relative_points,c.closed,c.role,c.forced_role,c.depth,c.enabled,
                           round(c.start_s,8),round(preview_radius,8),auto_trim)
                cached=self.preview_cache.get(cache_key)
                if cached is None:
                    route,removed_loops,cut_points=compensated_route(c,preview_radius*2,auto_trim)
                    if c.start_s > EPS:
                        start_point=point_at(c.points,c.start_s,True)[0]
                        route=rotate_closed_path(route,nearest_path_distance(route,start_point,True)[1])
                    errors,warnings=contour_toolpath_issues(c,preview_radius*2,auto_trim)
                    rel_route=[(x-anchor[0],y-anchor[1]) for x,y in route]
                    rel_removed=[[(x-anchor[0],y-anchor[1]) for x,y in loop] for loop in removed_loops]
                    rel_cuts=[(x-anchor[0],y-anchor[1]) for x,y in cut_points]
                    cached=(rel_route,rel_removed,rel_cuts,errors,warnings);self.preview_cache[cache_key]=cached
                rel_route,rel_removed,rel_cuts,errors,warnings=cached
                errors=list(errors)+self.collision_cache.get(id(c),[])
                route=[(x+anchor[0],y+anchor[1]) for x,y in rel_route]
                removed_loops=[[(x+anchor[0],y+anchor[1]) for x,y in loop] for loop in rel_removed]
                cut_points=[(x+anchor[0],y+anchor[1]) for x,y in rel_cuts]
                xy=[]
                for p in route+[route[0]]: xy.extend(self.transform(p))
                other_warnings=[w for w in warnings if "자동 절단" not in w]
                try:
                    stock_value=float(self.vars["stock"].get());target=c.target_depth if c.target_depth is not None else stock_value+float(self.vars["extra"].get())
                    preview_cfg={"wall_finish":bool(self.vars["wall_finish"].get()),
                                 "finish_scope":self.vars["finish_scope"].get(),
                                 "finish_allowance":float(self.vars["finish_allowance"].get())}
                    show_rough=wall_finish_for(c,target,stock_value,preview_cfg)
                except (tk.TclError,ValueError,KeyError):show_rough=False
                if show_rough:
                    rough,_=rough_route_for(c,route,preview_cfg);roughxy=[]
                    for p in rough+[rough[0]]:roughxy.extend(self.transform(p))
                    self.canvas.create_line(*roughxy,fill="#ffb347",dash=(7,4),width=2)
                path_color="#9b8cff" if c.safety_excluded else ("#ff3030" if errors else ("#ff9d3d" if other_warnings else "#ff6363"))
                path_dash=(8,4) if c.safety_excluded else (() if errors else (4,3))
                self.canvas.create_line(*xy,fill=path_color,dash=path_dash,width=3 if errors else (2 if c.safety_excluded else 1))
                x,y=self.transform(route[0])
                if show_order_numbers:self.canvas.create_text(x+9,y-9,text=str(number),fill="white",font=("Arial",self.ui_font_size,"bold"))
                if errors or other_warnings:
                    self.canvas.create_text(x+18,y+10,text="!",fill="#ff3030" if errors else "#ffb13b",font=("Arial",self.ui_font_size+5,"bold"))
                for loop in removed_loops:
                    loopxy=[]
                    for p in loop:loopxy.extend(self.transform(p))
                    self.canvas.create_line(*loopxy,fill="#ff9d00",width=3,dash=(2,2))
                for cp in cut_points:
                    cx,cy=self.transform(cp)
                    self.canvas.create_text(cx+8,cy-8,text="!",fill="#ffb000",font=("Arial",self.ui_font_size+5,"bold"))
                try:plan=lead_plan(c,route,self.vars["lead"].get());entry,mode=plan.entry,plan.mode
                except (tk.TclError,ValueError):plan=LeadPlan(route[0],"none");entry,mode=route[0],"none"
                if entry != route[0]:
                    leadxy=[]
                    for p in lead_arc_points(plan,route[0]) if plan.center is not None else [entry,route[0]]:leadxy.extend(self.transform(p))
                    ex,ey=self.transform(entry)
                    self.canvas.create_line(*leadxy,fill="#54e1ff",width=2,arrow="last",smooth=plan.center is not None)
                    if mode=="center-fallback":
                        self.canvas.create_oval(ex-4,ey-4,ex+4,ey+4,fill="#54e1ff",outline="white")
        self.tag_canvas_items_after(detail_marker,"view_detail")
        overlay_marker=self.canvas_item_marker()
        self.draw_measurement()
        if self.vars.get("xy_origin") and self.vars["xy_origin"].get() in ("Selected point","선택점"):
            # Draw last so the selected work origin cannot be covered by preview paths.
            ox,oy=self.transform((0.0,0.0))
            self.canvas.create_oval(ox-7,oy-7,ox+7,oy+7,fill="#2979ff",outline="white",width=2)
            self.canvas.create_line(ox-18,oy,ox+30,oy,fill="#ff5555",width=3,arrow="last")
            self.canvas.create_line(ox,oy+18,ox,oy-30,fill="#58e36a",width=3,arrow="last")
            self.canvas.create_text(ox+34,oy,text="X0",fill="#ff7777",anchor="w",font=("Arial",self.ui_font_size,"bold"))
            self.canvas.create_text(ox,oy-34,text="Y0",fill="#75ed83",anchor="s",font=("Arial",self.ui_font_size,"bold"))
            self.canvas.create_text(ox+10,oy+12,text="Z0",fill="#72a7ff",anchor="nw",font=("Arial",self.ui_font_size,"bold"))
        self.tag_canvas_items_after(overlay_marker,"view_live")

    def canvas_press(self,event):
        if self.manual_array_mode:
            key=self.manual_group_at(self.inv_transform((event.x,event.y)))
            self.manual_array_selected=key;self.manual_array_drag=None
            if key is not None:
                self.manual_array_drag=(key,event.x,event.y,event.x,event.y)
                self.status.set(f"선택 객체 #{key[1]} | 드래그 이동 · R키 90° 회전")
            else:self.status.set("배치할 객체의 경계 안을 클릭하세요.")
            self.redraw(refresh_tree=False);return
        if self.measure_mode or self.origin_mode or self.start_mode or self.join_mode or self.manual_mode:
            self.canvas_click(event);return
        self.canvas_selection_drag=(event.x,event.y,event.x,event.y)
        self.canvas.delete("selection_box")

    def canvas_left_drag(self,event):
        if self.manual_array_mode:
            if self.manual_array_drag is None:return
            key,sx,sy,lx,ly=self.manual_array_drag
            self.canvas.move(self.manual_group_tag(key),event.x-lx,event.y-ly)
            self.manual_array_drag=(key,sx,sy,event.x,event.y);return
        if self.canvas_selection_drag is None:return
        sx,sy,_,_=self.canvas_selection_drag;self.canvas_selection_drag=(sx,sy,event.x,event.y)
        self.canvas.delete("selection_box")
        if abs(event.x-sx)<4 and abs(event.y-sy)<4:return
        crossing=event.x<sx
        self.canvas.create_rectangle(sx,sy,event.x,event.y,outline="#42e695" if crossing else "#5fc6ff",
                                     width=2,dash=(5,3) if crossing else (),tags="selection_box")

    def canvas_left_release(self,event):
        if self.manual_array_mode:
            if self.manual_array_drag is None:return
            key,sx,sy,lx,ly=self.manual_array_drag;self.manual_array_drag=None
            scale=max(self.view[0],EPS);dx=(event.x-sx)/scale;dy=(sy-event.y)/scale
            if abs(dx)>EPS or abs(dy)>EPS:
                self.push_undo("수동 배치 이동");move_contour_group(self.contours,key,dx,dy)
                self.preview_cache.clear();self.collision_cache_key=None
                self.status.set(f"객체 #{key[1]} 이동 | ΔX {dx:.3f} ΔY {dy:.3f} mm")
            self.redraw(refresh_tree=False);return
        if self.canvas_selection_drag is None:return
        sx,sy,_,_=self.canvas_selection_drag;self.canvas_selection_drag=None;self.canvas.delete("selection_box")
        if abs(event.x-sx)<4 and abs(event.y-sy)<4:
            self.canvas_click(event);return
        a=self.inv_transform((sx,sy));b=self.inv_transform((event.x,event.y))
        rect=(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))
        crossing=event.x<sx
        hits=[c for c in self.visible_contours() if contour_in_selection_rect(c,rect,crossing)]
        additive=bool(event.state & (0x0001|0x0004))
        chosen=(self.selected_contours+hits) if additive else hits
        self.set_contour_selection(chosen,hits[-1] if hits else self.selected)
        mode="걸침 선택" if crossing else "창 선택"
        self.status.set(f"{mode}: 윤곽 {len(hits)}개 · 전체 선택 {len(self.selected_contours)}개")
        self.redraw(refresh_tree=False)

    def canvas_click(self, event):
        if not self.contours: return
        p=self.inv_transform((event.x,event.y))
        if self.measure_mode:
            self.measure_click(p,bool(event.state & 0x0001))
            return
        if self.origin_mode:
            self.set_xy_origin(p)
            return
        best=None
        for c in self.visible_contours():
            d,s=nearest_path_distance(c.points,p,c.closed)
            if best is None or d<best[0]: best=(d,c,s)
        if best and best[0]*self.view[0] <= 15:
            if self.start_mode:
                if not best[1].closed:
                    messagebox.showinfo("시작점", "절삭 시작점은 폐곡선에서 선택하세요.")
                else:
                    self.push_undo("절삭 시작점 변경")
                    best[1].start_s = best[2];self.set_contour_selection([best[1]],best[1])
                    self.status.set(f"절삭 시작점 설정 | Layer {best[1].layer}")
                    self.redraw(refresh_tree=False)
            elif self.join_mode:
                if best[1].closed:
                    messagebox.showinfo("라인 연결", "폐곡선이 아닌 열린 선을 선택하세요.")
                elif self.join_first is None:
                    self.join_first = best[1];self.set_contour_selection([best[1]],best[1])
                    self.status.set("첫 번째 선 선택됨. 연결할 두 번째 열린 선을 클릭하세요.")
                    self.redraw(refresh_tree=False)
                else:
                    self.join_selected_lines(self.join_first, best[1])
            elif self.manual_mode:
                if best[1].closed and best[1].role == "outer" and best[1].tabs_enabled:
                    self.push_undo("수동 탭 추가")
                    best[1].tabs.append(best[2]);best[1].tabs.sort();best[1].tabs_cleared=False;self.redraw()
                    self.status.set(f"수동 탭 추가: {len(best[1].tabs)}개")
            else:
                additive=bool(event.state & (0x0001|0x0004))
                chosen=(self.selected_contours+[best[1]]) if additive else [best[1]]
                self.set_contour_selection(chosen,best[1]);self.redraw(refresh_tree=False)
        elif not (self.start_mode or self.join_mode or self.manual_mode):
            self.set_contour_selection([]);self.redraw(refresh_tree=False)

    def make_gcode(self,split_selected=False):
        if not self.contours: messagebox.showinfo("안내", "먼저 DXF를 열어 주세요."); return
        progress:Optional[ProgressDialog]=None
        try:
            progress=ProgressDialog(self,"G-code 생성")
            progress.set_progress(2,"가공 설정 확인 중")
            cfg = self.config()
            requested_signature=self.job_signature(cfg);self.gcode="";self.gcode_parts=[];self.gcode_job_minutes=0.0;self.gcode_signature=None
            active = [c for c in self.contours if c.enabled]
            if not active:
                messagebox.showerror("가공 점검", "가공에 포함된 윤곽이 없습니다.")
                return
            part1:List[Contour]=[];part2:List[Contour]=[]
            if split_selected:
                selected_ids={id(c) for c in self.selected_contours}
                part1=[c for c in active if id(c) in selected_ids]
                part2=[c for c in active if id(c) not in selected_ids]
                if not part1:
                    messagebox.showinfo("2분할 G-code", "PART1으로 가공할 윤곽을 미리보기나 윤곽 목록에서 먼저 선택하세요.")
                    return
                if not part2:
                    messagebox.showinfo("2분할 G-code", "가공 윤곽이 모두 선택되어 PART2가 비어 있습니다.\nPART1에 넣을 윤곽만 선택하세요.")
                    return
            open_count = sum(not c.closed for c in active)
            warnings=[]
            if open_count:
                warnings.append(f"열린 윤곽 {open_count}개: 공구 중심선 가공으로 출력됩니다.")
            if self.nest_active:
                edge_issues,spacing_issues=self.manual_array_layout_issues()
                if edge_issues or spacing_issues:
                    warnings.append(f"배치 여유 위반: 가장자리 {edge_issues}개, 간격/겹침 {spacing_issues}쌍")
            sequence=ordered_contours(active,cfg.get("rapid_optimize",True))
            first_outer=next((i for i,c in enumerate(sequence) if c.closed and c.role=="outer"),None)
            if first_outer is not None and any(c.role=="inner" for c in sequence[first_outer+1:]):
                warnings.append("수동 순번 때문에 외곽이 일부 내부 형상보다 먼저 가공됩니다. 부품 고정을 확인하세요.")
            manual_orders=[c.cut_order for c in active if c.cut_order is not None]
            if len(manual_orders)!=len(set(manual_orders)):
                warnings.append("같은 수동 가공 순번이 중복되었습니다. 같은 번호 안에서는 자동 안전 순서를 사용합니다.")
            if split_selected:
                conflicts=split_outer_inner_conflicts(part1,part2)
                if conflicts:
                    warnings.append(
                        f"2분할 순서 주의: PART1 외곽 안쪽의 내부 윤곽 {conflicts}개가 PART2에 있습니다. "
                        "PART1에서 외곽을 먼저 자르면 소재가 분리될 수 있습니다.")
            too_small=[]; center_leads=0; fatal=[]; geometry_warnings=[]
            collision_map=tool_sweep_collisions(
                active,cfg["tool_d"],cfg.get("auto_trim",False),
                lambda value,message:progress.set_progress(5+value*.22,message) if progress else None)
            for check_index,c in enumerate(active,1):
                progress.set_progress(27+18*check_index/max(len(active),1),
                                      f"경로 안전검사 {check_index}/{len(active)}")
                errs,warns=contour_toolpath_issues(c,cfg["tool_d"],cfg.get("auto_trim",False))
                fatal += [f"Layer {c.layer}: {x}" for x in errs]
                fatal += [f"Layer {c.layer}: {x}" for x in collision_map.get(id(c),[])]
                geometry_warnings += [f"Layer {c.layer}: {x}" for x in warns]
                if c.safety_excluded:continue
                if c.closed and c.role=="inner":
                    width=max(p[0] for p in c.points)-min(p[0] for p in c.points)
                    height=max(p[1] for p in c.points)-min(p[1] for p in c.points)
                    if min(width,height) <= cfg["tool_d"] + EPS:
                        too_small.append(c.layer)
                    route,_,_=compensated_route(c,cfg["tool_d"],cfg.get("auto_trim",False))
                    if lead_point(c,route,cfg["lead"])[1]=="center-fallback": center_leads+=1
            if too_small:
                warnings.append(f"공구 지름보다 작거나 같은 내부 형상 {len(too_small)}개: 가공 불가 가능성")
            warnings += geometry_warnings
            if fatal:
                progress.close();progress=None
                messagebox.showerror("위험한 공구경로 - 생성 중지",
                                     "다음 문제 때문에 G-code를 생성하지 않습니다.\n\n"+"\n".join(fatal[:12])+
                                     ("\n..." if len(fatal)>12 else "")+"\n\n공구 지름, 내부/외부 판정 또는 형상을 수정하세요.")
                return
            if warnings:
                progress.close();progress=None
                if not messagebox.askokcancel("가공 전 점검", "\n".join(warnings)+"\n\n계속 생성할까요?"):
                    return
                progress=ProgressDialog(self,"G-code 생성")
            progress.set_progress(48,"G-code 공구경로 생성 중")
            if split_selected:
                common_origin=work_origin_for_contours(active,cfg)
                part1_m,part1_min,_,_=machining_report(part1,cfg)
                cfg1=dict(cfg);cfg1.update({
                    "_xy_origin_override":common_origin,
                    "_job_label":"PART1 OF 2 - SELECTED CONTOURS",
                    "_job_note":"Run PART1 first. Keep the same XY work zero for PART2."})
                cfg2=dict(cfg);cfg2.update({
                    "_xy_origin_override":common_origin,
                    "_job_label":"PART2 OF 2 - REMAINING CONTOURS",
                    "_job_note":"Before PART2: replace the end mill and re-zero Z only; do not change XY work zero.",
                    "accum_distance_m":cfg.get("accum_distance_m",0.0)+part1_m,
                    "accum_time_min":cfg.get("accum_time_min",0.0)+part1_min})
                code1=generate_gcode(
                    part1,cfg1,
                    lambda value,message:progress.set_progress(48+value*.25,f"PART1 · {message}") if progress else None)
                code2=generate_gcode(
                    part2,cfg2,
                    lambda value,message:progress.set_progress(73+value*.25,f"PART2 · {message}") if progress else None)
                self.gcode_parts=[("PART1",code1),("PART2",code2)]
                self.gcode=("(===== PART1: SELECTED CONTOURS =====)\n"+code1+
                            "\n\n(===== PART2: REMAINING CONTOURS =====)\n"+code2)
            else:
                code=generate_gcode(
                    self.contours,cfg,
                    lambda value,message:progress.set_progress(48+value*.50,message) if progress else None)
                self.gcode_parts=[("FULL",code)];self.gcode=code
            self.gcode_split_mode=bool(split_selected)
            self.gcode_signature=requested_signature
            self.text.delete("1.0","end"); self.text.insert("1.0",self.gcode)
            metres, minutes, total_m, total_min = machining_report(
                self.contours,cfg,
                lambda value,message:progress.set_progress(98+value*.02,message) if progress else None)
            self.gcode_job_minutes=minutes
            simulation_moves=[]
            for _,code in self.gcode_parts:simulation_moves.extend(parse_gcode_moves(code))
            rapid_mm=sum(math.hypot(m.end[0]-m.start[0],m.end[1]-m.start[1]) for m in simulation_moves if m.rapid)
            rapid_seconds=sum(m.seconds for m in simulation_moves if m.rapid)
            lead_note=f" | 리드인 중심 자동 {center_leads}개" if center_leads else ""
            split_note=(f" | PART1 {len(part1)}개 / PART2 {len(part2)}개" if split_selected else "")
            self.status.set(f"이번 {metres:.3f}m / {minutes:.1f}분{split_note} | 급속 XY {rapid_mm/1000:.3f}m / {rapid_seconds:.1f}초 | 작업 후 누적 {total_m:.3f}m{lead_note}")
            progress.set_progress(100,"G-code 생성 완료")
        except Exception as exc:
            if progress:progress.close();progress=None
            messagebox.showerror("생성 오류",str(exc))
        finally:
            if progress:progress.close()

    def run_path_check(self):
        if not self.contours:
            messagebox.showinfo("경로 검사","먼저 DXF를 열어 주세요."); return
        progress:Optional[ProgressDialog]=None
        try:
            cfg=self.config();tool_d=cfg["tool_d"];auto_trim=cfg.get("auto_trim",False)
            active=[x for x in self.contours if x.enabled]
            excluded_count=sum(c.safety_excluded for c in active)
            progress=ProgressDialog(self,"경로 안전검사")
            collision_map=tool_sweep_collisions(
                active,tool_d,auto_trim,
                lambda value,message:progress.set_progress(value*.65,message) if progress else None)
            errors=[];warnings=[]
            for i,c in enumerate(active,1):
                progress.set_progress(65+34*i/max(len(active),1),f"윤곽 안전검사 {i}/{len(active)}")
                es,ws=contour_toolpath_issues(c,tool_d,auto_trim)
                es=list(es)+collision_map.get(id(c),[])
                errors += [f"윤곽 {i} / Layer {c.layer}: {x}" for x in es]
                warnings += [f"윤곽 {i} / Layer {c.layer}: {x}" for x in ws]
            progress.set_progress(100,"경로 안전검사 완료");progress.close();progress=None
        except Exception as exc:
            if progress:progress.close()
            messagebox.showerror("설정 오류",str(exc));return
        self.redraw()
        if not errors and not warnings:
            note=f"\n안전검사 제외: {excluded_count}개" if excluded_count else ""
            messagebox.showinfo("경로 안전검사","공구 보정경로에서 이상을 찾지 못했습니다."+note)
        else:
            report=[]
            if errors: report.append("[G-code 생성 차단]\n"+"\n".join(errors[:12]))
            if warnings: report.append("[확인 필요]\n"+"\n".join(warnings[:12]))
            if excluded_count:report.append(f"[검사 제외]\n선택 윤곽 {excluded_count}개")
            messagebox.showwarning("경로 안전검사","\n\n".join(report))

    def save_gcode(self):
        try:cfg=self.config();current_signature=self.job_signature(cfg)
        except Exception as exc:messagebox.showerror("설정 오류",str(exc));return
        if not self.gcode or self.gcode_signature!=current_signature:self.make_gcode(split_selected=self.gcode_split_mode)
        if not self.gcode: return
        base=default_gcode_filename(self.part_objects,self.filename,self.contours,
                                    cfg["tool_d"],cfg["stock"],self.gcode_job_minutes)
        fn=filedialog.asksaveasfilename(defaultextension=".nc",initialfile=base,filetypes=[("G-code","*.nc *.gcode *.tap"),("All","*.*")])
        if fn:
            if len(self.gcode_parts)==2:
                saved=[]
                for part_fn,(_,code) in zip(split_gcode_paths(fn),self.gcode_parts):
                    with open(part_fn,"w",encoding="ascii",errors="replace",newline="\n") as f:f.write(code)
                    saved.append(part_fn)
                self.status.set(f"2분할 저장 완료: {saved[0]} / {saved[1]}")
                messagebox.showinfo("2분할 G-code 저장",
                                    f"PART1과 PART2를 따로 저장했습니다.\n\n{saved[0]}\n{saved[1]}\n\n"
                                    "PART1 완료 후 엔드밀을 교체하고 Z 원점만 다시 잡은 뒤 PART2를 실행하세요.\nXY 원점은 바꾸지 마세요.")
            else:
                code=self.gcode_parts[0][1] if self.gcode_parts else self.gcode
                with open(fn,"w",encoding="ascii",errors="replace",newline="\n") as f:f.write(code)
                self.status.set(f"저장 완료: {fn}")

    def open_3d(self):
        try:cfg=self.config();current_signature=self.job_signature(cfg)
        except Exception as exc:messagebox.showerror("설정 오류",str(exc));return
        if not self.gcode or self.gcode_signature!=current_signature:
            self.make_gcode(split_selected=self.gcode_split_mode)
            if not self.gcode or self.gcode_signature!=current_signature:return
        else:self.status.set("검사 완료된 G-code 재사용 · 시뮬레이션 바로 열기")
        moves=[]
        for _,code in self.gcode_parts or [("FULL",self.gcode)]:moves.extend(parse_gcode_moves(code))
        if not moves:
            messagebox.showerror("3D 시뮬레이션","표시할 G0/G1 이동을 찾지 못했습니다.");return
        Toolpath3D(self,moves,cfg)


if __name__ == "__main__":
    mp.freeze_support()
    if "--apply-update" in sys.argv:
        index=sys.argv.index("--apply-update")
        if len(sys.argv)<index+4:raise SystemExit(2)
        raise SystemExit(apply_update_process(os.path.abspath(sys.executable),sys.argv[index+1],
                                              int(sys.argv[index+2]),sys.argv[index+3]))
    cleanup_path=None
    if "--cleanup-update" in sys.argv:
        index=sys.argv.index("--cleanup-update")
        if len(sys.argv)>index+1:cleanup_path=sys.argv[index+1]
    if cleanup_path:cleanup_update_file(cleanup_path)
    App().mainloop()
