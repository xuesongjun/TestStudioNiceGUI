from nicegui import ui
from ex4nicegui import to_ref
from components.GeneralSelector import GeneralSelector
from logic.instrument import check_connection
from pages.layout import log
from logic.iqdump import iqdump
from logic.config import ip_addr
import threading

def home_page():
    # 创建任务状态引用
    is_running = to_ref(False)
    
    with ui.column().classes('p-4 gap-4 justify-end') as container:
        with ui.row().classes('full-width justify-end q-g-md'):
            # 信道选择器
            channel_selector = GeneralSelector(
                selector_name="信道",
                options=list(range(40)),
                items_per_row=5
                #on_selection_change=lambda lst: log(f"信道选择变化: {lst}")
            )

            # BLE 制式选择器
            ble_format_selector = GeneralSelector(
                selector_name="BLE制式",
                options=["LE1M", "LE2M", "LES2", "LES8"],
                items_per_row=3,
                items_per_line_in_result=3
                #on_selection_change=lambda lst: log(f"BLE制式选择变化: {lst}")
            )

        # 其他参数
        dump_type = ui.select(options = {0:'noise',1:'tone',2:'wave'}, value=0,label="Dump类型").props('outlined clearable').style('min-width: 170px')
        signal_amptd = ui.input(label='信号功率', placeholder='输入信号功率(dBm)').props('outlined clearable debounce="500"')
        cable_loss = ui.input(label='线损', placeholder='输入线损(dB)').props('outlined clearable debounce="500"')

        # 添加任务状态指示器
        status_label = ui.label('就绪').classes('text-lg font-medium text-green-600')
        
        # 封装开始测试的逻辑
        def start_dump():
            if is_running.value:
                log("测试任务正在运行中，请等待完成后再开始新任务")
                return
            
            # 检查是否有选择信道和BLE制式
            selected_channels = channel_selector.get_selected_list()
            selected_ble_modes = ble_format_selector.get_selected_list()
            
            if not selected_channels:
                log("请至少选择一个信道")
                return
            
            if not selected_ble_modes:
                log("请至少选择一个BLE制式")
                return
            
            # 更新状态为运行中
            is_running.value = True
            status_label.text = '正在执行测试...'
            status_label.classes(remove='text-green-600', add='text-blue-600')
            
            def run_task():
                try:
                    iqdump(
                        ip_str=ip_addr.value,
                        dump_type=dump_type.value,
                        AMPTD=signal_amptd.value,
                        cable_loss=cable_loss.value,
                        chn_list=selected_channels,
                        ble_modes_list=selected_ble_modes
                    )
                except Exception as e:
                    log(f"测试过程中发生错误: {str(e)}")
                finally:
                    # 测试完成后更新状态
                    is_running.value = False
                    status_label.text = '测试完成'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    # 在后台线程中，通过log函数来处理UI更新，它已经处理了线程安全问题
                    log("任务执行完成")
            # 启动新线程执行任务
            threading.Thread(target=run_task, daemon=True).start()

        # 开始Dump按钮
        ui.button(
            "开始Dump",
            on_click=start_dump,
            color="blue"
        ).classes('mb-4')

        # 统一日志区
        from pages.layout import log_area
        log_area  # 直接挂在页面下方

    return container
