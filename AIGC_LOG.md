# AIGC 使用过程记录

本项目开发过程中使用了 AIGC 工具 **CodeArts（GLM-5.2）** 辅助开发。以下记录 5 次具有代表性的 AI 协作过程，均来自真实开发过程。

---

## 协作 1：路径检测与核心数据结构设计

| 项目 | 内容 |
|------|------|
| 子任务 | 设计 `Arrow` / `Direction` / `Board` 数据结构并实现四向路径检测 |
| 借助何种 AIGC | CodeArts (GLM-5.2) |
| 我提出的要求 | "用 Python 设计一箭又一箭的棋盘逻辑：箭头有上下左右四种方向，棋盘用网格表示。需要实现路径检测——判断箭头前进方向上到边界之间是否还有其他箭头。要求纯逻辑、不依赖图形库，方便单元测试。用 dataclass 和 Enum。" |
| AI 实现或提供了什么 | 完整的 `core/board.py`：`Direction` 枚举（带 `delta` 单位向量属性）、`Arrow` 不可变 dataclass、`Board` 类（用 `dict[(row,col)]->Arrow` 存储，O(1) 查询）、`path_cells` / `path_blocked` / `can_fly_out` / `first_blocker` 四个检测方法，以及 `is_solvable` / `find_solution` 回溯求解器。 |
| 效果如何 | 一次生成的代码结构清晰、逻辑正确。四向检测用 `range` 生成路径格子再判断是否在 `arrows` 字典中，简洁且无越界风险。求解器的"删除箭头只会解除阻挡"性质注释也很有帮助。 |
| 人工修改 | ① 给 `Direction.from_str` 增加了对中文"上下左右"和箭头符号 `^v<>` 的兼容；② 在 `Board.__init__` 中增加了同格多箭头的 `ValueError` 校验，避免后续调试困难；③ 给求解器加了状态记忆化（`memo: set`），否则 6 关关卡里较大的棋盘会超时。 |

**关键代码（AI 生成 + 人工优化）：**

```python
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
    return [(r, cc) for cc in range(c + 1, self.cols)]  # RIGHT

def path_blocked(self, arrow: Arrow) -> bool:
    return any(cell in self.arrows for cell in self.path_cells(arrow))
```

---

## 协作 2：关卡设计与可通关性验证

| 项目 | 内容 |
|------|------|
| 子任务 | 设计 6 个由易到难的手工关卡，并验证全部可通关 |
| 借助何种 AIGC | CodeArts (GLM-5.2) |
| 我提出的要求 | "设计 6 个一箭又一箭关卡，用字符串地图表示（.^v<>），由易到难。每个关卡都要保证可通关。写一个验证函数用回溯求解器检查每个关卡。" |
| AI 实现或提供了什么 | 6 个关卡的字符串地图、`parse_map` 解析函数、`validate_levels` 校验函数，以及在 `levels.py` 导入时自动校验的守卫代码。 |
| 效果如何 | **初次生成的第 4 关和第 6 关不可通关**——存在面对面箭头互相阻挡的死锁（例如同一行一个朝右、一个朝左，中间无空隙）。AI 生成的验证函数正确地检测出了这两个问题。 |
| 人工修改 | 重新设计第 4 关（"十字"）和第 6 关（"迷阵"），改用"单向列车 + 外向箭头"布局避免对向死锁，并用 `find_solution` 逐关试玩验证消除顺序。最终 6 关全部通过 `is_solvable` 校验。 |

**问题关卡与修正（第 4 关示例）：**

```
# AI 初版（不可通关，中心对向死锁）
"..v.."
"....."
"<.>.>"   ← 中心 > 和 < 互相阻挡
"....."
"..v.."

# 修正后（可通关）
"..v.."
"....."
"<...>"   ← 中心留空，左右箭头可先飞出
".>>>."
"..v.."
```

---

## 协作 3：飞出与碰撞动画实现

| 项目 | 内容 |
|------|------|
| 子任务 | 实现箭头飞出棋盘的滑动淡出动画，以及碰撞时的晃动 + 变红反馈 |
| 借助何种 AIGC | CodeArts (GLM-5.2) |
| 我提出的要求 | "用 pygame 实现两种动画：1) 箭头飞出——沿方向滑出边界并淡出；2) 碰撞——原位晃动并变红闪烁。要能和 Game 状态机配合，动画期间禁止点击。" |
| AI 实现或提供了什么 | `FlyOutAnim` 类（记录起始格、方向、持续时间，按进度计算偏移与 alpha）、`CollisionAnim` 类（用正弦函数计算晃动偏移、按进度在原色与红色间插值），以及主循环中动画队列的更新与绘制逻辑。 |
| 效果如何 | 基本可用，飞出动画的淡出效果自然。碰撞晃动用了正弦函数，比线性偏移更顺滑。 |
| 人工修改 | ① AI 给的飞出持续时间偏长（0.5s），玩起来拖沓，改为 0.35s；碰撞改为 0.4s。② 碰撞动画的红色闪烁在浅色箭头上不明显，改为同时叠加半透明红色圆圈。③ 修复了动画期间 `Game.click` 仍可被调用的竞态——在主循环里加了 `if self.anim_queue: return` 守卫。 |

**关键代码（碰撞晃动，AI 生成 + 人工调参）：**

```python
class CollisionAnim:
    def __init__(self, arrow, duration=0.4):
        self.arrow = arrow
        self.duration = duration
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        return self.t >= self.duration

    def offset(self):
        # 正弦晃动，幅度随时间衰减
        progress = self.t / self.duration
        amp = 6 * (1 - progress)
        return (math.sin(self.t * 40) * amp, 0)
```

---

## 协作 4：随机关卡反向构造生成器

| 项目 | 内容 |
|------|------|
| 子任务 | 实现随机生成保证可通关的关卡 |
| 借助何种 AIGC | CodeArts (GLM-5.2) |
| 我提出的要求 | "写一个随机关卡生成器，要求生成的关卡一定可通关。提示：可以用反向构造——从空棋盘开始，每次放一个'相对当前棋盘可飞出'的箭头，放置顺序的逆序就是消除顺序。" |
| AI 实现或提供了什么 | `random_solvable_level(rows, cols, count, seed)` 函数：用 `random.Random(seed)` 初始化，循环随机选格子和方向，若 `board.can_fly_out(arrow)` 则放入，直到放够 `count` 个或达到尝试上限。 |
| 效果如何 | 算法正确，生成的关卡确实可通关（已用 `is_solvable` 对 10 个种子验证全部通过）。 |
| 人工修改 | ① AI 原版没有尝试次数上限，当棋盘较满时可能死循环，加了 `max_attempts = max(count * 40, 200)`；② 给函数加了 `seed` 参数方便测试复现；③ 当实际放入数少于 `count` 时（棋盘太满），返回实际数量而非报错，并在关卡名里标注真实箭头数。 |

**关键代码（反向构造核心）：**

```python
def random_solvable_level(rows, cols, count, seed=None):
    rng = random.Random(seed)
    board = Board(rows, cols)
    placed = []
    for _ in range(max(count * 40, 200)):
        if len(placed) >= count:
            break
        r, c = rng.randrange(rows), rng.randrange(cols)
        if (r, c) in board.arrows:
            continue
        a = Arrow(r, c, rng.choice(list(Direction)))
        if board.can_fly_out(a):   # 关键：只放"当前可飞出"的箭头
            board.add(a)
            placed.append(a)
    return {"name": f"随机关卡 ({len(placed)} 箭)", ...}
```

---

## 协作 5：Bug 定位与修复

| 项目 | 内容 |
|------|------|
| 子任务 | 修复随机关卡通关后状态错误 + 修复截图脚本 `draw_text` 参数错误 |
| 借助何种 AIGC | CodeArts (GLM-5.2) |
| 我提出的要求 | "随机关卡通关后显示的是'全部通关'而不是'本关通关'，帮我排查。另外截图脚本报错 `draw_text() got multiple values for argument 'bold'`。" |
| AI 实现或提供了什么 | ① 定位到 `Game._is_last_level` 对自定义关卡返回 `True`，导致随机关卡通关直接进入 `ALL_COMPLETE`；② 定位到 `draw_overlay` 调用 `draw_text(surf, text, box.centerx, box.top+50, ...)` 时把两个坐标当成了两个位置参数，而 `draw_text` 的签名是 `draw_text(surf, text, pos, ...)`，`pos` 应为元组。 |
| 效果如何 | 两个 Bug 都准确定位。 |
| 人工修改 | ① 把 `_is_last_level` 改为对 `_custom_level is not None` 时返回 `False`（随机关卡通关后按"下一关"回菜单）；② 把 `draw_overlay` 里的两次 `draw_text` 调用改为传元组 `(box.centerx, box.top+50)`。修复后截图脚本一次性生成 5 张截图成功。 |

**修复前后对比：**

```python
# Bug: _is_last_level 对随机关卡返回 True
def _is_last_level(self):
    return self.current_level_idx >= len(self.levels) - 1  # 随机关卡 idx=0 误判为最后一关

# 修复
def _is_last_level(self):
    if self._custom_level is not None:
        return False   # 随机关卡通关后回菜单，不视为最后一关
    return self.current_level_idx >= len(self.levels) - 1
```

---

## 总结

| 协作 | 子任务 | AI 贡献 | 人工修改幅度 |
|------|--------|---------|-------------|
| 1 | 路径检测 | 生成完整核心结构 | 小（加校验、记忆化） |
| 2 | 关卡设计 | 生成 6 关 + 验证函数 | 中（2 关不可通关，重设计） |
| 3 | 动画实现 | 生成两种动画类 | 中（调参、加守卫、改视觉） |
| 4 | 随机关卡 | 生成反向构造算法 | 小（加尝试上限、seed） |
| 5 | Bug 修复 | 准确定位两处 Bug | 小（按建议改代码） |

**整体感受**：AI 在生成结构化代码（数据结构、算法骨架）时效率很高，但在关卡设计这类需要"试玩直觉"的任务上容易产生死锁布局，必须配合求解器验证。AI 擅长定位报错信息明确的 Bug，但对涉及游戏状态语义的 Bug（如"随机关卡是否算最后一关"）需要人类给出业务规则提示。
