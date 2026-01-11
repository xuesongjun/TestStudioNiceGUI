from nicegui import ui
from datetime import datetime
import time
from queue import Queue

# 通知队列 - 用于跨线程传递通知
_notify_queue = Queue()

# 全局日志区 - 使用scroll_area组件，内置自动滚动
with ui.scroll_area().classes('w-full h-48 border border-gray-300 rounded bg-white') as scroll_container:
    log_area = ui.html(sanitize=False).classes('font-mono text-sm p-2').style('padding-bottom: 20px;')

# 全局开关，控制日志是否自动带时间戳
LOG_USE_TIMESTAMP = True

# 滚动防抖相关变量
_last_scroll_time = 0
_scroll_timer = None

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
        def update_log_ui():
            """在正确的UI上下文中更新log"""
            try:
                # 获取颜色值，如果没有指定颜色则使用默认黑色
                color_value = COLOR_MAP.get(color, COLOR_MAP[None])
                # 创建带颜色的HTML内容
                html_message = f'<div style="color: {color_value}; margin: 0; padding: 0; line-height: 1.2;">{display_message}</div>'
                
                # 在正确的UI上下文中更新HTML内容
                with scroll_container:
                    current_content = log_area.content if hasattr(log_area, 'content') and log_area.content else ""
                    log_area.content = current_content + html_message
                    log_area.update()
                
                # 立即滚动，确保实时性
                try:
                    scroll_container.scroll_to(percent=1.0)
                except:
                    pass
                
                # 延迟滚动确保可靠性
                ui.timer(0.1, lambda: self_scroll(), once=True)
                
                def self_scroll():
                    try:
                        scroll_container.scroll_to(percent=1.0)
                        # JavaScript备用滚动
                        ui.run_javascript("""
                            const containers = [
                                ...document.querySelectorAll('.q-scrollarea__container'),
                                ...document.querySelectorAll('.q-scrollarea__content')
                            ];
                            containers.forEach(container => {
                                if (container.scrollHeight > container.clientHeight) {
                                    container.scrollTop = container.scrollHeight + 200;
                                }
                            });
                        """)
                    except:
                        pass
            except Exception as e:
                # 如果仍然失败，只输出到终端
                print(f"Log UI update failed: {e}")
        
        try:
            # 始终使用timer来在主UI线程中执行更新，避免线程问题
            ui.timer(0.01, update_log_ui, once=True)
        except Exception:
            # 如果timer失败，则跳过UI更新，只输出到终端
            pass

    # --- 输出到终端 ---
    print(print_message, end=end, file=file, flush=flush)


def notify(message: str, type: str = 'info', position: str = 'top', timeout: int = 5000):
    """
    线程安全的通知函数，可以在后台线程中调用
    将通知放入队列，由定时器在 UI 上下文中处理
    """
    _notify_queue.put({
        'message': message,
        'type': type,
        'position': position,
        'timeout': timeout
    })


def _process_notify_queue():
    """处理通知队列中的消息"""
    while not _notify_queue.empty():
        try:
            item = _notify_queue.get_nowait()
            ui.notify(
                item['message'],
                type=item['type'],
                position=item['position'],
                timeout=item['timeout']
            )
        except Exception as e:
            print(f"Process notify failed: {e}")


def init_notify_timer():
    """初始化通知定时器，需要在页面创建后调用"""
    ui.timer(0.1, _process_notify_queue)
