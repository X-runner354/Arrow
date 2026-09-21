"""生成 README 所需的游戏截图（用 SDL dummy 驱动离屏渲染后保存 PNG）。

运行：py make_screenshots.py
输出：assets/start.png, assets/playing.png, assets/level_complete.png, assets/failed.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from main import App
from core import GameState, find_solution, build_board, LEVELS
from ui import cell_center

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS, exist_ok=True)


def save(app: App, name: str) -> None:
    path = os.path.join(ASSETS, name)
    pygame.image.save(app.screen, path)
    print("saved", path)


def click_btn(app: App, key: str, buttons_fn) -> bool:
    btns = buttons_fn()
    for b in btns:
        if b.key == key:
            app.handle_click(b.rect.center)
            return True
    return False


def main() -> None:
    app = App()

    # 1) 开始界面
    app.draw()
    save(app, "start.png")

    # 2) 游戏界面（第 1 关）
    click_btn(app, "start", app.start_buttons)
    for _ in range(3):
        app.update(1 / 60)
        app.draw()
    save(app, "playing.png")

    # 3) 通关界面：用求解器把第 1 关玩通
    sol = find_solution(build_board(LEVELS[0]))
    layout = app.current_layout()
    origin, cell_size, _, _ = layout
    for a in sol:
        if app.game.state != GameState.PLAYING:
            break
        if app.game.board.get(a.row, a.col) is None:
            continue
        cx, cy = cell_center(a.row, a.col, origin, cell_size)
        app.handle_click((cx, cy))
        for _ in range(30):
            app.update(1 / 60)
            app.draw()
        layout = app.current_layout()
        if layout:
            origin, cell_size, _, _ = layout
    app.draw()
    save(app, "level_complete.png")

    # 4) 失败界面：开第 3 关，反复点被阻挡的箭头直到失败
    app.game.back_to_menu()
    app.clear_animations()
    # 直接加载第 3 关
    app.game.score = 0
    app.game._custom_level = None
    app.game._load_level(2)
    app.clear_animations()
    for _ in range(3):
        app.update(1 / 60)
        app.draw()
    save(app, "playing_level3.png")
    # 第 3 关 (0,0)> 被 (0,1)v 阻挡
    while app.game.state == GameState.PLAYING:
        app.handle_click((cell_center(0, 0, *app.current_layout()[:2])))
        for _ in range(15):
            app.update(1 / 60)
            app.draw()
    app.draw()
    save(app, "failed.png")

    pygame.quit()
    print("\n截图生成完毕，见 assets/ 目录")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
