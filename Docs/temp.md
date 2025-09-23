好主意 👍，我给你整理一份 **Tailwind + NiceGUI 布局速查表**，以后你写 `ui.xxx().classes(...)` 的时候，可以快速查到常用类名效果，不用一个个试。

---

# 📌 Tailwind + NiceGUI 布局速查表

## 1. **Flex & 布局**

| 类名                | 含义         | 效果     |
| ----------------- | ---------- | ------ |
| `flex`            | 启用 flex 布局 | 横向排布   |
| `flex-col`        | 垂直方向排列     | 纵向布局   |
| `items-center`    | 交叉轴居中      | 垂直方向居中 |
| `justify-center`  | 主轴居中       | 水平方向居中 |
| `justify-between` | 两端对齐       | 左右分散   |
| `justify-around`  | 平均分布       | 中间间隔相等 |
| `gap-4`           | 子元素间距 16px | 控制元素间距 |

---

## 2. **Spacing（外边距 / 内边距）**

👉 Tailwind 的 spacing 单位：`1 = 0.25rem = 4px`

| 类名     | 含义         | 像素                       |
| ------ | ---------- | ------------------------ |
| `m-4`  | 外边距 16px   | margin: 16px             |
| `p-4`  | 内边距 16px   | padding: 16px            |
| `mt-6` | 上边距 24px   | margin-top: 24px         |
| `mb-2` | 下边距 8px    | margin-bottom: 8px       |
| `px-8` | 左右内边距 32px | padding-left/right: 32px |
| `py-4` | 上下内边距 16px | padding-top/bottom: 16px |

---

## 3. **文本 & 字体**

| 类名              | 含义   |
| --------------- | ---- |
| `text-sm`       | 小号文字 |
| `text-base`     | 正常大小 |
| `text-lg`       | 稍大   |
| `text-xl`       | 大标题  |
| `text-2xl`      | 更大标题 |
| `font-bold`     | 加粗   |
| `font-semibold` | 半粗   |
| `text-gray-500` | 灰色文字 |
| `text-red-500`  | 红色文字 |

---

## 4. **颜色 & 背景**

| 类名                  | 含义        |
| ------------------- | --------- |
| `bg-gray-100`       | 浅灰背景      |
| `bg-blue-500`       | 蓝色背景      |
| `bg-green-500`      | 绿色背景      |
| `text-white`        | 白色文字      |
| `hover:bg-blue-600` | hover 变深蓝 |

---

## 5. **圆角 & 阴影**

| 类名             | 含义        |
| -------------- | --------- |
| `rounded`      | 小圆角       |
| `rounded-lg`   | 大圆角       |
| `rounded-full` | 圆形（头像/按钮） |
| `shadow`       | 默认阴影      |
| `shadow-lg`    | 大阴影       |
| `shadow-none`  | 无阴影       |

---

## 6. **宽高控制**

| 类名             | 含义         |
| -------------- | ---------- |
| `w-full`       | 占满父容器宽度    |
| `w-1/2`        | 占一半宽度      |
| `max-w-md`     | 最大宽度 28rem |
| `h-12`         | 高度 48px    |
| `min-h-screen` | 最小高度撑满屏幕   |

---

## 7. **定位**

| 类名                 | 含义   |
| ------------------ | ---- |
| `absolute`         | 绝对定位 |
| `relative`         | 相对定位 |
| `fixed`            | 固定定位 |
| `top-0 left-0`     | 左上角  |
| `right-0 bottom-0` | 右下角  |
| `z-10`             | 层级控制 |

---

✅ **NiceGUI 使用方式：**

```python
from nicegui import ui

with ui.row().classes('gap-6 justify-between items-center mt-6'):
    ui.button('左边')
    ui.button('右边')
```

---

要不要我帮你整理一份 **常用布局组合示例**（比如顶部导航栏、左右布局、卡片网格），直接复制粘贴就能用？


好，那我就整理一份 **常用布局组合示例速查表**，以后你可以直接复制到 `NiceGUI` 项目里用，基本覆盖常见的布局场景 🚀。

---

# 📌 NiceGUI + Tailwind 常用布局示例

## 1️⃣ 顶部导航栏

```python
from nicegui import ui

with ui.header().classes('bg-blue-600 text-white p-4'):
    ui.label('Test Studio').classes('text-xl font-bold')
    with ui.row().classes('ml-auto gap-4'):
        ui.button('首页', on_click=lambda: ui.open('/'))
        ui.button('设置', on_click=lambda: ui.open('/settings'))
```

---

## 2️⃣ 左侧菜单 + 主体

```python
with ui.row().classes('h-screen'):
    with ui.column().classes('w-1/5 bg-gray-100 p-4 gap-4'):
        ui.link('首页', '/')
        ui.link('设置', '/settings')
    with ui.column().classes('flex-1 p-6'):
        ui.label('这里是主内容').classes('text-2xl font-bold')
```

---

## 3️⃣ 卡片网格布局

```python
with ui.grid(columns=3).classes('gap-6 p-6'):
    for i in range(6):
        with ui.card().classes('p-4 shadow rounded-lg'):
            ui.label(f'卡片 {i+1}').classes('text-lg font-semibold')
            ui.button('操作', on_click=lambda: ui.notify(f'点击了卡片 {i+1}'))
```

---

## 4️⃣ 表单布局（设置页常用）

```python
with ui.column().classes('gap-4 max-w-md p-6'):
    ui.input('仪表 IP').props('outlined clearable')
    ui.select(['COM1','COM2','COM3'], label='串口选择').props('outlined')
    ui.checkbox('启用日志')
    ui.button('保存设置', on_click=lambda: ui.notify('设置已保存'))
```

---

## 5️⃣ 分栏布局（左右对比）

```python
with ui.row().classes('gap-12 p-6'):
    with ui.card().classes('flex-1 p-4'):
        ui.label('左侧内容').classes('text-lg font-semibold')
    with ui.card().classes('flex-1 p-4'):
        ui.label('右侧内容').classes('text-lg font-semibold')
```

---

## 6️⃣ 顶部 + 左侧 + 主体 三段式（最常见的后台管理）

```python
with ui.column().classes('h-screen'):
    # 顶部导航
    with ui.row().classes('bg-blue-600 text-white p-4 items-center'):
        ui.label('Test Studio').classes('text-xl font-bold')
    
    # 主体
    with ui.row().classes('flex-1'):
        # 左侧菜单
        with ui.column().classes('w-1/5 bg-gray-100 p-4 gap-4'):
            ui.link('首页', '/')
            ui.link('设置', '/settings')
        
        # 主体内容
        with ui.column().classes('flex-1 p-6'):
            ui.label('这里是主体内容').classes('text-2xl font-bold')
```

---

## 7️⃣ 日志区（固定在底部）

```python
with ui.column().classes('h-screen'):
    with ui.column().classes('flex-1 p-6'):
        ui.label('主内容区')
    with ui.card().classes('h-40 overflow-auto p-2 bg-black text-white'):
        ui.label('日志输出...')
```

---

这样你就有一套速查表：

* **导航栏**
* **侧边栏**
* **卡片网格**
* **表单**
* **分栏**
* **后台三段式**
* **日志区**

---

要不要我帮你把这几种布局，整合成一个 **完整的 test\_studio 版后台模板**（首页、设置页、日志区都能切换），直接跑就能用？
