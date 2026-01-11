from nicegui import ui
from pages.home import home_page
from pages.settings import settings_page
from pages.data_view import data_view_page
from db.db_manager import init_db  # 导入数据库初始化函数

# ---------- 初始化数据库 ----------
init_db(table_name="ble_test_results")  # 启动时自动创建表和数据库

# 创建页面容器
home_container = home_page()
settings_container = settings_page()
data_view_container = data_view_page()

# 初始显示首页
home_container.visible = True
settings_container.visible = False
data_view_container.visible = False

# 切换函数
def show_home():
    home_container.visible = True
    settings_container.visible = False
    data_view_container.visible = False

def show_settings():
    home_container.visible = False
    settings_container.visible = True
    data_view_container.visible = False

def show_data_view():
    home_container.visible = False
    settings_container.visible = False
    data_view_container.visible = True

# 顶部导航栏
with ui.header().classes('bg-blue-600 text-white'):
    with ui.row().classes('w-full items-center justify-between p-2'):
        ui.label('Test Studio').classes('text-xl font-bold')
        with ui.row().classes('gap-4'):
            ui.button('首页', on_click=show_home).props('icon=home flat')
            ui.button('数据查看', on_click=show_data_view).props('icon=table_chart flat')
            ui.button('设置', on_click=show_settings).props('icon=settings flat')

# 启动应用
ui.run(title='Test Studio', port=8080)
