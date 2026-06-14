# 可视化模块 - 最小可执行任务列表

## 目录：`src/visualization/`

### 文件清单
- `src/visualization/__init__.py`
- `src/visualization/plotter.py`       — 实时图表绘制
- `src/visualization/interactive.py`   — 交互模式 GUI 控制

---

## 任务清单

### V1. 创建 `src/visualization/` 包结构
- 创建 `src/visualization/__init__.py`

### V2. 实现实时图表模块 (`plotter.py`)

- [ ] **V2.1 实现 `RealtimePlotter.__init__()` 与图表初始化**
  - matplotlib 图形初始化：1 行 2 列布局（左：空间分布散点图，右：统计曲线图）
  - 左图设置：x/y 范围 0~universe_size，等比例缩放，网格
  - 右图设置：x 轴-时间步，y 轴-文明数量，网格
  - `plt.ion()` 开启交互模式
  - 编写单元测试验证初始化不报错（不测试渲染）

- [ ] **V2.2 实现空间分布散点图更新 `_update_scatter()`**
  - 提取所有存活文明的 x/y/level/energy_output
  - 颜色映射：level 1~5 对应 蓝/绿/黄/橙/红
  - 点大小映射：`log10(energy)*5`，截断到 [5, 100]
  - 高效更新（使用 `set_offsets`/`set_sizes`/`set_color`，不重建）
  - 编写单元测试验证更新不报错

- [ ] **V2.3 实现统计曲线图更新 `_update_stats_curves()`**
  - 维护历史数据队列（step_history, total_history, level_history 1~5）
  - 限制显示点数（最多 500 点防止性能下降）
  - 绘制总文明数和各级别文明数曲线
  - 图例显示
  - 编写单元测试验证多次更新不积累内存泄漏

- [ ] **V2.4 实现图表标题更新 `_update_title()`**
  - 显示当前步数和存活文明数
  - 编写单元测试验证

- [ ] **V2.5 实现 `update()` 主方法**
  - 依次调用 scatter、stats_curves、title 更新
  - `fig.canvas.draw_idle()` + `flush_events()` 刷新
  - 编写单元测试验证多次 update 不报错

- [ ] **V2.6 实现 `close()` 清理**
  - `plt.ioff()` + `plt.close(fig)`
  - 编写单元测试验证

### V3. 实现高性能模式主循环 `run_fast()`
- 无图表，每步输出终端摘要
- 循环调用 `simulation.step()` 直到完成
- 完成后输出最终信息

### V4. 实现标准模式主循环 `run_standard()`
- 创建 `RealtimePlotter`
- 循环调用 `step()`，每 `plot_update_interval` 步更新图表
- 完成后保持图表窗口打开（`plt.show(block=True)`）

### V5. 实现交互模式增强图表 (`plotter.py`)

- [ ] **V5.1 实现 `InteractiveRealtimePlotter` 类**
  - 继承 `RealtimePlotter`
  - 绑定点击事件处理器 `_on_click`
  - 绑定快捷键事件处理器 `_on_key_press`

- [ ] **V5.2 实现点击事件 `_on_click()`**
  - 判断点击区域是否为散点图
  - 调用 `controller.show_civilization_detail()` 显示文明详情

- [ ] **V5.3 实现键盘快捷键绑定**
  - 空格：暂停/继续
  - `+`/`=`: 加速
  - `-`: 减速
  - `→`: 单步执行
  - `Esc`: 退出

### V6. 实现交互控制模块 (`interactive.py`)

- [ ] **V6.1 实现 `InteractiveController.__init__()`**
  - 接收 `Simulation` 和 `SimulationConfig`
  - 初始化运行状态（is_running, is_paused, speed, step_interval）
  - 创建 `InteractiveRealtimePlotter` 关联
  - 编写单元测试验证控制器初始化

- [ ] **V6.2 实现 tkinter 控制面板 UI**
  - 创建 `tk.Tk` 主窗口
  - 按钮行：[▶ 暂停] [⏪ 减速] [⏩ 加速] [⏭ 单步] [💾 导出] [❌ 退出]
  - 速度滑块（0.1x ~ 10.0x）+ 速度标签
  - 状态信息标签（步数、存活、新生、毁灭）

- [ ] **V6.3 实现暂停/继续控制 `toggle_pause()`**
  - 切换 `is_paused` 状态
  - 更新按钮文字
  - 暂停时停止定时器，继续时调度下一步
  - 编写单元测试验证

- [ ] **V6.4 实现速度控制（加速/减速/滑块）**
  - `speed_up()`: 速度 ×1.5
  - `slow_down()`: 速度 /1.5
  - `_on_speed_change()`: 滑块回调
  - `_update_speed_display()`: 更新显示
  - 编写单元测试验证

- [ ] **V6.5 实现单步执行 `step_forward()`**
  - 仅在暂停时有效
  - 调用 `simulation.run_single_step()`
  - 更新显示
  - 编写单元测试验证

- [ ] **V6.6 实现文明详情弹窗 `show_civilization_detail()`**
  - 查找距离点击位置最近的文明（100 光年范围内）
  - 创建 `tk.Toplevel` 详情窗口
  - 显示文明全部 16 个参数的详细信息
  - 编写单元测试验证最近文明查找逻辑

- [ ] **V6.7 实现状态导出 `export_state()`**
  - 调用 `simulation.save_state()` 导出 JSON
  - 更新状态栏显示导出文件名
  - 编写单元测试验证

- [ ] **V6.8 实现停止与清理 `stop()`**
  - 停止模拟运行
  - 停止定时器
  - 关闭图表窗口
  - 销毁 tkinter 主窗口

- [ ] **V6.9 实现定时器驱动步进循环**
  - `_run_step_loop()`: 执行一步 + 更新显示 + 调度下一步
  - `_schedule_next_step()`: 使用 `threading.Timer` 按间隔调度
  - `_stop_timer()`: 停止定时器
  - 模拟完成时自动停止

- [ ] **V6.10 实现交互模式入口 `run_interactive()`**
  - 创建控制器、图表、关联
  - 初始绘制
  - 启动模拟
  - 进入 tkinter 主循环
