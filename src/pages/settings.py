from nicegui import ui
from ex4nicegui import to_ref, rxui
from logic.instrument import check_connection
import serial.tools.list_ports
from logic.config import ip_addr, com_num 

def list_serial_ports():
    """扫描并返回本机可用串口列表"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def settings_page():
    with ui.column().classes('p-4 gap-4') as container:
        ui.label('设置').classes('text-2xl font-bold')

        # --- 串口选择 (并排布局) ---
        
        initial_ports = list_serial_ports()
        
        if initial_ports and (not com_num.value or com_num.value not in initial_ports):
            com_num.value = initial_ports[0]
        
        placeholder_option = "未检测到可用串口"

        # 使用响应式变量存储串口列表
        available_ports = to_ref(initial_ports if initial_ports else [placeholder_option])
        
        # 提示标签
        no_port_label = ui.label("").classes('text-red-500 text-sm')
        
        def update_serial_ports():
            """执行串口扫描和UI更新的逻辑"""
            current_ports = list_serial_ports()
            
            if current_ports:
                # 更新响应式变量
                available_ports.value = current_ports
                
                # 检查当前选中的值是否依然有效，无效则重置
                if not com_num.value or com_num.value not in current_ports:
                    com_num.value = current_ports[0]
                
                # 清除提示
                no_port_label.text = ""
                
                ui.notify(f'成功刷新：找到 {len(current_ports)} 个串口', type='positive')
                
            else:
                # 如果没有可用串口
                available_ports.value = [placeholder_option]
                com_num.value = placeholder_option
                
                # 显示提示
                no_port_label.text = "未检测到可用串口设备"
                
                ui.notify('未检测到可用串口设备', type='warning')

        # 使用 rxui.select 并动态设置禁用属性
        with ui.row().classes('w-full items-center gap-2'):
            # 串口选择框：使用 rxui.select 并绑定响应式变量
            com_select = rxui.select(
                options=available_ports,
                value=com_num,
                label='串口选择'
            ).props('outlined clearable').classes('grow')
            
            # 初始状态：如果没有串口则禁用
            if not initial_ports:
                com_select.props('disabled')
            
            # 刷新按钮：图标按钮，保持小巧并与下拉框对齐
            ui.button(
                icon='refresh', 
                on_click=update_serial_ports
            ).props('flat round color=primary').tooltip('刷新串口列表')
            
        # 初始状态配置
        if not initial_ports:
            no_port_label.text = "未检测到可用串口设备"

        # 将提示标签放在下拉框的下方
        no_port_label

        # --- IP 输入框 ---
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