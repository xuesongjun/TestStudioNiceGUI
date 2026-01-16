from nicegui import ui, context
from nicegui.client import Client
from datetime import datetime
from queue import Queue

# 通知队列 - 用于跨线程传递通知
_notify_queue = Queue()

# 日志队列 - 用于跨线程传递日志
_log_queue = Queue()

# 日志区元素（每次页面加载都创建新实例）
log_area = None
scroll_container = None

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

def _is_element_active(element) -> bool:
    """判断元素关联的客户端是否仍然活跃，避免操作已删除的客户端"""
    if element is None:
        return False
    client = getattr(element, 'client', None)
    if client is None:
        return False
    # _deleted 标志在客户端删除后置为 True
    if getattr(client, '_deleted', False):
        return False
    # 没有任何 socket 连接也认为不活跃
    if not client.has_socket_connection:
        return False
    # 保险起见检查实例表
    if client.id not in Client.instances:
        return False
    return True


def create_log_area():
    """为当前客户端创建（或替换）日志区域"""
    global log_area, scroll_container

    # 每次新页面请求都重新创建，避免跨客户端复用导致“客户端已删除”错误
    with ui.scroll_area().classes('w-full h-48 border border-gray-300 rounded bg-white') as scroll:
        scroll_container = scroll
        log_area = ui.html(sanitize=False).classes('font-mono text-sm p-2').style('padding-bottom: 20px;')

    # 页面对应客户端删除时清理引用
    current_client = context.client if hasattr(context, "client") else None
    if current_client:
        def _clear_on_delete(_=None):
            global log_area, scroll_container
            log_area = None
            scroll_container = None
        current_client.on_delete(_clear_on_delete)

    return log_area

def log(*args, sep=' ', end='\n', file=None, flush=True, with_timestamp=None, color=None):
    """
    兼容 print 的 log 函数，输出到 log_area 和标准输出
    带时间戳（可全局控制）和颜色支持
    使用队列机制确保线程安全和实时更新
    """
    global LOG_USE_TIMESTAMP

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

    # 将日志放入队列，由定时器处理UI更新
    _log_queue.put({
        'message': display_message,
        'color': color
    })

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

def _process_log_queue():
    """处理日志队列中的消息"""
    global log_area

    if not _is_element_active(log_area):
        return

    updated = False
    while not _log_queue.empty():
        try:
            item = _log_queue.get_nowait()
            color_value = COLOR_MAP.get(item['color'], COLOR_MAP[None])
            html_message = (
                f'<div style="color: {color_value}; margin: 0; padding: 0; line-height: 1.2;">'
                f'{item["message"]}</div>'
            )

            current_content = log_area.content if hasattr(log_area, 'content') and log_area.content else ""
            log_area.content = current_content + html_message
            updated = True
        except Exception as e:
            print(f"Process log failed: {e}", flush=True)

    if updated:
        try:
            log_area.update()
            if _is_element_active(scroll_container):
                scroll_container.scroll_to(percent=1.0)
        except Exception as e:
            print(f"Scroll/update log area failed: {e}", flush=True)


def _process_notify_queue():
    """处理通知队列中的消息"""
    # 若当前没有活跃的客户端，直接跳过，避免触发“客户端已删除”警告
    if not _is_element_active(log_area):
        return

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
            print(f"Process notify failed: {e}", flush=True)


def init_notify_timer():
    """初始化通知和日志定时器，需要在页面创建后调用（每个客户端各一次）"""
    ui.timer(0.1, _process_notify_queue)
    ui.timer(0.05, _process_log_queue)  # 更频繁地处理日志以确保实时性
