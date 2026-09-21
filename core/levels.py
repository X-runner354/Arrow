"""关卡定义、字符串地图解析、随机可通关关卡生成器。

关卡用字符串地图直观书写，字符含义：
    '.' 空格   '^' 上   'v' 下   '<' 左   '>' 右

所有手工关卡在导入时都会经 ``is_solvable`` 校验，确保存在合法通关顺序。
``random_solvable_level`` 用“反向构造”生成保证可通关的随机关卡：
从空棋盘起不断放入“相对当前已放箭头可飞出”的箭头，其逆序即为合法消除顺序。
"""

from __future__ import annotations

import random
from typing import List, Dict, Any

from .board import Arrow, Board, Direction, is_solvable


_CHAR_TO_DIR = {"^": Direction.UP, "v": Direction.DOWN, "<": Direction.LEFT, ">": Direction.RIGHT}


def parse_map(rows_text: List[str]) -> Dict[str, Any]:
    """把字符串地图解析成 {rows, cols, arrows}。"""
    rows = len(rows_text)
    cols = max(len(r) for r in rows_text)
    arrows: List[Arrow] = []
    for r, line in enumerate(rows_text):
        for c, ch in enumerate(line):
            if ch in _CHAR_TO_DIR:
                arrows.append(Arrow(r, c, _CHAR_TO_DIR[ch]))
            # 其余字符（含 '.'、空格、补齐位）视为空格
    return {"rows": rows, "cols": cols, "arrows": arrows}


# ---- 手工关卡（由易到难）----
# 每个元素: (名称, 地图字符串列表, 最大失误次数)
_RAW_LEVELS: List[Dict[str, Any]] = [
    {
        "name": "第 1 关 · 热身",
        "max_mistakes": 5,
        "map": [
            ">..",
            ".^.",
            "..<",
        ],
    },
    {
        "name": "第 2 关 · 列车",
        "max_mistakes": 4,
        "map": [
            ">>..",
            "....",
            "..<<",
            "....",
        ],
    },
    {
        "name": "第 3 关 · 让路",
        "max_mistakes": 4,
        "map": [
            ">v.",
            "...",
            ".<<",
        ],
    },
    {
        "name": "第 4 关 · 十字",
        "max_mistakes": 4,
        "map": [
            "..v..",
            ".....",
            "<...>",
            ".>>>.",
            "..v..",
        ],
    },
    {
        "name": "第 5 关 · 穿梭",
        "max_mistakes": 5,
        "map": [
            ">v...",
            ".....",
            "..>>>",
            ".....",
            "..<<.",
        ],
    },
    {
        "name": "第 6 关 · 迷阵",
        "max_mistakes": 6,
        "map": [
            "v>....",
            "......",
            "..>>>.",
            "......",
            ".<<<..",
            "....^.",
        ],
    },
]


def _build_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_map(raw["map"])
    return {
        "name": raw["name"],
        "rows": parsed["rows"],
        "cols": parsed["cols"],
        "arrows": parsed["arrows"],
        "max_mistakes": raw["max_mistakes"],
    }


LEVELS: List[Dict[str, Any]] = [_build_raw(r) for r in _RAW_LEVELS]


def build_board(level: Dict[str, Any]) -> Board:
    """由关卡描述构造棋盘。"""
    return Board(level["rows"], level["cols"], level["arrows"])


def validate_levels(levels: List[Dict[str, Any]] = LEVELS) -> List[Dict[str, Any]]:
    """校验所有关卡可通关，返回不可通关关卡列表（空列表表示全部通过）。"""
    bad = []
    for lv in levels:
        b = build_board(lv)
        if not is_solvable(b):
            bad.append(lv)
    return bad


def random_solvable_level(
    rows: int = 5,
    cols: int = 5,
    count: int = 8,
    max_mistakes: int = 5,
    seed: Any = None,
) -> Dict[str, Any]:
    """反向构造一个保证可通关的随机关卡。

    不断在空格随机放置“相对当前棋盘可飞出”的箭头，放置顺序的逆序即合法消除顺序。
    """
    rng = random.Random(seed)
    board = Board(rows, cols)
    placed: List[Arrow] = []
    dirs = list(Direction)
    attempts = 0
    max_attempts = max(count * 40, 200)
    while len(placed) < count and attempts < max_attempts:
        attempts += 1
        r = rng.randrange(rows)
        c = rng.randrange(cols)
        if (r, c) in board.arrows:
            continue
        d = rng.choice(dirs)
        a = Arrow(r, c, d)
        if board.can_fly_out(a):
            board.add(a)
            placed.append(a)
    return {
        "name": f"随机关卡 ({len(placed)} 箭)",
        "rows": rows,
        "cols": cols,
        "arrows": placed,
        "max_mistakes": max_mistakes,
    }


# 导入时自检：若有手工关卡不可通关，抛错以便尽早发现设计问题。
_bad = validate_levels()
if _bad:
    names = ", ".join(lv["name"] for lv in _bad)
    raise RuntimeError(f"以下关卡不可通关，请检查设计: {names}")
