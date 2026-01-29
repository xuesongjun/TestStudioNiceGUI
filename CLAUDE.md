**提示**：本项已启用自动化记忆技能。开发结束请对我说“**存盘**”，开始开发请对我说“**同步进度**”。
# BLE RF Test Studio

## 项目简介

BLE RF Test Studio 是一个基于 Web 的射频测试工具，用于 BLE（低功耗蓝牙）芯片的射频性能测试与分析。目前主要支持 **ECW6700** 和 **ECR2560** 芯片，通过串口与 DUT（被测设备）通信，通过 VISA 协议控制 Keysight N5182B 信号源等仪器。

### 核心功能

- **IQ Dump**：采集 IQ 数据，进行增益扫描和噪声分析，计算 SNR、NF、IMRR 等射频指标
- **BLE PER 测试**：丢包率（PER）测试和灵敏度扫描，支持 LE1M/LE2M/LR500K/LR125K 四种 BLE 模式
- **寄存器对比**：多设备寄存器值对比，支持差异寄存器同步、排除校准寄存器
- **数据查看**：测试结果可视化，历史数据查询
- **日志系统**：实时日志显示，支持彩色分类输出

---

## 目录结构

```
├── src/
│   ├── main.py                  # 应用入口，页面路由和导航
│   ├── config_manager.py        # JSON 配置管理器（单例模式）
│   ├── __init__.py
│   ├── pages/                   # UI 页面
│   │   ├── layout.py            # 全局布局、日志系统（Queue + Timer）、通知系统
│   │   ├── home.py              # IQ Dump 页面
│   │   ├── ble_per.py           # BLE PER 测试页面
│   │   ├── reg_compare.py       # 寄存器对比页面
│   │   ├── data_view.py         # 数据查看页面
│   │   ├── log_page.py          # 日志页面
│   │   └── settings.py          # 设置页面
│   ├── logic/                   # 业务逻辑（与 UI 分离）
│   │   ├── serial_lib.py        # 串口通信库（SerialCommunication 类：read_reg, write_reg）
│   │   ├── ble_per_test.py      # BLE PER 测试逻辑（per_test, sensitivity_scan）
│   │   ├── reg_compare_logic.py # 寄存器对比逻辑（compare_registers, sync_register）
│   │   ├── instrument.py        # VISA 仪器连接检查
│   │   ├── iqdump.py            # IQ 数据采集逻辑
│   │   ├── gain_sweep.py        # 增益扫描逻辑
│   │   ├── iq_file_parser.py    # IQ 文件解析
│   │   ├── iq_analyzer.py       # IQ 数据分析
│   │   └── config.py            # 全局响应式配置变量（to_ref）
│   ├── components/              # 可复用 UI 组件
│   │   └── GeneralSelector.py   # 通用多选器（信道选择、BLE 制式选择）
│   ├── config/                  # 配置文件
│   │   ├── test_studio_cfg.json # 应用配置（仪器 IP、串口、信号参数）
│   │   └── register_maps/
│   │       └── default_regs.yaml# ECW6700 寄存器映射（分组、地址、排除列表）
│   ├── db/
│   │   └── db_manager.py        # SQLite 数据库管理
│   └── utils/
│       └── file_dialog.py       # 文件选择对话框
├── data/                        # 运行时数据（IQ dumps、数据库）
├── Docs/                        # 文档
├── venv/                        # Python 虚拟环境
├── requirements.txt             # Python 依赖
├── setup.bat                    # 环境安装脚本
├── run.bat                      # 启动脚本
├── run_wt.bat                   # Windows Terminal 启动脚本
└── .gitignore
```

---

## 核心技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.9+ |
| Web UI 框架 | NiceGUI (>=1.4.0) + ex4nicegui (>=0.7.0) |
| 响应式状态 | `ex4nicegui.to_ref()` + `rxui` 组件 |
| 图表可视化 | Plotly (>=5.18.0) |
| 数据处理 | NumPy (>=1.24.0) |
| 仪器控制 | PyVISA (>=1.13.0) + pyvisa-py |
| 串口通信 | PySerial (>=3.5) |
| 数据库 | SQLite3（内置） |
| 配置格式 | JSON（应用配置）+ YAML（寄存器映射） |
| Excel 导出 | openpyxl (>=3.1.0) |

---

## 常用命令

### 环境安装

```bash
# 首次安装（Windows）
setup.bat

# 或手动安装
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 启动应用

```bash
# Windows 推荐（双击即可）
run.bat

# 或手动启动
venv\Scripts\activate
python -u src/main.py
```

应用启动后访问 http://localhost:8081

### Git 提交规范

本项目使用**中文**提交信息，示例：

```
新增寄存器对功能
优化寄存器对比速度
增加灵敏度扫描功能
修复PER测试时第一次出错问题
```

---

## 代码风格规范

### 语言与注释

- 所有注释、日志输出、UI 文本均使用**中文**
- 变量名和函数名使用英文，遵循 Python snake_case 风格
- 文件模块级别可选写 docstring，使用中文描述

### UI 页面（pages/）

- 每个页面是一个函数，返回 `ui.column()` 容器
- 使用 `to_ref()` 管理响应式状态
- 使用 `layout.log()` 输出日志，`layout.notify()` 弹出通知
- 耗时操作必须放在 `threading.Thread` 中执行，避免阻塞 UI
- 跨线程更新 UI 通过 Queue + `ui.timer` 机制

### 业务逻辑（logic/）

- 与 UI 完全分离，不直接导入 `nicegui`（`instrument.py` 除外）
- 通过回调函数（`log_func`、`result_callback`、`progress_callback`）与 UI 通信
- 自定义异常类（如 `PerTestError`、`RegCompareError`）用于错误传递
- 串口命令格式：`"write 0x{addr:x} 0x{value:x}\r\n"` / `"read 0x{addr:x} {size}\r\n"`

### 配置管理

- 应用全局配置：`src/config/test_studio_cfg.json`
- 响应式配置变量：`src/logic/config.py`（使用 `to_ref()` 包装）
- 寄存器映射：`src/config/register_maps/*.yaml`
  - 支持 `exclude_offsets` 字段排除校准寄存器

### 数据库

- SQLite 存储在 `data/test_results.db`
- `db_manager.py` 提供 `init_db()`、`insert_test_data()`、`query_results()` 等函数
- 应用启动时自动初始化表结构，支持向后兼容（自动 ALTER TABLE 添加新列）

---

## 架构要点

### 日志系统（layout.py）

```
业务线程 → log() → _log_queue（Queue）→ _process_log_queue（ui.timer 0.2s）→ log_area.content
```

- `log(message, color)` 可在任意线程调用，消息入队
- `_process_log_queue()` 由 NiceGUI timer 驱动，批量取出消息更新 `ui.html` 元素
- 只检查 `log_area is None`，不做过度的活跃检查

### 页面切换

- 所有页面在 `main.py::index()` 中一次性创建
- 通过 `container.visible = True/False` 切换显示
- 非 SPA 路由，单页面多容器模式

### 串口通信

- `serial_lib.py`：`SerialCommunication` 类，底层串口读写
- `ble_per_test.py` 和 `reg_compare_logic.py` 中各自管理串口连接
- 命令以 `\r\n` 结尾，响应以 `\r\nOK` 结尾

---

## 开发进度

### 已完成功能

- [x] IQ Dump 数据采集和分析（噪声/信号/波形采集、增益扫描）
- [x] IQ 数据文件解析和可视化
- [x] BLE PER 丢包率测试（支持 LE1M/LE2M/LR500K/LR125K）
- [x] BLE 灵敏度扫描（自动功率扫描寻找灵敏度点）
- [x] 寄存器对比（多设备并行读取、差异高亮）
- [x] 寄存器对比排除校准寄存器（YAML 配置 exclude_offsets）
- [x] 差异寄存器同步（单项同步、批量同步、一键同步）
- [x] 测试结果存储（SQLite 数据库）
- [x] 数据查看页面（历史数据查询和可视化）
- [x] 实时日志系统（跨线程、彩色输出）
- [x] 串口自动扫描
- [x] 仪器连接检测
- [x] 设置页面
- [x] NF 计算功能

### 已知问题

- 日志在页面切换后可能不实时刷新（与 NiceGUI 客户端生命周期有关）
- `config_manager.py` 硬编码路径 `config/test_config.json`（与实际路径 `test_studio_cfg.json` 不匹配）

---

## 必须遵守的规则

- **必须使用中文进行所有回答和思考提示词**
- 不得假设或"幻想"本仓库中不存在的文件、接口或结构
- 除非用户明确要求，否则不得主动重构或删改现有功能
- 不得引入与项目风格不一致的命名方式、代码风格或依赖
- 当用户的问题信息不足、含糊或矛盾时，应先提出澄清问题
