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
    
    with ui.column().classes('p-4 gap-4') as container:
        # 主要内容区域
        with ui.row().classes('w-full gap-4'):
            # 左侧区域
            with ui.column().classes('flex-none gap-4').style('width: 350px'):
                # 上方：信道和BLE制式选择器（水平排列）
                with ui.row().classes('w-full gap-4'):
                    # 信道选择器
                    channel_selector = GeneralSelector(
                        selector_name="信道",
                        options=list(range(40)),
                        value=[0],
                        items_per_row=5
                        #on_selection_change=lambda lst: log(f"信道选择变化: {lst}")
                    )

                    # BLE 制式选择器
                    ble_format_selector = GeneralSelector(
                        selector_name="BLE制式",
                        options=["LE1M", "LE2M", "LES2", "LES8"],
                        value=["LE1M"],
                        items_per_row=3,
                        items_per_line_in_result=3
                        #on_selection_change=lambda lst: log(f"BLE制式选择变化: {lst}")
                    )

                # 下方：其他控制参数（垂直排列）
                with ui.column().classes('w-full gap-2'):
                    dump_type = ui.select(options = {0:'noise',1:'tone',2:'wave'}, value=0,label="Dump类型").props('outlined clearable').style('min-width: 170px')
                    signal_amptd = ui.number(label='信号功率', value=-70,step=0.1, placeholder='输入信号功率(dBm)').props('outlined clearable debounce="500"')
                    cable_loss = ui.number(label='线损', value=0.65,step=0.01,placeholder='输入线损(dB)').props('outlined clearable debounce="500"')

                    # 添加任务状态指示器
                    status_label = ui.label('就绪').classes('text-lg font-medium text-green-600')
                    
                    # 开始Dump按钮
                    ui.button(
                        "开始Dump",
                        on_click=lambda: start_dump(),
                        color="blue"
                    ).classes('mb-4')
            
            # 右侧图表区域 - 垂直排列，占据大部分空间
            with ui.row().classes('flex-1 gap-4'):
                # 频域图表容器
                with ui.column().classes('flex-2'):
                    ui.label('频域图表').classes('text-lg font-bold mb-2')
                    freq_chart_container = ui.plotly({}).classes('w-full').style('height: 500px; min-width: 850px')
                # 时域图表容器
                with ui.column().classes('flex-1'):
                    ui.label('时域图表').classes('text-lg font-bold mb-2')
                    time_chart_container = ui.plotly({}).classes('w-full').style('height: 500px; min-width: 650px')

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
            
            def update_charts(time_fig, freq_fig):
                """在主线程中更新图表的回调函数"""
                time_chart_container.figure = time_fig
                freq_chart_container.figure = freq_fig
                time_chart_container.update()
                freq_chart_container.update()
            
            def run_task():
                try:
                    iqdump(
                        ip_str=ip_addr.value,
                        dump_type=dump_type.value,
                        AMPTD=signal_amptd.value,
                        cable_loss=cable_loss.value,
                        chn_list=selected_channels,
                        ble_modes_list=selected_ble_modes,
                        chart_update_callback=update_charts
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

        # 统一日志区
        from pages.layout import log_area
        log_area  # 直接挂在页面下方

    return container
