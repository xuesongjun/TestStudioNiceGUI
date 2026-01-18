import sys
import os

# 禁用stdout缓冲，确保日志实时输出
sys.stdout.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

from nicegui import ui
from pages.home import home_page
from pages.settings import settings_page
from pages.data_view import data_view_page
from pages.ble_per import ble_per_page
from pages.layout import init_notify_timer
from pages import layout
from pages.log_page import log_page
from pages.reg_compare import reg_compare_page
from db.db_manager import init_db  # 导入数据库初始化函数


@ui.page('/')
def index():
    """按客户端构建页面，避免使用已删除客户端的元素"""

    # 创建页面容器（log_page 需要先创建，以初始化 log_area）
    home_container = home_page()
    settings_container = settings_page()
    data_view_container = data_view_page()
    ble_per_container = ble_per_page()
    reg_compare_container = reg_compare_page()
    reg_compare_container.visible = False
    log_container = log_page()
    log_container.visible = False

    # 启动通知定时器（在 log_area 初始化后）
    init_notify_timer()

    # 切换函数
    def show_home():
        home_container.visible = True
        settings_container.visible = False
        data_view_container.visible = False
        ble_per_container.visible = False
        reg_compare_container.visible = False
        log_container.visible = False

    def show_settings():
        home_container.visible = False
        settings_container.visible = True
        data_view_container.visible = False
        ble_per_container.visible = False
        reg_compare_container.visible = False
        log_container.visible = False

    def show_data_view():
        home_container.visible = False
        settings_container.visible = False
        data_view_container.visible = True
        ble_per_container.visible = False
        reg_compare_container.visible = False
        log_container.visible = False

    def show_ble_per():
        home_container.visible = False
        settings_container.visible = False
        data_view_container.visible = False
        ble_per_container.visible = True
        reg_compare_container.visible = False
        log_container.visible = False

    def show_reg_compare():
        home_container.visible = False
        settings_container.visible = False
        data_view_container.visible = False
        ble_per_container.visible = False
        reg_compare_container.visible = True
        log_container.visible = False

    def show_log():
        home_container.visible = False
        settings_container.visible = False
        data_view_container.visible = False
        ble_per_container.visible = False
        reg_compare_container.visible = False
        log_container.visible = True
        # 刷新日志显示
        layout.refresh_log_display()

    # 初始显示首页
    show_home()

    # 顶部导航栏
    with ui.header().classes('bg-blue-600 text-white'):
        with ui.row().classes('w-full items-center justify-between p-2'):
            ui.label('Test Studio').classes('text-xl font-bold')
            with ui.row().classes('gap-4'):
                ui.button('IQ Dump', on_click=show_home).props('icon=home flat')
                ui.button('BLE PER', on_click=show_ble_per).props('icon=signal_cellular_alt flat')
                ui.button('寄存器对比', on_click=show_reg_compare).props('icon=compare flat')
                ui.button('数据查看', on_click=show_data_view).props('icon=table_chart flat')
                ui.button('日志', on_click=show_log).props('icon=article flat')
                ui.button('设置', on_click=show_settings).props('icon=settings flat')

if __name__ in {'__main__', '__mp_main__'}:
    # ---------- 初始化数据库 ----------
    init_db(table_name="ble_test_results")  # 启动时自动创建表和数据库

    # 启动应用
    ui.run(title='Test Studio', port=8081, reload=True)
