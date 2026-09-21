"""一箭又一箭 —— 核心逻辑包。

本包只包含与图形界面无关的纯逻辑：棋盘、箭头、四向路径检测、
关卡定义、可通关求解器以及游戏状态机。这样便于单元测试。
"""

from .board import Direction, Arrow, Board, is_solvable, find_solution
from .levels import LEVELS, build_board, random_solvable_level, validate_levels
from .game import GameState, Game, ClickResult

__all__ = [
    "Direction",
    "Arrow",
    "Board",
    "is_solvable",
    "find_solution",
    "LEVELS",
    "build_board",
    "random_solvable_level",
    "validate_levels",
    "GameState",
    "Game",
    "ClickResult",
]
