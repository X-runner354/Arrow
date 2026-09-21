"""一箭又一箭 —— Pygame 主程序。

运行：
    py main.py        (Windows)
    python main.py    (其他平台)

操作：
    鼠标左键点击箭头 / 按钮
    R 重新开始本关   H 提示   U 撤销   ESC 返回菜单/退出
    SPACE / Enter   下一关（通关时）
"""

from __future__ import annotations

import math
import sys
from typing import Optional, Tuple, List

import pygame

from core import Game, GameState, Direction, Arrow, Board, random_solvable_level, LEVELS, build_board
from core.board import find_solution
import ui
from ui import Colors, WINDOW_W, WINDOW_H, board_layout, cell_at_pos, cell_center, draw_arrow, draw_board, draw_hud, draw_text, font, make_button_row, Button
from sound import SoundManager


# ---------------- 颜色插值 ----------------
def lerp_color(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


# ---------------- 动画 ----------------
class FlyOutAnim:
    """箭头沿方向飞出棋盘并淡出。"""

    def __init__(self, arrow: Arrow, origin: Tuple[int, int], cell_size: int,
                 rows: int, cols: int):
        self.arrow = arrow
        self.cell_size = cell_size
        self.t = 0.0
        self.duration = 0.38
        self.start = cell_center(arrow.row, arrow.col, origin, cell_size)
        d = arrow.direction
        dx, dy = ui._DIR_VEC[d]
        # 飞到棋盘外：先到边界再加一格余量
        if d == Direction.UP:
            edge = origin[1]
        elif d == Direction.DOWN:
            edge = origin[1] + rows * cell_size
        elif d == Direction.LEFT:
            edge = origin[0]
        else:
            edge = origin[0] + cols * cell_size
        if dx != 0:
            travel = abs(edge - self.start[0]) + cell_size * 1.2
        else:
            travel = abs(edge - self.start[1]) + cell_size * 1.2
        self.end = (self.start[0] + dx * travel, self.start[1] + dy * travel)

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t >= self.duration

    def draw(self, surface: pygame.Surface) -> None:
        p = min(1.0, self.t / self.duration)
        ease = 1 - (1 - p) ** 3
        x = self.start[0] + (self.end[0] - self.start[0]) * ease
        y = self.start[1] + (self.end[1] - self.start[1]) * ease
        color = lerp_color(Colors.ARROW, Colors.BG, p)
        edge_c = lerp_color(Colors.ARROW_EDGE, Colors.BG, p)
        draw_arrow(surface, (int(x), int(y)), self.arrow.direction, color,
                   self.cell_size, edge_color=edge_c, scale=1.0 + p * 0.25)


class CollisionAnim:
    """箭头向阻挡方向小幅位移后弹回 + 红色闪烁。"""

    def __init__(self, arrow: Arrow, origin: Tuple[int, int], cell_size: int):
        self.arrow = arrow
        self.cell_size = cell_size
        self.t = 0.0
        self.duration = 0.34
        self.center = cell_center(arrow.row, arrow.col, origin, cell_size)

    @property
    def pos(self) -> Tuple[int, int]:
        return self.arrow.pos

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t >= self.duration

    def draw(self, surface: pygame.Surface) -> None:
        p = min(1.0, self.t / self.duration)
        dx, dy = ui._DIR_VEC[self.arrow.direction]
        amp = self.cell_size * 0.20 * (1 - p)
        off = amp * math.sin(p * math.pi * 5)
        x = self.center[0] + dx * off
        y = self.center[1] + dy * off
        flash = max(0.0, math.sin(p * math.pi * 4))
        color = lerp_color(Colors.ARROW, Colors.COLLIDE, flash)
        edge_c = lerp_color(Colors.ARROW_EDGE, Colors.COLLIDE, flash)
        draw_arrow(surface, (int(x), int(y)), self.arrow.direction, color,
                   self.cell_size, edge_color=edge_c)


# ---------------- 应用 ----------------
class App:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.SCALED, vsync=1)
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.game = Game()
        self.animations: List = []
        self.hidden: set = set()
        self.hint_pos: Optional[Tuple[int, int]] = None
        self.flash_msg = ""
        self.flash_msg_t = 0.0
        self.last_state = self.game.state
        self.show_solution = False
        self.solution_steps: List[Arrow] = []
        self.solution_idx = 0
        self.solution_timer = 0.0

    # ---- 工具 ----
    def current_layout(self):
        if self.game.board is None:
            return None
        return board_layout(self.game.board.rows, self.game.board.cols)

    def push_flash(self, msg: str) -> None:
        self.flash_msg = msg
        self.flash_msg_t = 1.4

    def clear_animations(self) -> None:
        self.animations.clear()
        self.hidden.clear()

    # ---- 事件 ----
    def handle_click(self, pos: Tuple[int, int]) -> None:
        st = self.game.state
        if st == GameState.START:
            self.handle_start_click(pos)
        elif st == GameState.PLAYING:
            self.handle_playing_click(pos)
        elif st == GameState.LEVEL_COMPLETE:
            self.handle_level_complete_click(pos)
        elif st == GameState.FAILED:
            self.handle_failed_click(pos)
        elif st == GameState.ALL_COMPLETE:
            self.handle_all_complete_click(pos)

    def handle_start_click(self, pos) -> None:
        for btn in self.start_buttons():
            if btn.hit(pos):
                self.sound.click()
                if btn.key.startswith("lv"):
                    idx = int(btn.key[2:])
                    self.game.score = 0
                    self.game.current_level_idx = idx
                    self.game._custom_level = None
                    self.game._load_level(idx)
                    self.clear_animations()
                elif btn.key == "random":
                    lv = random_solvable_level(5, 5, 8, max_mistakes=5)
                    self.game.score = 0
                    self.game.start_custom_level(lv)
                    self.clear_animations()
                elif btn.key == "start":
                    self.game.start_game()
                    self.clear_animations()
                return

    def handle_playing_click(self, pos) -> None:
        for btn in self.playing_buttons():
            if btn.hit(pos):
                self.sound.click()
                if btn.key == "restart":
                    self.game.restart_level()
                    self.clear_animations()
                    self.hint_pos = None
                elif btn.key == "hint":
                    self.hint_pos = self.game.hint()
                    if self.hint_pos is None:
                        self.push_flash("没有可提示的箭头")
                elif btn.key == "undo":
                    if self.game.undo():
                        self.hint_pos = None
                    else:
                        self.push_flash("无法撤销")
                elif btn.key == "menu":
                    self.game.back_to_menu()
                    self.clear_animations()
                elif btn.key == "solve":
                    self.toggle_solve()
                return
        # 棋盘点击
        layout = self.current_layout()
        if layout is None:
            return
        origin, cell_size, _, _ = layout
        cell = cell_at_pos(pos, origin, cell_size,
                           self.game.board.rows, self.game.board.cols)
        if cell is None:
            return
        self.hint_pos = None
        r, c = cell
        res = self.game.click(r, c)
        if res.action == "flew":
            self.sound.fly()
            self.animations.append(FlyOutAnim(res.arrow, origin, cell_size,
                                              self.game.board.rows, self.game.board.cols))
        elif res.action == "blocked":
            self.sound.collide()
            anim = CollisionAnim(res.arrow, origin, cell_size)
            self.animations.append(anim)
            self.hidden.add(anim.pos)
            self.push_flash("前方有箭头阻挡！失误 -1")
        elif res.action == "empty":
            self.push_flash("该格没有箭头")

    def toggle_solve(self) -> None:
        if self.show_solution:
            self.show_solution = False
            self.solution_steps = []
            return
        sol = self.game.solution()
        if sol:
            self.show_solution = True
            self.solution_steps = sol
            self.solution_idx = 0
            self.solution_timer = 0.0
            self.push_flash("AI 自动演示中…")
        else:
            self.push_flash("当前局面无解")

    def handle_level_complete_click(self, pos) -> None:
        for btn in self.complete_buttons():
            if btn.hit(pos):
                self.sound.click()
                if btn.key == "next":
                    self.game.next_level()
                    self.clear_animations()
                    self.hint_pos = None
                elif btn.key == "menu":
                    self.game.back_to_menu()
                    self.clear_animations()
                return

    def handle_failed_click(self, pos) -> None:
        for btn in self.failed_buttons():
            if btn.hit(pos):
                self.sound.click()
                if btn.key == "restart":
                    self.game.restart_level()
                    self.clear_animations()
                elif btn.key == "menu":
                    self.game.back_to_menu()
                    self.clear_animations()
                return

    def handle_all_complete_click(self, pos) -> None:
        for btn in self.all_complete_buttons():
            if btn.hit(pos):
                self.sound.click()
                if btn.key == "menu":
                    self.game.back_to_menu()
                    self.clear_animations()
                return

    # ---- 按钮集 ----
    def start_buttons(self) -> List[Button]:
        btns = []
        # 关卡选择 1..6
        n = len(LEVELS)
        w, h, gap = 64, 50, 12
        total = n * w + (n - 1) * gap
        x = (WINDOW_W - total) // 2
        y = 360
        for i in range(n):
            btns.append(Button((x, y, w, h), str(i + 1), f"lv{i}"))
            x += w + gap
        # 开始 / 随机
        btns += make_button_row(440, [("开始游戏", "start"), ("随机关卡", "random")],
                                width=160, height=46, gap=20)
        return btns

    def playing_buttons(self) -> List[Button]:
        return make_button_row(640,
                               [("重新开始", "restart"), ("提示", "hint"),
                                ("撤销", "undo"), ("AI演示", "solve"), ("返回菜单", "menu")],
                               width=110, height=40, gap=12)

    def complete_buttons(self) -> List[Button]:
        return make_button_row(420, [("下一关", "next"), ("返回菜单", "menu")],
                               width=160, height=46, gap=20)

    def failed_buttons(self) -> List[Button]:
        return make_button_row(420, [("重新开始", "restart"), ("返回菜单", "menu")],
                               width=160, height=46, gap=20)

    def all_complete_buttons(self) -> List[Button]:
        return make_button_row(420, [("返回菜单", "menu")],
                               width=180, height=46, gap=20)

    # ---- 更新 ----
    def update(self, dt: float) -> None:
        # 计时
        if self.game.state == GameState.PLAYING:
            self.game.elapsed += dt
        # 状态转换音效
        if self.game.state != self.last_state:
            if self.game.state == GameState.LEVEL_COMPLETE:
                self.sound.win()
            elif self.game.state == GameState.ALL_COMPLETE:
                self.sound.win()
            elif self.game.state == GameState.FAILED:
                self.sound.lose()
            self.last_state = self.game.state
        # 动画
        done = []
        for a in self.animations:
            if a.update(dt):
                done.append(a)
        for a in done:
            self.animations.remove(a)
            if isinstance(a, CollisionAnim):
                self.hidden.discard(a.pos)
        # flash 消息
        if self.flash_msg_t > 0:
            self.flash_msg_t -= dt
            if self.flash_msg_t <= 0:
                self.flash_msg = ""
        # AI 演示
        if self.show_solution and self.game.state == GameState.PLAYING:
            self.solution_timer += dt
            if self.solution_timer >= 0.55 and self.solution_idx < len(self.solution_steps):
                self.solution_timer = 0.0
                a = self.solution_steps[self.solution_idx]
                self.solution_idx += 1
                layout = self.current_layout()
                if layout and self.game.board and self.game.board.get(a.row, a.col) is not None:
                    res = self.game.click(a.row, a.col)
                    if res.action == "flew" and layout:
                        origin, cell_size, _, _ = layout
                        self.animations.append(FlyOutAnim(res.arrow, origin, cell_size,
                                                          self.game.board.rows, self.game.board.cols))
                        self.sound.fly()
            if self.solution_idx >= len(self.solution_steps):
                self.show_solution = False

    # ---- 绘制 ----
    def draw(self) -> None:
        self.screen.fill(Colors.BG)
        st = self.game.state
        if st == GameState.START:
            self.draw_start()
        else:
            self.draw_game()
            if st == GameState.LEVEL_COMPLETE:
                self.draw_overlay("本关通关！", Colors.OK, self.complete_buttons(),
                                  sub=f"得分 {self.game.score}   用时 {self.game.elapsed:.1f}s")
            elif st == GameState.FAILED:
                self.draw_overlay("本关失败", Colors.BAD, self.failed_buttons(),
                                  sub="失误次数已耗尽，再试一次吧")
            elif st == GameState.ALL_COMPLETE:
                self.draw_overlay("全部通关！", Colors.ACCENT, self.all_complete_buttons(),
                                  sub=f"总分 {self.game.score}   用时 {self.game.elapsed:.1f}s")
        pygame.display.flip()

    def draw_start(self) -> None:
        # 背景装饰箭头
        self.screen.fill(Colors.BG)
        pygame.draw.rect(self.screen, Colors.BG2, (0, 0, WINDOW_W, 120))
        draw_text(self.screen, "一箭又一箭", (WINDOW_W // 2, 70), 56, Colors.ACCENT,
                  bold=True, center=True)
        draw_text(self.screen, "点击箭头，让它飞出棋盘 —— 前方有箭头阻挡则不能飞出",
                  (WINDOW_W // 2, 175), 22, Colors.TEXT_DIM, center=True)
        draw_text(self.screen, "选择关卡", (WINDOW_W // 2, 320), 24, Colors.TEXT, bold=True, center=True)

        # 规则说明
        rules = [
            "· 棋盘上的箭头有 ↑ ↓ ← → 四种方向",
            "· 点击箭头：若它与边界之间无其他箭头，则飞出消除",
            "· 若前方有箭头阻挡，不能消除，并消耗 1 次失误",
            "· 清空本关全部箭头即通关；失误耗尽则失败",
        ]
        y = 530
        for line in rules:
            draw_text(self.screen, line, (WINDOW_W // 2, y), 19, Colors.TEXT_DIM, center=True)
            y += 28
        draw_text(self.screen, "快捷键：R 重新开始   H 提示   U 撤销   ESC 返回菜单",
                  (WINDOW_W // 2, WINDOW_H - 30), 17, Colors.TEXT_DIM, center=True)

        for btn in self.start_buttons():
            btn.update_hover(pygame.mouse.get_pos())
            btn.draw(self.screen)

    def draw_game(self) -> None:
        layout = self.current_layout()
        # HUD
        label = ""
        if self.game._custom_level is not None:
            label = self.game.level_name()
        draw_hud(self.screen, self.game, label)

        if layout is None:
            return
        origin, cell_size, bw, bh = layout
        board = self.game.board
        if board is None:
            return
        draw_board(self.screen, board, origin, cell_size,
                   hint_pos=self.hint_pos, hidden=self.hidden)

        # 动画
        for a in self.animations:
            a.draw(self.screen)

        # flash 消息
        if self.flash_msg:
            alpha = min(1.0, self.flash_msg_t / 0.3) if self.flash_msg_t < 0.3 else 1.0
            col = lerp_color(Colors.BG, Colors.COLLIDE, alpha)
            draw_text(self.screen, self.flash_msg, (WINDOW_W // 2, 130), 22, col,
                      bold=True, center=True)

        # 按钮
        if self.game.state == GameState.PLAYING:
            for btn in self.playing_buttons():
                btn.update_hover(pygame.mouse.get_pos())
                btn.draw(self.screen)

        # 失误数警示
        if self.game.mistakes_left <= 1 and self.game.state == GameState.PLAYING:
            draw_text(self.screen, "失误即将耗尽！", (WINDOW_W // 2, WINDOW_H - 80), 20,
                      Colors.BAD, bold=True, center=True)

    def draw_overlay(self, title: str, color, buttons: List[Button], sub: str = "") -> None:
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((10, 12, 20, 170))
        self.screen.blit(overlay, (0, 0))
        box_w, box_h = 460, 220
        box = pygame.Rect((WINDOW_W - box_w) // 2, 300, box_w, box_h)
        pygame.draw.rect(self.screen, Colors.PANEL, box, border_radius=14)
        pygame.draw.rect(self.screen, color, box, 3, border_radius=14)
        draw_text(self.screen, title, (box.centerx, box.top + 50), 40, color,
                  bold=True, center=True)
        if sub:
            draw_text(self.screen, sub, (box.centerx, box.top + 110), 22, Colors.TEXT, center=True)
        for btn in buttons:
            btn.update_hover(pygame.mouse.get_pos())
            btn.draw(self.screen)

    # ---- 主循环 ----
    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game.state == GameState.PLAYING:
                            self.game.back_to_menu()
                            self.clear_animations()
                        elif self.game.state == GameState.START:
                            running = False
                        else:
                            self.game.back_to_menu()
                            self.clear_animations()
                    elif event.key == pygame.K_r:
                        if self.game.state in (GameState.PLAYING, GameState.FAILED):
                            self.game.restart_level()
                            self.clear_animations()
                    elif event.key == pygame.K_h:
                        if self.game.state == GameState.PLAYING:
                            self.hint_pos = self.game.hint()
                    elif event.key == pygame.K_u:
                        if self.game.state == GameState.PLAYING:
                            self.game.undo()
                            self.hint_pos = None
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        if self.game.state == GameState.LEVEL_COMPLETE:
                            self.game.next_level()
                            self.clear_animations()
                            self.hint_pos = None
                        elif self.game.state == GameState.START:
                            self.game.start_game()
                            self.clear_animations()
            self.update(dt)
            self.draw()
        pygame.quit()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
