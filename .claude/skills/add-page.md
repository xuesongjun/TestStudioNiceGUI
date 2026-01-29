---
name: add-page
description: |
  为 Test Studio 添加新页面
---

# 添加新页面

## 步骤

### 1. 创建页面文件

在 `src/pages/` 目录下创建新的 `.py` 文件，遵循现有页面模式：

```python
from nicegui import ui
from ex4nicegui import to_ref, rxui
from pages.layout import log, notify

def new_page():
    with ui.column().classes('p-4 gap-4') as container:
        ui.label('页面标题').classes('text-xl font-bold')
        # 页面内容...
    return container
```

### 2. 注册页面路由

在 `src/main.py` 中：

1. 导入页面函数：
```python
from pages.new_page import new_page
```

2. 在 `index()` 函数中创建容器：
```python
new_container = new_page()
new_container.visible = False
```

3. 添加切换函数，在所有 `show_*` 函数中处理 `new_container.visible`

4. 在导航栏中添加按钮：
```python
ui.button('新页面', on_click=show_new).props('icon=icon_name flat')
```

### 3. 添加业务逻辑（如需要）

在 `src/logic/` 目录下创建对应的逻辑模块。

## 注意事项

- 页面通过 `container.visible` 切换显示/隐藏
- 使用 `layout.log()` 输出日志，使用 `layout.notify()` 弹出通知
- 耗时操作必须放在子线程中，通过 `threading.Thread` 执行
- 跨线程更新 UI 需通过 Queue + timer 机制
- 响应式变量使用 `to_ref()` + `rxui` 组件
