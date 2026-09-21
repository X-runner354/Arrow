"""棋盘、箭头与四向路径检测、可通关求解器。

设计要点
--------
* ``Arrow`` 用不可变 dataclass 表示，``direction`` 取自 ``Direction`` 枚举。
* ``Board`` 内部用 ``dict[(row, col)] -> Arrow`` 存箭头，查询/删除均为 O(1)。
* 路径检测只看“同一行或同一列、箭头与边界之间是否还有其他箭头”，
  与作业基础版判定一致。
* ``is_solvable`` / ``find_solution`` 用回溯 + 状态记忆求解，用于：
  ① 加载时校验关卡可通关；② 提示功能；③ AI 自动求解扩展。

一个重要性质：删除箭头只会“解除阻挡”，不会让原本可飞出的箭头变得被阻挡。
因此只要初始棋盘可通关，任意合法消除序列后剩余棋盘仍可通关，
即只要还有箭头就一定存在可飞出者——玩家不会陷入“有箭头却谁都飞不出去”的死局。
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Iterable, Optional, List, Dict, Tuple


class Direction(Enum):
    """箭头的四种方向。"""

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def delta(self) -> Tuple[int, int]:
        """返回 (d_row, d_col) 单位向量，UP 时 row 减小。"""
        return {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[self]

    @classmethod
    def from_str(cls, s: str) -> "Direction":
        """从字符串构造，兼容 'UP'/'U'/'上' 等写法。"""
        s = s.strip().upper()
        mapping = {
            "UP": cls.UP, "U": cls.UP, "上": cls.UP, "W": cls.UP,
            "DOWN": cls.DOWN, "D": cls.DOWN, "下": cls.DOWN, "S": cls.DOWN,
            "LEFT": cls.LEFT, "L": cls.LEFT, "左": cls.LEFT, "A": cls.LEFT,
            "RIGHT": cls.RIGHT, "R": cls.RIGHT, "右": cls.RIGHT, "D2": cls.RIGHT,
        }
        if s in mapping:
            return mapping[s]
        # 兼容箭头符号
        symbol_map = {"^": cls.UP, "v": cls.DOWN, "<": cls.LEFT, ">": cls.RIGHT}
        if s in symbol_map:
            return symbol_map[s]
        raise ValueError(f"无法识别的方向: {s!r}")


@dataclass(frozen=True)
class Arrow:
    """棋盘上的一个箭头。"""

    row: int
    col: int
    direction: Direction

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)


class Board:
    """矩形棋盘，存放箭头并提供路径检测。"""

    def __init__(self, rows: int, cols: int, arrows: Iterable[Arrow] = ()):
        if rows <= 0 or cols <= 0:
            raise ValueError("rows 和 cols 必须为正整数")
        self.rows = rows
        self.cols = cols
        self.arrows: Dict[Tuple[int, int], Arrow] = {}
        for a in arrows:
            if not self.in_bounds(a.row, a.col):
                raise ValueError(f"箭头越界: ({a.row}, {a.col})")
            if a.pos in self.arrows:
                raise ValueError(f"同一格存在多个箭头: {a.pos}")
            self.arrows[a.pos] = a

    # ---- 基础查询 ----
    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def get(self, r: int, c: int) -> Optional[Arrow]:
        return self.arrows.get((r, c))

    def is_empty(self) -> bool:
        return len(self.arrows) == 0

    def count(self) -> int:
        return len(self.arrows)

    def all_arrows(self) -> List[Arrow]:
        return list(self.arrows.values())

    # ---- 路径检测 ----
    def path_cells(self, arrow: Arrow) -> List[Tuple[int, int]]:
        """返回箭头前进方向上、到边界为止的所有格子（不含自身）。"""
        r, c = arrow.row, arrow.col
        d = arrow.direction
        if d == Direction.UP:
            return [(rr, c) for rr in range(r - 1, -1, -1)]
        if d == Direction.DOWN:
            return [(rr, c) for rr in range(r + 1, self.rows)]
        if d == Direction.LEFT:
            return [(r, cc) for cc in range(c - 1, -1, -1)]
        # RIGHT
        return [(r, cc) for cc in range(c + 1, self.cols)]

    def path_blocked(self, arrow: Arrow) -> bool:
        """箭头与边界之间是否存在其他箭头。"""
        return any(cell in self.arrows for cell in self.path_cells(arrow))

    def can_fly_out(self, arrow: Arrow) -> bool:
        return not self.path_blocked(arrow)

    def first_blocker(self, arrow: Arrow) -> Optional[Arrow]:
        """返回路径上离箭头最近的阻挡箭头（用于碰撞动画定位）。"""
        for cell in self.path_cells(arrow):
            if cell in self.arrows:
                return self.arrows[cell]
        return None

    # ---- 修改 ----
    def remove(self, arrow: Arrow) -> None:
        self.arrows.pop(arrow.pos, None)

    def add(self, arrow: Arrow) -> None:
        if not self.in_bounds(arrow.row, arrow.col):
            raise ValueError(f"箭头越界: {arrow.pos}")
        self.arrows[arrow.pos] = arrow

    def copy(self) -> "Board":
        b = Board(self.rows, self.cols)
        b.arrows = dict(self.arrows)
        return b

    # ---- 序列化（用于记忆化/调试）----
    def key(self) -> frozenset:
        return frozenset((a.row, a.col, a.direction) for a in self.arrows.values())


def is_solvable(board: Board) -> bool:
    """判断棋盘上的箭头能否全部消除（回溯 + 记忆化）。"""
    memo: set = set()
    return _is_solvable(board, memo)


def _is_solvable(board: Board, memo: set) -> bool:
    if board.is_empty():
        return True
    k = board.key()
    if k in memo:
        return False
    # 任选一个可飞出的箭头递归；若全部失败则记为不可解
    for a in board.all_arrows():
        if board.can_fly_out(a):
            board.remove(a)
            ok = _is_solvable(board, memo)
            board.add(a)  # 回溯
            if ok:
                return True
    memo.add(k)
    return False


def find_solution(board: Board) -> Optional[List[Arrow]]:
    """返回一种合法消除顺序（箭头列表），不可通关时返回 None。"""
    memo: set = set()
    path: List[Arrow] = []
    if _find_solution(board, path, memo):
        return path
    return None


def _find_solution(board: Board, path: List[Arrow], memo: set) -> bool:
    if board.is_empty():
        return True
    k = board.key()
    if k in memo:
        return False
    for a in board.all_arrows():
        if board.can_fly_out(a):
            board.remove(a)
            path.append(a)
            if _find_solution(board, path, memo):
                board.add(a)  # 恢复，保持外部 board 不变
                return True
            path.pop()
            board.add(a)
    memo.add(k)
    return False
