from nicegui import ui
from pages.layout import create_log_area, clear_log


def log_page():
    """日志页面"""
    with ui.column().classes('w-full p-4 gap-3').style('height: calc(100vh - 120px);') as container:
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('日志').classes('text-xl font-bold')
            ui.button('清除日志', icon='clear', on_click=clear_log)
        create_log_area(height='100%')
    return container
