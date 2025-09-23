from nicegui import ui
from datetime import datetime

# 全局日志区 - 使用HTML组件支持颜色
log_area = ui.html().classes('w-full h-48 border border-gray-300 rounded p-2 overflow-y-auto bg-white font-mono text-sm')

# 全局开关，控制日志是否自动带时间戳
LOG_USE_TIMESTAMP = True

# 颜色映射
COLOR_MAP = {
    'red': '#dc2626',
    'blue': '#2563eb', 
    'green': '#16a34a',
    'yellow': '#ca8a04',
    'purple': '#9333ea',
    'orange': '#ea580c',
    'gray': '#6b7280',
    'black': '#000000',
    None: '#000000'  # 默认黑色
}

def log(*args, sep=' ', end='\n', file=None, flush=False, with_timestamp=None, color=None):
    """
    兼容 print 的 log 函数，输出到 log_area 和标准输出
    带时间戳（可全局控制）和颜色支持
    """
    global LOG_USE_TIMESTAMP
    global log_area

    # 决定是否加时间戳，优先使用函数参数，其次使用全局开关
    if with_timestamp is None:
        with_timestamp = LOG_USE_TIMESTAMP

    # 组合消息
    message_content = sep.join(map(str, args))

    if with_timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_message = f"{timestamp} > {message_content}"
        print_message = f"{timestamp} > {message_content}"
    else:
        display_message = message_content
        print_message = message_content

    # --- 输出到 log_area ---  
    if log_area is not None:
        # 获取颜色值
        color_value = COLOR_MAP.get(color, COLOR_MAP[None])
        
        # 创建带颜色的HTML内容
        html_message = f'<div style="color: {color_value}; margin: 0; padding: 0; line-height: 1.2;">{display_message}</div>'
        
        try:
            # 尝试直接更新，如果在主线程中执行
            current_content = log_area.content if hasattr(log_area, 'content') and log_area.content else ""
            log_area.content = current_content + html_message
            log_area.update()
        except Exception:
            # 如果在工作线程中，使用JavaScript方式更新UI
            js_safe_html = html_message.replace("'", "\\'").replace('"', '\\"')
            ui.run_javascript(f"""
                var logArea = document.querySelector('.nicegui-html');
                if (logArea) {{
                    logArea.innerHTML += '{js_safe_html}';
                    logArea.scrollTop = logArea.scrollHeight;
                }}
            """)

    # --- 输出到终端 ---
    print(print_message, end=end, file=file, flush=flush)
