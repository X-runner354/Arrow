"""界面绘制工具：颜色、字体、箭头/棋盘/HUD/按钮绘制、布局与坐标换算。

本模块只提供“把东西画到指定 surface 上”的纯函数，不含主循环和事件处理，
因此 main.py 和 make_screenshots.py 都可以复用它。
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, List

import pygame

from core.board import Arrow, Board, Direction

# ---------------- 颜色 ----------------
class Colors:
    BG = (30, 34, 48)
    BG2 = (44, 50, 70)
    PANEL = (54, 62, 88)
    GRID = (70, 80, 110)
    GRID_LIGHT = (60, 68, 96)
    ARROW = (96, 200, 255)
    ARROW_EDGE = (220, 245, 255)
    HINT = (255, 220, 90)
    COLLIDE = (255, 90, 90)
    TEXT = (235, 238, 245)
    TEXT_DIM = (170, 178, 200)
    ACCENT = (120, 220, 180)
    BTN = (70, 80, 115)
    BTN_HOVER = (96, 110, 155)
    BTN_TEXT = (235, 238, 245)
    OK = (110, 220, 140)
    BAD = (255, 110, 110)
    OVERLAY = (10, 12, 20)


# ---------------- 字体 ----------------
_FONT_CACHE: dict = {}

def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONT_CACHE:
        # 逗号分隔的候选名，pygame 会取第一个可用；含中文回退字体
        name = "microsoftyahei,microsoftyaheiui,simhei,msyh,arial,dejavusans"
        f = pygame.font.SysFont(name, size, bold=bold)
        _FONT_CACHE[key] = f
    return _FONT_CACHE[key]


# ---------------- 布局 ----------------
WINDOW_W = 980
WINDOW_H = 720
BOARD_AREA_TOP = 150
BOARD_AREA_BOTTOM = 600
BOARD_AREA_LEFT = 60
BOARD_AREA_RIGHT = 920


def board_layout(rows: int, cols: int) -> Tuple[Tuple[int, int], int, int, int]:
    """返回 (origin, cell_size, board_w, board_h)，棋盘水平居中。"""
    avail_w = BOARD_AREA_RIGHT - BOARD_AREA_LEFT
    avail_h = BOARD_AREA_BOTTOM - BOARD_AREA_TOP
    cell = max(20, min(avail_w // cols, avail_h // rows, 96))
    bw = cell * cols
    bh = cell * rows
    ox = (WINDOW_W - bw) // 2
    oy = BOARD_AREA_TOP + (avail_h - bh) // 2
    return (ox, oy), cell, bw, bh


def cell_at_pos(pos: Tuple[int, int], origin: Tuple[int, int], cell_size: int,
                rows: int, cols: int) -> Optional[Tuple[int, int]]:
    """屏幕坐标 -> 棋盘格 (r, c)，不在棋盘内返回 None。"""
    x, y = pos
    ox, oy = origin
    if x < ox or y < oy:
        return None
    c = (x - ox) // cell_size
    r = (y - oy) // cell_size
    if 0 <= r < rows and 0 <= c < cols:
        return (r, c)
    return None


def cell_center(r: int, c: int, origin: Tuple[int, int], cell_size: int) -> Tuple[int, int]:
    ox, oy = origin
    return (ox + c * cell_size + cell_size // 2, oy + r * cell_size + cell_size // 2)


# ---------------- 箭头绘制 ----------------
_DIR_VEC = {
    Direction.UP: (0, -1),
    Direction.DOWN: (0, 1),
    Direction.LEFT: (-1, 0),
    Direction.RIGHT: (1, 0),
}


def draw_arrow(surface: pygame.Surface, center: Tuple[int, int],
               direction: Direction, color: Tuple[int, int, int],
               cell_size: int, edge_color: Optional[Tuple[int, int, int]] = None,
               scale: float = 1.0) -> None:
    """画一个指向 direction 的箭头。scale 用于动画缩放。"""
    cx, cy = center
    dx, dy = _DIR_VEC[direction]
    px, py = -dy, dx  # 垂直方向
    L = cell_size * 0.30 * scale
    shaft_w = max(3, int(cell_size * 0.10 * scale))
    head_w = cell_size * 0.18 * scale

    tail = (cx - dx * L * 0.8, cy - dy * L * 0.8)
    head_base = (cx + dx * L * 0.15, cy + dy * L * 0.15)
    tip = (cx + dx * L, cy + dy * L)

    # 箭杆
    pygame.draw.line(surface, color, tail, head_base, shaft_w)
    # 箭头三角形
    p1 = (tip[0], tip[1])
    p2 = (head_base[0] + px * head_w, head_base[1] + py * head_w)
    p3 = (head_base[0] - px * head_w, head_base[1] - py * head_w)
    pygame.draw.polygon(surface, color, [p1, p2, p3])
    if edge_color is not None:
        pygame.draw.polygon(surface, edge_color, [p1, p2, p3], max(1, shaft_w // 3))


# ---------------- 棋盘绘制 ----------------
def draw_board(surface: pygame.Surface, board: Board, origin: Tuple[int, int],
               cell_size: int, hint_pos: Optional[Tuple[int, int]] = None,
               hidden: Optional[set] = None) -> None:
    ox, oy = origin
    bw = cell_size * board.cols
    bh = cell_size * board.rows

    # 棋盘底板
    pygame.draw.rect(surface, Colors.BG2, (ox - 6, oy - 6, bw + 12, bh + 12), border_radius=10)
    pygame.draw.rect(surface, Colors.PANEL, (ox, oy, bw, bh), border_radius=6)

    # 网格线
    for c in range(board.cols + 1):
        x = ox + c * cell_size
        pygame.draw.line(surface, Colors.GRID_LIGHT, (x, oy), (x, oy + bh), 1)
    for r in range(board.rows + 1):
        y = oy + r * cell_size
        pygame.draw.line(surface, Colors.GRID_LIGHT, (ox, y), (ox + bw, y), 1)
    pygame.draw.rect(surface, Colors.GRID, (ox, oy, bw, bh), 2, border_radius=6)

    # 提示高亮
    if hint_pos is not None:
        hr, hc = hint_pos
        hx = ox + hc * cell_size
        hy = oy + hr * cell_size
        pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) * 0.5
        glow = tuple(int(Colors.HINT[i] * (0.35 + 0.25 * pulse)) for i in range(3))
        pygame.draw.rect(surface, glow, (hx + 2, hy + 2, cell_size - 4, cell_size - 4), border_radius=6)
        pygame.draw.rect(surface, Colors.HINT, (hx + 2, hy + 2, cell_size - 4, cell_size - 4), 3, border_radius=6)

    hidden = hidden or set()
    # 箭头
    for a in board.all_arrows():
        if a.pos in hidden:
            continue
        center = cell_center(a.row, a.col, origin, cell_size)
        draw_arrow(surface, center, a.direction, Colors.ARROW, cell_size,
                   edge_color=Colors.ARROW_EDGE)


# ---------------- 文本工具 ----------------
def draw_text(surface: pygame.Surface, text: str, pos: Tuple[int, int],
              size: int, color: Tuple[int, int, int] = Colors.TEXT,
              bold: bool = False, center: bool = False) -> pygame.Rect:
    f = font(size, bold)
    surf = f.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(surf, rect)
    return rect


# ---------------- 按钮 ----------------
class Button:
    def __init__(self, rect: pygame.Rect, text: str, key: str):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.key = key
        self.hovered = False

    def update_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered

    def draw(self, surface: pygame.Surface) -> None:
        col = Colors.BTN_HOVER if self.hovered else Colors.BTN
        pygame.draw.rect(surface, col, self.rect, border_radius=8)
        pygame.draw.rect(surface, Colors.GRID, self.rect, 2, border_radius=8)
        draw_text(surface, self.text, self.rect.center, 20,
                  Colors.BTN_TEXT, bold=True, center=True)

    def hit(self, pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def make_button_row(y: int, items: List[Tuple[str, str]], width: int = 130,
                    height: int = 42, gap: int = 14) -> List[Button]:
    """在 y 行水平居中排一排按钮。items: [(text, key), ...]"""
    total = len(items) * width + (len(items) - 1) * gap
    x = (WINDOW_W - total) // 2
    btns = []
    for text, key in items:
        btns.append(Button((x, y, width, height), text, key))
        x += width + gap
    return btns


# ---------------- HUD ----------------
def draw_hud(surface: pygame.Surface, game, level_label: str = "") -> None:
    # 顶栏背景
    pygame.draw.rect(surface, Colors.BG2, (0, 0, WINDOW_W, 120))
    pygame.draw.line(surface, Colors.GRID, (0, 120), (WINDOW_W, 120), 2)

    title = "一箭又一箭"
    draw_text(surface, title, (40, 22), 34, Colors.ACCENT, bold=True)

    # 关卡名
    name = level_label or game.level_name()
    draw_text(surface, name, (40, 70), 22, Colors.TEXT)

    # 右侧统计
    stats = [
        ("关卡", f"{getattr(game, 'current_level_idx', 0) + 1}/{game.total_levels()}"),
        ("剩余箭头", str(game.arrows_left())),
        ("剩余失误", str(game.mistakes_left)),
        ("得分", str(game.score)),
        ("用时", f"{game.elapsed:4.1f}s"),
    ]
    _draw_stats_right(surface, stats)


def _draw_stats_right(surface: pygame.Surface, stats: List[Tuple[str, str]]) -> None:
    """把统计项整齐地右对齐画在顶栏。"""
    x_right = WINDOW_W - 40
    y = 34
    # 先测量每项宽度，从右到左排
    rendered = []
    for label, val in stats:
        vf = font(24, True)
        lf = font(16)
        vs = vf.render(val, True, Colors.TEXT)
        ls = lf.render(label, True, Colors.TEXT_DIM)
        rendered.append((label, val, vs, ls))
    gap = 26
    x = x_right
    for label, val, vs, ls in reversed(rendered):
        # value 右对齐到 x
        vrect = vs.get_rect()
        vrect.topright = (x, y)
        # label 在 value 左侧
        lrect = ls.get_rect()
        lrect.topright = (vrect.left - 8, y + 6)
        surface.blit(vs, vrect)
        surface.blit(ls, lrect)
        x = lrect.left - gap
