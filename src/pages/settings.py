from nicegui import ui
from ex4nicegui import to_ref, rxui
from logic.instrument import check_connection
import serial.tools.list_ports
from logic.config import ip_addr, com_num, fs, SN, vpp, nbit, dump_file_path
import os
from pages.layout import log
from utils.file_dialog import select_folder 

def list_serial_ports():
    """扫描并返回本机可用串口列表"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def settings_page():
    with ui.column().classes('p-4 gap-4') as container:
        ui.label('设置').classes('text-2xl font-bold')

        # --- 串口选择 (并排布局) ---
        
        initial_ports = list_serial_ports()

        placeholder_option = "未检测到可用串口"

        # 使用响应式变量存储串口列表
        available_ports = to_ref(initial_ports if initial_ports else [placeholder_option])

        # 确保com_num的值在可用列表中,否则重置
        if initial_ports:
            if not com_num.value or com_num.value not in initial_ports:
                com_num.value = initial_ports[0]
        else:
            # 如果没有可用串口,设置为placeholder
            if com_num.value not in [placeholder_option]:
                com_num.value = placeholder_option
        
        def update_serial_ports():
            """执行串口扫描和UI更新的逻辑"""
            current_ports = list_serial_ports()
            
            if current_ports:
                # 更新响应式变量
                available_ports.value = current_ports
                
                # 检查当前选中的值是否依然有效，无效则重置
                if not com_num.value or com_num.value not in current_ports:
                    com_num.value = current_ports[0]
                
                # 启用下拉框
                com_select.props(remove='disabled')
                
                ui.notify(f'成功刷新：找到 {len(current_ports)} 个串口', type='positive')
                
            else:
                # 如果没有可用串口
                available_ports.value = [placeholder_option]
                com_num.value = placeholder_option
                
                # 禁用下拉框
                com_select.props('disabled')
                
                ui.notify('未检测到可用串口设备', type='warning')

        # 添加点击事件处理函数
        def on_dropdown_focus():
            """下拉框获得焦点时自动刷新串口列表"""
            update_serial_ports()

        # 串口选择框：使用 rxui.select 并绑定响应式变量
        com_select = rxui.select(
            options=available_ports,
            value=com_num,
            label='串口选择'
        ).props('outlined clearable').classes('w-full')
        
        # 为下拉框添加点击事件监听器
        com_select.on('focus', on_dropdown_focus)
        
        # 初始状态：如果没有串口则禁用
        if not initial_ports:
            com_select.props('disabled')

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

        # --- 分隔线 ---
        ui.separator()
        ui.label('IQ 数据采集参数').classes('text-xl font-bold mt-4')

        # --- IQ 参数配置 ---
        with ui.row().classes('gap-4 w-full'):
            rxui.number(
                "采样率 (Hz)",
                value=fs,
                format="%.0f",
                step=1e6,
                min=1e6,
                max=100e6
            ).props('outlined').classes('flex-1')

            rxui.number(
                "采样点数",
                value=SN,
                format="%.0f",
                step=1024,
                min=512,
                max=16384
            ).props('outlined').classes('flex-1')

        with ui.row().classes('gap-4 w-full'):
            rxui.number(
                "ADC参考电压 Vpp (V)",
                value=vpp,
                format="%.2f",
                step=0.1,
                min=0.1,
                max=5.0
            ).props('outlined').classes('flex-1')

            rxui.number(
                "ADC位数",
                value=nbit,
                format="%.0f",
                step=1,
                min=8,
                max=16
            ).props('outlined').classes('flex-1')

        # --- 分隔线 ---
        ui.separator()
        ui.label('文件存储配置').classes('text-xl font-bold mt-4')

        # --- 文件路径配置 ---
        with ui.row().classes('gap-2 w-full items-center'):
            rxui.input(
                "IQ Dump 文件存放路径",
                value=dump_file_path,
                placeholder="请输入文件存放路径"
            ).props('outlined clearable').classes('flex-1')

            ui.button(
                "浏览",
                icon='folder_open',
                on_click=lambda: browse_folder(),
                color='blue'
            )

            ui.button(
                "打开文件夹",
                icon='folder',
                on_click=lambda: open_folder(),
                color='green'
            )

        def browse_folder():
            """浏览并选择文件夹"""
            try:
                # 获取初始目录 - 优先使用上次选择的目录
                last_selected_dir = getattr(browse_folder, 'last_dir', None)
                if last_selected_dir and os.path.exists(last_selected_dir):
                    initial_dir = last_selected_dir
                elif dump_file_path.value and os.path.exists(dump_file_path.value):
                    initial_dir = dump_file_path.value
                else:
                    initial_dir = None

                # 打开文件夹选择对话框
                selected_path = select_folder(
                    title="选择IQ Dump文件存放路径",
                    initial_dir=initial_dir
                )

                if selected_path:
                    # 保存选择的目录供下次使用
                    browse_folder.last_dir = selected_path
                    dump_file_path.value = selected_path
                    ui.notify(f'已选择路径: {selected_path}', type='positive')
                    log(f'文件存放路径已更新: {selected_path}', color='green')
                else:
                    ui.notify('未选择文件夹', type='info')

            except Exception as e:
                ui.notify(f'选择文件夹失败: {str(e)}', type='negative')
                log(f'选择文件夹失败: {str(e)}', color='red')

        def open_folder():
            """打开当前配置的文件夹"""
            try:
                folder_path = dump_file_path.value
                # 如果文件夹不存在,先创建
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    log(f'创建文件夹: {folder_path}', color='green')

                # 打开文件夹
                os.startfile(folder_path)
                ui.notify(f'已打开文件夹: {folder_path}', type='positive')
            except Exception as e:
                ui.notify(f'打开文件夹失败: {str(e)}', type='negative')
                log(f'打开文件夹失败: {str(e)}', color='red')
            
    return container
