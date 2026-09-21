"""一箭又一箭 —— 单元测试（对应作业测试表 T01–T06）。

运行：
    py -m unittest tests.test_core
    或
    py -m unittest discover
"""

import unittest

from core.board import Arrow, Board, Direction, is_solvable, find_solution
from core.game import Game, GameState


def make_level(rows, cols, arrows, max_mistakes=3, name="测试关"):
    return {"name": name, "rows": rows, "cols": cols,
            "arrows": arrows, "max_mistakes": max_mistakes}


class TestPathDetection(unittest.TestCase):
    """直接测试 Board 的四向路径检测。"""

    def test_right_blocked(self):
        # → · · ↑ ·  第一个箭头朝右，右侧有箭头 → 被阻挡
        b = Board(1, 5, [Arrow(0, 0, Direction.RIGHT), Arrow(0, 3, Direction.UP)])
        self.assertTrue(b.path_blocked(b.get(0, 0)))
        self.assertFalse(b.can_fly_out(b.get(0, 0)))

    def test_right_free_at_edge(self):
        # ↑ · · · →  最后一个箭头朝右，右侧无箭头 → 可飞出
        b = Board(1, 5, [Arrow(0, 0, Direction.UP), Arrow(0, 4, Direction.RIGHT)])
        self.assertFalse(b.path_blocked(b.get(0, 4)))
        self.assertTrue(b.can_fly_out(b.get(0, 4)))

    def test_all_four_directions(self):
        # 中心箭头四向各放一个阻挡箭头（分别用独立棋盘构造）
        # 上方阻挡
        b1 = Board(3, 3, [Arrow(1, 1, Direction.UP), Arrow(0, 1, Direction.UP)])
        self.assertTrue(b1.path_blocked(b1.get(1, 1)))
        # 下方阻挡
        b2 = Board(3, 3, [Arrow(1, 1, Direction.DOWN), Arrow(2, 1, Direction.UP)])
        self.assertTrue(b2.path_blocked(b2.get(1, 1)))
        # 左方阻挡
        b3 = Board(3, 3, [Arrow(1, 1, Direction.LEFT), Arrow(1, 0, Direction.UP)])
        self.assertTrue(b3.path_blocked(b3.get(1, 1)))
        # 右方阻挡
        b4 = Board(3, 3, [Arrow(1, 1, Direction.RIGHT), Arrow(1, 2, Direction.UP)])
        self.assertTrue(b4.path_blocked(b4.get(1, 1)))


class TestGameT01T06(unittest.TestCase):
    """对应作业测试表 T01–T06。"""

    def _new_game(self, level):
        g = Game(levels=[level])
        g.start_game()
        return g

    # T01 点击前方无阻挡的箭头 → 箭头飞出棋盘并消失
    def test_T01_fly_out_when_unblocked(self):
        lv = make_level(3, 3, [Arrow(0, 0, Direction.RIGHT)], max_mistakes=3)
        g = self._new_game(lv)
        self.assertEqual(g.arrows_left(), 1)
        res = g.click(0, 0)
        self.assertEqual(res.action, "flew")
        self.assertEqual(g.arrows_left(), 0)
        self.assertIsNone(g.board.get(0, 0))

    # T02 点击前方有阻挡的箭头 → 箭头不消失，失误次数减 1
    def test_T02_blocked_consumes_mistake(self):
        lv = make_level(1, 3, [Arrow(0, 0, Direction.RIGHT), Arrow(0, 2, Direction.UP)],
                        max_mistakes=3)
        g = self._new_game(lv)
        before = g.mistakes_left
        res = g.click(0, 0)
        self.assertEqual(res.action, "blocked")
        self.assertIsNotNone(g.board.get(0, 0))   # 箭头仍在
        self.assertEqual(g.arrows_left(), 2)
        self.assertEqual(g.mistakes_left, before - 1)

    # T03 点击位于边缘且朝向棋盘外的箭头 → 正常消失，不发生越界错误
    def test_T03_edge_arrow_no_out_of_bounds(self):
        # 四个角分别朝外
        arrows = [
            Arrow(0, 0, Direction.LEFT),    # 左上角朝左
            Arrow(0, 2, Direction.RIGHT),   # 右上角朝右
            Arrow(2, 0, Direction.LEFT),    # 左下角朝左
            Arrow(2, 2, Direction.RIGHT),   # 右下角朝右
            Arrow(1, 0, Direction.UP),      # 左边朝上
            Arrow(1, 2, Direction.DOWN),    # 右边朝下
        ]
        lv = make_level(3, 3, arrows, max_mistakes=3)
        g = self._new_game(lv)
        for r, c in [(0, 0), (0, 2), (2, 0), (2, 2), (1, 0), (1, 2)]:
            res = g.click(r, c)
            self.assertEqual(res.action, "flew", f"({r},{c}) 应飞出: {res.action}")
        self.assertEqual(g.arrows_left(), 0)

    # T04 消除本关全部箭头 → 显示通关并进入下一关
    def test_T04_clear_all_advances_level(self):
        # 用两个简单关卡
        lv1 = make_level(3, 3, [Arrow(0, 0, Direction.RIGHT)], max_mistakes=3, name="L1")
        lv2 = make_level(3, 3, [Arrow(0, 0, Direction.DOWN)], max_mistakes=3, name="L2")
        g = Game(levels=[lv1, lv2])
        g.start_game()
        self.assertEqual(g.current_level_idx, 0)
        res = g.click(0, 0)
        self.assertEqual(res.action, "flew")
        self.assertEqual(g.state, GameState.LEVEL_COMPLETE)
        g.next_level()
        self.assertEqual(g.state, GameState.PLAYING)
        self.assertEqual(g.current_level_idx, 1)
        self.assertEqual(g.arrows_left(), 1)

    # T05 失误次数耗尽 → 显示失败并允许重新开始
    def test_T05_mistakes_exhausted_fails_and_restart(self):
        lv = make_level(1, 3, [Arrow(0, 0, Direction.RIGHT), Arrow(0, 2, Direction.UP)],
                        max_mistakes=2)
        g = self._new_game(lv)
        # 反复点被阻挡的 (0,0)
        r1 = g.click(0, 0)
        self.assertEqual(r1.action, "blocked")
        self.assertEqual(g.state, GameState.PLAYING)
        r2 = g.click(0, 0)
        self.assertEqual(r2.action, "blocked")
        self.assertEqual(g.state, GameState.FAILED)
        self.assertEqual(g.mistakes_left, 0)
        # 重新开始
        g.restart_level()
        self.assertEqual(g.state, GameState.PLAYING)
        self.assertEqual(g.mistakes_left, 2)
        self.assertEqual(g.arrows_left(), 2)

    # T06 游戏中重新开始 → 箭头布局和失误次数恢复
    def test_T06_restart_restores_state(self):
        lv = make_level(3, 3, [Arrow(0, 0, Direction.RIGHT), Arrow(2, 2, Direction.LEFT)],
                        max_mistakes=3)
        g = self._new_game(lv)
        # 消除一个、制造一次失误
        g.click(0, 0)  # 飞出
        # (2,2)< 路径 (2,1),(2,0) 空 → 也可飞出；改用阻挡场景
        lv2 = make_level(1, 3, [Arrow(0, 0, Direction.RIGHT), Arrow(0, 1, Direction.RIGHT),
                                Arrow(0, 2, Direction.UP)], max_mistakes=3)
        g = self._new_game(lv2)
        init_arrows = g.arrows_left()
        init_mistakes = g.mistakes_left
        g.click(0, 0)  # 被 (0,1) 阻挡 → 失误
        g.click(0, 2)  # 飞出
        self.assertEqual(g.arrows_left(), init_arrows - 1)
        self.assertEqual(g.mistakes_left, init_mistakes - 1)
        # 重新开始
        g.restart_level()
        self.assertEqual(g.arrows_left(), init_arrows)
        self.assertEqual(g.mistakes_left, init_mistakes)
        self.assertEqual(g.state, GameState.PLAYING)


class TestSolverAndLevels(unittest.TestCase):
    """求解器与全部手工关卡可通关。"""

    def test_all_levels_solvable(self):
        from core.levels import LEVELS, build_board
        for lv in LEVELS:
            b = build_board(lv)
            self.assertTrue(is_solvable(b), f"{lv['name']} 不可通关")
            sol = find_solution(b)
            self.assertIsNotNone(sol)
            self.assertEqual(len(sol), len(lv["arrows"]))

    def test_random_level_solvable(self):
        from core.levels import random_solvable_level, build_board
        for seed in range(10):
            lv = random_solvable_level(5, 5, 8, seed=seed)
            self.assertTrue(is_solvable(build_board(lv)), f"seed={seed} 不可通关")


if __name__ == "__main__":
    unittest.main(verbosity=2)
