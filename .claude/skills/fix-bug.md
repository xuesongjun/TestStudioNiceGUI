---
name: fix-bug
description: |
  按照标准流程修复 Test Studio 中的 Bug
---

# Bug 修复流程

## 项目结构

```
src/
  main.py              # 入口文件，页面路由
  pages/               # UI 页面
    layout.py           # 布局、日志系统、通知系统
    home.py             # IQ Dump 页面
    ble_per.py          # BLE PER 测试页面
    reg_compare.py      # 寄存器对比页面
    data_view.py        # 数据查看页面
    log_page.py         # 日志页面
    settings.py         # 设置页面
  logic/               # 业务逻辑
    ble_per_test.py     # BLE PER 测试逻辑（PER扫描、灵敏度扫描）
    reg_compare_logic.py# 寄存器对比逻辑（读寄存器、对比、同步）
    serial_lib.py       # 串口通信库（SerialCommunication 类）
    instrument.py       # 仪器连接检查
    iqdump.py           # IQ 数据采集
    gain_sweep.py       # 增益扫描
    iq_file_parser.py   # IQ 文件解析
    iq_analyzer.py      # IQ 分析
    config.py           # 全局配置变量（ip, com, dut_id 等）
  config/              # 配置文件
    test_studio_cfg.json       # 应用配置（仪器IP、串口、信号参数）
    register_maps/
      default_regs.yaml        # ECW6700 寄存器配置（分组、地址范围、排除列表）
  components/          # 可复用组件
    GeneralSelector.py  # 通用多选器组件
  db/
    db_manager.py       # SQLite 数据库管理
  utils/
    file_dialog.py      # 文件选择对话框
```

## 修复步骤

1. **定位错误**：根据错误信息，确认报错文件和行号
2. **阅读相关代码**：先读取报错文件，理解上下文逻辑
3. **分析根因**：找到问题的根本原因，而非表面现象
4. **修复代码**：只修改必要的部分，不做额外重构
5. **验证修复**：确认修复逻辑正确

## 常见问题类型

### 串口通信问题
- 检查 `serial_lib.py` 中的 `SerialCommunication` 类
- 注意 `read_reg` / `write_reg` 的超时和异常处理
- 串口命令格式：`"write 0x{addr:x} 0x{value:x}\r\n"`

### NiceGUI UI 问题
- 框架：NiceGUI + ex4nicegui（`to_ref`, `rxui`）
- 跨线程更新 UI：通过 Queue + `ui.timer` 处理
- 日志系统在 `layout.py`：使用 `_log_queue` 队列 + `_process_log_queue` 定时器
- 页面切换：通过 `container.visible` 控制

### 寄存器相关问题
- 配置文件：`src/config/register_maps/default_regs.yaml`
- 逻辑代码：`src/logic/reg_compare_logic.py`
- 注意 `exclude_offsets`（排除的校准寄存器）
