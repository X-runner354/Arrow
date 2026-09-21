"""游戏状态机（纯逻辑，不依赖任何图形库）。

把所有“点哪个箭头会发生什么”的规则集中在这里，方便单元测试。
界面层（main.py）只负责把 ``Game`` 的状态画出来并把鼠标点击转交给它。
"""

from __future__ import annotations

from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from .board import Arrow, Board, Direction, find_solution
from .levels import LEVELS, build_board


class GameState(Enum):
    START = "START"                 # 开始界面
    PLAYING = "PLAYING"             # 游戏中
    LEVEL_COMPLETE = "LEVEL_COMPLETE"  # 当前关通关
    FAILED = "FAILED"               # 失误耗尽，本关失败
    ALL_COMPLETE = "ALL_COMPLETE"   # 全部关卡通关


class ClickResult:
    """点击一格后返回给界面层的结果，用于驱动动画。"""

    def __init__(self, action: str, arrow: Optional[Arrow] = None,
                 blocker: Optional[Arrow] = None, message: str = ""):
        self.action = action        # "flew" | "blocked" | "empty" | "ignored"
        self.arrow = arrow
        self.blocker = blocker
        self.message = message

    def __repr__(self) -> str:
        return f"ClickResult(action={self.action!r}, arrow={self.arrow}, blocker={self.blocker})"


class Game:
    """一箭又一箭游戏逻辑。"""

    def __init__(self, levels: Optional[List[Dict[str, Any]]] = None):
        self.levels = levels if levels is not None else LEVELS
        self.state = GameState.START
        self.current_level_idx = 0
        self.board: Optional[Board] = None
        self.max_mistakes = 0
        self.mistakes_left = 0
        self.score = 0
        self.elapsed = 0.0  # 由界面层累加秒数
        self._history: List[Arrow] = []       # 已消除箭头（用于撤销）
        self._level_start_score = 0
        self._level_time = 0.0
        self._custom_level: Optional[Dict[str, Any]] = None  # 随机关卡用

    # ---- 关卡加载 ----
    def _level(self) -> Dict[str, Any]:
        if self._custom_level is not None:
            return self._custom_level
        return self.levels[self.current_level_idx]

    def start_game(self) -> None:
        """从第 1 关开始。"""
        self.current_level_idx = 0
        self._custom_level = None
        self.score = 0
        self._load_level(0)

    def start_custom_level(self, level: Dict[str, Any]) -> None:
        """开始一个随机关卡。"""
        self._custom_level = level
        self._load_level(0, level=level)

    def _load_level(self, idx: int, level: Optional[Dict[str, Any]] = None) -> None:
        lv = level if level is not None else self.levels[idx]
        self.current_level_idx = idx
        self.board = build_board(lv)
        self.max_mistakes = lv["max_mistakes"]
        self.mistakes_left = self.max_mistakes
        self._history = []
        self._level_start_score = self.score
        self._level_time = 0.0
        self.state = GameState.PLAYING

    # ---- 玩家操作 ----
    def click(self, r: int, c: int) -> ClickResult:
        """点击棋盘 (r, c) 格。"""
        if self.state != GameState.PLAYING or self.board is None:
            return ClickResult("ignored", message="当前不可操作")
        arrow = self.board.get(r, c)
        if arrow is None:
            return ClickResult("empty", message="该格无箭头")

        if self.board.can_fly_out(arrow):
            self.board.remove(arrow)
            self._history.append(arrow)
            self.score += 10
            if self.board.is_empty():
                self.score += self.mistakes_left * 2  # 剩余失误奖励
                if self._is_last_level():
                    self.state = GameState.ALL_COMPLETE
                else:
                    self.state = GameState.LEVEL_COMPLETE
            return ClickResult("flew", arrow=arrow, message="箭头飞出棋盘")
        else:
            self.mistakes_left -= 1
            blocker = self.board.first_blocker(arrow)
            if self.mistakes_left <= 0:
                self.mistakes_left = 0
                self.state = GameState.FAILED
            return ClickResult("blocked", arrow=arrow, blocker=blocker,
                               message="前方有箭头阻挡")

    def restart_level(self) -> None:
        """重新开始当前关卡，恢复初始布局与失误数（得分回退到本关开始时）。"""
        if self._custom_level is not None:
            self._load_level(0, level=self._custom_level)
        else:
            self._load_level(self.current_level_idx)

    def next_level(self) -> None:
        """进入下一关。"""
        if self._custom_level is not None:
            # 随机关卡通完后回到开始界面
            self._custom_level = None
            self.state = GameState.START
            return
        nxt = self.current_level_idx + 1
        if nxt >= len(self.levels):
            self.state = GameState.ALL_COMPLETE
            return
        self._load_level(nxt)

    def back_to_menu(self) -> None:
        self.state = GameState.START
        self._custom_level = None

    # ---- 扩展：撤销 ----
    def undo(self) -> bool:
        """撤销上一次成功消除，恢复该箭头（不恢复失误，因为成功消除不消耗失误）。"""
        if self.state != GameState.PLAYING or not self._history or self.board is None:
            return False
        arrow = self._history.pop()
        self.board.add(arrow)
        self.score = max(0, self.score - 10)
        return True

    # ---- 扩展：提示 ----
    def hint(self) -> Optional[Tuple[int, int]]:
        """返回一个当前可飞出箭头的坐标，没有则返回 None。"""
        if self.board is None:
            return None
        for a in self.board.all_arrows():
            if self.board.can_fly_out(a):
                return a.pos
        return None

    # ---- 扩展：自动求解（演示用）----
    def solution(self) -> Optional[List[Arrow]]:
        if self.board is None:
            return None
        return find_solution(self.board)

    # ---- 查询 ----
    def arrows_left(self) -> int:
        return 0 if self.board is None else self.board.count()

    def level_name(self) -> str:
        return self._level()["name"]

    def _is_last_level(self) -> bool:
        if self._custom_level is not None:
            # 随机关卡通关后按“下一关”回到菜单，故不视为最后一关
            return False
        return self.current_level_idx >= len(self.levels) - 1

    def total_levels(self) -> int:
        return len(self.levels)
