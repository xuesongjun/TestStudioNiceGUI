from nicegui import ui
from ex4nicegui import to_ref, rxui
from components.GeneralSelector import GeneralSelector
from logic.instrument import check_connection
from pages.layout import log, notify
from logic.iqdump import iqdump, SerialPortError
from logic.gain_sweep import gain_sweep, GainSweepError, create_auto_config
from logic.config import ip_addr, com_num, dut_id, batch_id, fs, SN, vpp, nbit, dump_file_path
from logic.iq_file_parser import parse_iq_file, list_iq_files
from utils.file_dialog import select_file
import threading
import os
from datetime import datetime

def home_page():
    # 创建任务状态引用
    is_running = to_ref(False)
    # 创建停止标志
    stop_requested = to_ref(False)
    
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

                    # IQ Dump 模式选择
                    with ui.row().classes('w-full gap-2'):
                        iqdump_mode = ui.select(
                            options={0: 'rxdump', 1: 'phydump'},
                            value=0,
                            label="IQ模式"
                        ).props('outlined dense').classes('flex-1')

                        iqdump_trigger = ui.select(
                            options={0: 'free run', 1: 'trigger'},
                            value=0,
                            label="触发模式"
                        ).props('outlined dense').classes('flex-1')

                        iq_swap = ui.checkbox('IQ Swap', value=True).classes('self-center')

                    signal_amptd = ui.number(label='信号功率', value=-80,step=0.1, placeholder='输入信号功率(dBm)').props('outlined clearable debounce="500"')
                    cable_loss = ui.number(label='线损', value=0.7,step=0.01,placeholder='输入线损(dB)').props('outlined clearable debounce="500"')

                    # 添加任务状态指示器
                    status_label = ui.label('就绪').classes('text-lg font-medium text-green-600')

                    # 按钮区域
                    with ui.row().classes('w-full gap-2'):
                        # 开始Dump按钮
                        start_dump_btn = ui.button(
                            "开始Dump",
                            on_click=lambda: start_dump(),
                            color="blue"
                        ).classes('flex-1')

                        # 停止按钮
                        stop_btn = ui.button(
                            "停止",
                            icon='stop',
                            on_click=lambda: stop_test(),
                            color="red"
                        ).classes('flex-1')
                        stop_btn.set_enabled(False)  # 初始禁用

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

                    # 分隔线 - 批量增益测试
                    ui.separator().classes('my-2')
                    ui.label('批量增益测试').classes('text-sm font-bold')

                    # 增益配置文件选择
                    gain_config_file = to_ref("")
                    gain_config_label = ui.label('未选择配置文件').classes('text-xs text-gray-500')

                    with ui.row().classes('w-full gap-2'):
                        ui.button(
                            "选择配置",
                            icon='folder_open',
                            on_click=lambda: select_gain_config(),
                            color='orange'
                        ).classes('flex-1')

                        ui.button(
                            "生成配置",
                            icon='auto_fix_high',
                            on_click=lambda: show_auto_config_dialog(),
                            color='teal'
                        ).classes('flex-1')

                    # 测试信道选择（单选）
                    gain_test_chn = ui.number(label='测试信道', value=19, min=0, max=39, step=1).props('outlined').classes('w-full')

                    # 单音频偏
                    gain_tone_freq = ui.number(label='单音频偏(MHz)', value=1.0, step=0.1).props('outlined').classes('w-full')

                    # 开始批量增益测试按钮
                    ui.button(
                        "开始批量增益测试",
                        icon='play_arrow',
                        on_click=lambda: start_gain_sweep(),
                        color='teal'
                    ).classes('w-full')
            
            # 右侧图表区域 - 垂直排列，占据大部分空间
            with ui.column().classes('flex-1 gap-4'):
                # 图表区域
                with ui.row().classes('w-full gap-4'):
                    # 频域图表容器
                    with ui.column().classes('flex-2'):
                        ui.label('频域图表').classes('text-lg font-bold mb-2')
                        freq_chart_container = ui.plotly({}).classes('w-full').style('height: 500px; min-width: 850px')
                    # 时域图表容器
                    with ui.column().classes('flex-1'):
                        ui.label('时域图表').classes('text-lg font-bold mb-2')
                        time_chart_container = ui.plotly({}).classes('w-full').style('height: 500px; min-width: 650px')

                # 增益测试结果表格区域
                with ui.column().classes('w-full'):
                    ui.label('增益测试结果').classes('text-lg font-bold mb-2')
                    # 创建表格容器
                    result_table = ui.table(
                        columns=[
                            {'name': 'lna', 'label': 'LNA', 'field': 'lna', 'align': 'center'},
                            {'name': 'tia', 'label': 'TIA', 'field': 'tia', 'align': 'center'},
                            {'name': 'bbf', 'label': 'BBF', 'field': 'bbf', 'align': 'center'},
                            {'name': 'pga', 'label': 'PGA', 'field': 'pga', 'align': 'center'},
                            {'name': 'gain', 'label': 'Gain (dB)', 'field': 'gain', 'align': 'center'},
                        ],
                        rows=[],
                        row_key='id'
                    ).classes('w-full').style('max-height: 300px')

        # 停止测试函数
        def stop_test():
            """停止当前正在运行的测试"""
            if is_running.value:
                stop_requested.value = True
                log("正在停止测试...", color="yellow")
                notify("正在停止测试，请稍候...", type='warning')
            else:
                notify("当前没有正在运行的测试", type='info')

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

        # 选择增益配置文件
        def select_gain_config():
            try:
                file_path = select_file(
                    title="选择增益配置文件",
                    filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
                )
                if file_path:
                    gain_config_file.value = file_path
                    gain_config_label.text = f'已选择: {os.path.basename(file_path)}'
                    log(f'已选择配置文件: {file_path}', color='blue')
            except Exception as e:
                log(f'选择文件失败: {e}', color='red')

        # 创建示例配置文件
        def show_auto_config_dialog():
            """显示自动生成配置的对话框"""
            dialog = ui.dialog().props('persistent')
            with dialog, ui.card().classes('w-auto'):
                ui.label('自动生成增益配置').classes('text-lg font-bold mb-2')
                ui.label('增益 = 基准 + 控制字 × 步进').classes('text-xs text-gray-500 mb-2')

                # 表头
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.label('').classes('w-12')
                    ui.label('最小').classes('flex-1 text-center text-xs')
                    ui.label('最大').classes('flex-1 text-center text-xs')
                    ui.label('基准(dB)').classes('flex-1 text-center text-xs')
                    ui.label('步进(dB)').classes('flex-1 text-center text-xs')

                # LNA配置
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.label('LNA:').classes('w-12')
                    lna_min = ui.number(value=0, min=0, max=15).props('dense outlined').classes('flex-1')
                    lna_max = ui.number(value=8, min=0, max=15).props('dense outlined').classes('flex-1')
                    lna_base = ui.number(value=0, step=1).props('dense outlined').classes('flex-1')
                    lna_step_db = ui.number(value=3, min=0.5, max=10, step=0.5).props('dense outlined').classes('flex-1')

                # TIA配置
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.label('TIA:').classes('w-12')
                    tia_min = ui.number(value=0, min=0, max=15).props('dense outlined').classes('flex-1')
                    tia_max = ui.number(value=4, min=0, max=15).props('dense outlined').classes('flex-1')
                    tia_base = ui.number(value=0, step=1).props('dense outlined').classes('flex-1')
                    tia_step_db = ui.number(value=3, min=0.5, max=10, step=0.5).props('dense outlined').classes('flex-1')

                # BBF配置
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.label('BBF:').classes('w-12')
                    bbf_min = ui.number(value=0, min=0, max=15).props('dense outlined').classes('flex-1')
                    bbf_max = ui.number(value=4, min=0, max=15).props('dense outlined').classes('flex-1')
                    bbf_base = ui.number(value=0, step=1).props('dense outlined').classes('flex-1')
                    bbf_step_db = ui.number(value=2, min=0.5, max=10, step=0.5).props('dense outlined').classes('flex-1')

                # PGA配置
                with ui.row().classes('w-full gap-2 items-center'):
                    ui.label('PGA:').classes('w-12')
                    pga_min = ui.number(value=0, min=0, max=15).props('dense outlined').classes('flex-1')
                    pga_max = ui.number(value=4, min=0, max=15).props('dense outlined').classes('flex-1')
                    pga_base = ui.number(value=0, step=1).props('dense outlined').classes('flex-1')
                    pga_step_db = ui.number(value=2, min=0.5, max=10, step=0.5).props('dense outlined').classes('flex-1')

                # 目标输出功率
                target_output = ui.number(label='目标输出功率(dBm)', value=-5.0, step=0.5).props('outlined').classes('w-full mt-2')

                # 按钮
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('取消', on_click=dialog.close, color='gray')

                    def generate_config():
                        try:
                            sample_dir = os.path.join(os.getcwd(), "data")
                            os.makedirs(sample_dir, exist_ok=True)
                            sample_path = os.path.join(sample_dir, f"gain_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

                            create_auto_config(
                                file_path=sample_path,
                                lna_range=(int(lna_min.value), int(lna_max.value)),
                                tia_range=(int(tia_min.value), int(tia_max.value)),
                                bbf_range=(int(bbf_min.value), int(bbf_max.value)),
                                pga_range=(int(pga_min.value), int(pga_max.value)),
                                lna_base_db=float(lna_base.value),
                                lna_step_db=float(lna_step_db.value),
                                tia_base_db=float(tia_base.value),
                                tia_step_db=float(tia_step_db.value),
                                bbf_base_db=float(bbf_base.value),
                                bbf_step_db=float(bbf_step_db.value),
                                pga_base_db=float(pga_base.value),
                                pga_step_db=float(pga_step_db.value),
                                target_output_dbm=float(target_output.value)
                            )

                            # 自动选择生成的文件
                            gain_config_file.value = sample_path
                            gain_config_label.text = f'已选择: {os.path.basename(sample_path)}'

                            notify(f"配置文件已生成: {sample_path}", type='positive')
                            dialog.close()
                        except Exception as e:
                            log(f'生成配置文件失败: {e}', color='red')
                            notify(f"生成失败: {e}", type='negative')

                    ui.button('生成', on_click=generate_config, color='primary')

            dialog.open()

        # 开始批量增益测试
        def start_gain_sweep():
            if is_running.value:
                log("测试任务正在运行中，请等待完成后再开始新任务")
                notify("任务正在运行中", type='warning')
                return

            if not gain_config_file.value:
                log("请先选择增益配置文件", color="yellow")
                notify("请先选择增益配置文件", type='warning')
                return

            # 清空结果表格
            result_table.rows.clear()
            result_table.update()

            # 重置停止标志
            stop_requested.value = False

            # 更新状态和按钮
            is_running.value = True
            stop_btn.set_enabled(True)
            start_dump_btn.set_enabled(False)
            status_label.text = '正在执行批量增益测试...'
            status_label.classes(remove='text-green-600', add='text-blue-600')

            def update_charts(time_fig, freq_fig):
                """在主线程中更新图表的回调函数"""
                time_chart_container.figure = time_fig
                freq_chart_container.figure = freq_fig
                time_chart_container.update()
                freq_chart_container.update()

            def update_result_table(lna, tia, bbf, pga, measured_gain):
                """在主线程中更新结果表格的回调函数"""
                # 添加新行到表格
                new_row = {
                    'id': len(result_table.rows) + 1,
                    'lna': lna,
                    'tia': tia,
                    'bbf': bbf,
                    'pga': pga,
                    'gain': f"{measured_gain:.2f}" if measured_gain is not None else "N/A"
                }
                result_table.rows.append(new_row)
                result_table.update()

            def run_gain_sweep_task():
                error_msg = None
                try:
                    # 生成输出文件名
                    output_dir = os.path.join(os.getcwd(), "data", "gain_results")
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(
                        output_dir,
                        f"gain_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    )

                    # 获取选中的 BLE 制式
                    selected_ble_modes = ble_format_selector.get_selected_list()
                    ble_mode = selected_ble_modes[0] if selected_ble_modes else "LE1M"

                    gain_sweep(
                        config_file=gain_config_file.value,
                        ip_str=ip_addr.value,
                        com_num=int(com_num.value[3:]),
                        fs=fs.value,
                        SN=int(SN.value),
                        vpp=vpp.value,
                        nbit=int(nbit.value),
                        cable_loss=cable_loss.value,
                        tone_freq=gain_tone_freq.value,
                        chn=int(gain_test_chn.value),
                        ble_mode=ble_mode,
                        output_file=output_file,
                        chart_update_callback=update_charts,
                        result_callback=update_result_table,
                        stop_flag=lambda: stop_requested.value
                    )
                    if stop_requested.value:
                        notify("测试已停止", type='warning')
                    else:
                        notify(f"测试完成，结果已保存到: {output_file}", type='positive')
                except GainSweepError as e:
                    error_msg = str(e)
                    log(f"增益测试错误: {error_msg}", color="red")
                except Exception as e:
                    error_msg = str(e)
                    log(f"测试过程中发生错误: {error_msg}", color="red")
                finally:
                    is_running.value = False
                    stop_btn.set_enabled(False)
                    start_dump_btn.set_enabled(True)
                    stop_requested.value = False
                    status_label.text = '就绪'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    log("批量增益测试完成")
                    if error_msg:
                        notify(error_msg, type='negative')

            threading.Thread(target=run_gain_sweep_task, daemon=True).start()

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

            # 重置停止标志
            stop_requested.value = False

            # 更新状态和按钮
            is_running.value = True
            stop_btn.set_enabled(True)
            start_dump_btn.set_enabled(False)
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
                        iqdump_mode=iqdump_mode.value,
                        iqdump_trigger=iqdump_trigger.value,
                        iq_swap=iq_swap.value,
                        AMPTD=signal_amptd.value,
                        cable_loss=cable_loss.value,
                        chn_list=selected_channels,
                        ble_modes_list=selected_ble_modes,
                        chart_update_callback=update_charts,
                        dut_id=dut_id.value,
                        batch_id=batch_id.value,
                        save_file_path=dump_file_path.value,
                        stop_flag=lambda: stop_requested.value
                    )
                    if stop_requested.value:
                        notify("测试已停止", type='warning')
                    else:
                        notify("测试完成", type='positive')
                except SerialPortError as e:
                    error_msg = str(e)
                    log(f"串口错误: {error_msg}", color="red")
                except Exception as e:
                    error_msg = str(e)
                    log(f"测试过程中发生错误: {error_msg}")
                finally:
                    # 测试完成后更新状态和按钮
                    is_running.value = False
                    stop_btn.set_enabled(False)
                    start_dump_btn.set_enabled(True)
                    stop_requested.value = False
                    status_label.text = '就绪'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    log("任务执行完成")
                    # 如果有错误，发送通知
                    if error_msg:
                        notify(error_msg, type='negative')
            # 启动新线程执行任务
            threading.Thread(target=run_task, daemon=True).start()

    return container
