from nicegui import ui
from ex4nicegui import to_ref, rxui
from components.GeneralSelector import GeneralSelector
from logic.instrument import check_connection
from pages.layout import log, notify
from logic.iqdump import iqdump, SerialPortError
from logic.config import ip_addr, com_num, dut_id, batch_id, fs, SN, vpp, nbit, dump_file_path
from logic.iq_file_parser import parse_iq_file, list_iq_files
from utils.file_dialog import select_file
import threading
import os

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
                    # DUT和批次信息
                    rxui.input("DUT编号", value=dut_id, placeholder="输入DUT编号, 如: #3, #4").props('outlined clearable')
                    rxui.input("批次编号", value=batch_id, placeholder="自动生成或手动输入").props('outlined clearable')

                    dump_type = ui.select(options = {0:'noise',1:'tone',2:'wave',3:'NF'}, value=0,label="Dump类型").props('outlined clearable').style('min-width: 170px')
                    signal_amptd = ui.number(label='信号功率', value=-80,step=0.1, placeholder='输入信号功率(dBm)').props('outlined clearable debounce="500"')
                    cable_loss = ui.number(label='线损', value=0.65,step=0.01,placeholder='输入线损(dB)').props('outlined clearable debounce="500"')

                    # 添加任务状态指示器
                    status_label = ui.label('就绪').classes('text-lg font-medium text-green-600')

                    # 开始Dump按钮
                    ui.button(
                        "开始Dump",
                        on_click=lambda: start_dump(),
                        color="blue"
                    ).classes('mb-2')

                    # 分隔线
                    ui.separator().classes('my-2')
                    ui.label('IQ 文件重绘').classes('text-sm font-bold')

                    # 显示当前选择的文件
                    selected_file_label = ui.label('未选择文件').classes('text-xs text-gray-500 mb-2')

                    # 文件操作按钮
                    ui.button(
                        "浏览并选择IQ文件",
                        icon='folder_open',
                        on_click=lambda: browse_and_redraw(),
                        color='purple'
                    ).classes('w-full')
            
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

        # 浏览并选择IQ文件重新绘图
        def browse_and_redraw():
            """打开文件选择对话框,选择IQ文件并重新绘制图表"""
            try:
                # 获取初始目录 - 优先使用上次选择的文件所在目录
                last_selected_dir = getattr(browse_and_redraw, 'last_dir', None)
                if last_selected_dir and os.path.exists(last_selected_dir):
                    initial_dir = last_selected_dir
                elif dump_file_path.value and os.path.exists(dump_file_path.value):
                    initial_dir = dump_file_path.value
                else:
                    initial_dir = None

                # 打开文件选择对话框
                selected_file_path = select_file(
                    title="选择IQ Dump文件",
                    initial_dir=initial_dir,
                    filetypes=[
                        ("文本文件", "*.txt"),
                        ("所有文件", "*.*")
                    ]
                )

                if not selected_file_path:
                    log('未选择文件', color='yellow')
                    return

                # 保存选择的目录供下次使用
                browse_and_redraw.last_dir = os.path.dirname(selected_file_path)

                # 更新显示的文件名
                file_name = os.path.basename(selected_file_path)
                selected_file_label.text = f'已选择: {file_name}'
                log(f'已选择文件: {file_name}', color='blue')

                def parse_and_draw():
                    try:
                        log(f'正在解析文件: {file_name}', color='blue')

                        # 从文件名中提取信息 (如果可能)
                        # 文件名格式: iqdata_LE1M_2402_Tone.txt
                        parts = file_name.replace('iqdata_', '').replace('.txt', '').split('_')

                        ble_mode = None
                        chn = None
                        dump_noise = 0

                        if len(parts) >= 2:
                            ble_mode = parts[0]  # 例如 LE1M
                            try:
                                freq = int(parts[1])  # 例如 2402
                                chn = (freq - 2400) // 2  # 转换为信道号
                            except:
                                pass

                        if len(parts) >= 3:
                            dump_type_str = parts[2].lower()
                            dump_noise = 1 if 'noise' in dump_type_str else 0

                        # 解析文件并绘图
                        result = parse_iq_file(
                            file_path=selected_file_path,
                            fs=fs.value,
                            vpp=vpp.value,
                            nbit=int(nbit.value),
                            sg_pwr=signal_amptd.value,
                            dump_noise=dump_noise,
                            chn=chn,
                            ble_mode=ble_mode
                        )

                        if result and 'time_chart' in result and 'freq_chart' in result:
                            # 使用容器上下文在主事件循环中更新图表
                            def update_charts_ui():
                                with container:
                                    time_chart_container.figure = result['time_chart']
                                    freq_chart_container.figure = result['freq_chart']
                                    time_chart_container.update()
                                    freq_chart_container.update()

                            with container:
                                ui.timer(0.01, update_charts_ui, once=True)
                            log('成功重新绘制图表', color='green')
                        else:
                            log('文件解析失败或数据格式不正确', color='red')

                    except Exception as e:
                        log(f'重新绘图时发生错误: {str(e)}', color='red')

                # 在后台线程中执行解析
                threading.Thread(target=parse_and_draw, daemon=True).start()

            except Exception as e:
                log(f'选择文件失败: {str(e)}', color='red')

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
                error_msg = None
                try:
                    log(com_num.value)
                    iqdump(
                        fs=fs.value,
                        SN=int(SN.value),
                        vpp=vpp.value,
                        nbit=int(nbit.value),
                        ip_str=ip_addr.value,
                        com_num=int(com_num.value[3:]),
                        dump_type=dump_type.value,
                        AMPTD=signal_amptd.value,
                        cable_loss=cable_loss.value,
                        chn_list=selected_channels,
                        ble_modes_list=selected_ble_modes,
                        chart_update_callback=update_charts,
                        dut_id=dut_id.value,
                        batch_id=batch_id.value,
                        save_file_path=dump_file_path.value
                    )
                except SerialPortError as e:
                    error_msg = str(e)
                    log(f"串口错误: {error_msg}", color="red")
                except Exception as e:
                    error_msg = str(e)
                    log(f"测试过程中发生错误: {error_msg}")
                finally:
                    # 测试完成后更新状态
                    is_running.value = False
                    status_label.text = '测试完成'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    log("任务执行完成")
                    # 如果有错误，发送通知
                    if error_msg:
                        notify(error_msg, type='negative')
            # 启动新线程执行任务
            threading.Thread(target=run_task, daemon=True).start()

        # 统一日志区
        from pages.layout import log_area
        log_area  # 直接挂在页面下方

    return container
