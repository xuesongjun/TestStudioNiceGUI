from nicegui import ui
from ex4nicegui import to_ref, rxui
from logic.instrument import check_connection
import serial.tools.list_ports
from logic.config import ip_addr

def list_serial_ports():
    """扫描并返回本机可用串口列表"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def settings_page():
    with ui.column().classes('p-4 gap-4') as container:
        ui.label('设置').classes('text-2xl font-bold')

        # 串口选择（动态获取）
        available_ports = list_serial_ports()
        com_select = ui.select(
            options=available_ports,
            label='串口选择'
        ).props('outlined clearable')

        # # 添加刷新按钮
        # def refresh_ports():
        #     com_select.options = list_serial_ports()
        #     ui.notify("串口列表已刷新")

        # ui.button('刷新串口', on_click=refresh_ports)

        # IP 输入框
        rxui.input(
            "VISA IP",
            value=ip_addr,
            placeholder="请输入 IP e.g. 169.254.42.178"
        ).props('outlined clearable debounce="500"')

        ui.button(
            "检测连接",
            on_click=lambda: check_connection(ip_addr.value),
            color="red"
        ).classes('mb-4')
        

    return container
