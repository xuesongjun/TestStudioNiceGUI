"""
BLE PER (Packet Error Rate) 测试页面
基于 NiceGUI 开发
"""
from nicegui import ui
from ex4nicegui import to_ref
from pages.layout import log, notify
from logic.ble_per_test import per_test, PerTestError, list_serial_ports
from logic.config import ip_addr
import threading
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def ble_per_page():
    """BLE PER 测试页面"""

    # 状态引用
    is_running = to_ref(False)
    stop_requested = to_ref(False)
    test_results = []

    with ui.column().classes('p-4 gap-4 w-full') as container:
        # 标题
        ui.label('BLE PER 测试').classes('text-2xl font-bold mb-4')

        # 主要内容区域
        with ui.row().classes('w-full gap-4'):
            # 左侧控制面板
            with ui.column().classes('flex-none gap-4').style('width: 300px'):
                # 连接设置
                with ui.card().classes('w-full'):
                    ui.label('连接设置').classes('text-lg font-bold mb-2')

                    chip_model = ui.select(
                        label='芯片型号',
                        options=['ECR2560', 'ECW6700'],
                        value='ECW6700'
                    ).props('outlined').classes('w-full')

                    # 串口选择
                    com_port = ui.select(
                        label='串口',
                        options=list_serial_ports(),
                        value=None
                    ).props('outlined').classes('w-full')

                    # 刷新串口按钮
                    def refresh_ports():
                        ports = list_serial_ports()
                        com_port.options = ports
                        com_port.update()
                        log("串口列表已刷新", color="blue")

                    ui.button('刷新串口', icon='refresh', on_click=refresh_ports).classes('w-full')

                    baudrate = ui.select(
                        label='波特率',
                        options=[9600, 19200, 38400, 57600, 115200, 460800, 921600],
                        value=115200
                    ).props('outlined').classes('w-full')

                # 测试参数
                with ui.card().classes('w-full'):
                    ui.label('测试参数').classes('text-lg font-bold mb-2')

                    # BLE 模式选择
                    ble_mode = ui.select(
                        label='BLE 模式',
                        options={0: '1M', 1: '2M', 2: 'LR500K (S2)', 3: 'LR125K (S8)'},
                        value=0
                    ).props('outlined').classes('w-full')

                    channel = ui.number(
                        label='RF信道 (0-39)',
                        value=0,
                        min=0,
                        max=39,
                        step=1
                    ).props('outlined').classes('w-full')

                    # 频率显示
                    freq_label = ui.label('频率: 2402 MHz').classes('text-blue-600 font-bold')

                    def update_freq():
                        freq = 2402 + channel.value * 2
                        freq_label.text = f'频率: {freq} MHz'

                    channel.on_value_change(lambda: update_freq())

                    start_power = ui.number(
                        label='起始功率 (dBm)',
                        value=0,
                        step=0.1
                    ).props('outlined').classes('w-full')

                    stop_power = ui.number(
                        label='截止功率 (dBm)',
                        value=-100,
                        step=0.1
                    ).props('outlined').classes('w-full')

                    power_step = ui.number(
                        label='功率步进 (dB)',
                        value=1,
                        min=0.1,
                        step=0.1
                    ).props('outlined').classes('w-full')

                    num_packets = ui.number(
                        label='发包数',
                        value=1500,
                        min=100,
                        step=100
                    ).props('outlined').classes('w-full')

                    cable_loss = ui.number(
                        label='线损 (dB)',
                        value=0.7,
                        min=0,
                        step=0.1
                    ).props('outlined').classes('w-full')

                # 控制按钮
                with ui.row().classes('w-full gap-2'):
                    start_btn = ui.button(
                        '开始测试',
                        icon='play_arrow',
                        color='green'
                    ).classes('flex-1')

                    stop_btn = ui.button(
                        '停止',
                        icon='stop',
                        color='red'
                    ).classes('flex-1')
                    stop_btn.set_enabled(False)

                # 进度条
                progress_bar = ui.linear_progress(value=0).classes('w-full')

                # 状态显示
                status_label = ui.label('就绪').classes('text-lg font-medium text-green-600')

            # 右侧图表和结果区域
            with ui.column().classes('flex-1 gap-4 min-w-0'):
                # 覆盖 Plotly 默认固定宽度，保证初始渲染即占满
                ui.add_head_html(
                    '<style>.per-chart .js-plotly-plot{width:100% !important;}</style>'
                )
                # 图表区域
                with ui.card().classes('w-full min-w-0').style('min-width:0'):
                    ui.label('PER / RSSI 曲线').classes('text-lg font-bold mb-2')

                    # 创建初始空图表
                    fig = make_subplots(specs=[[{"secondary_y": True}]])

                    # PER 曲线（左Y轴）
                    fig.add_trace(
                        go.Scatter(
                            x=[], y=[],
                            mode='lines+markers',
                            name='PER',
                            line=dict(color='blue', width=2),
                            marker=dict(size=8, color='blue'),
                            yaxis='y'
                        ),
                        secondary_y=False
                    )

                    # RSSI 曲线（右Y轴）
                    fig.add_trace(
                        go.Scatter(
                            x=[], y=[],
                            mode='lines+markers',
                            name='RSSI',
                            line=dict(color='green', width=2),
                            marker=dict(size=8, color='green', symbol='square'),
                            yaxis='y2'
                        ),
                        secondary_y=True
                    )

                    # 添加 PER=30.8% 参考线
                    fig.add_hline(
                        y=30.8,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="PER=30.8%",
                        annotation_position="right",
                        secondary_y=False
                    )

                    # 设置图表布局
                    fig.update_xaxes(title_text="功率 (dBm)")
                    fig.update_yaxes(
                        title_text="PER (%)",
                        range=[0, 110],
                        secondary_y=False
                    )
                    fig.update_yaxes(
                        title_text="RSSI (dBm)",
                        secondary_y=True
                    )

                    fig.update_layout(
                        height=650,
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        margin=dict(l=60, r=20, t=30, b=50),
                        autosize=True
                    )

                    # 创建 Plotly 图表组件，配置为响应式
                    per_chart = (
                        ui.plotly(fig)
                        .classes('w-full per-chart')
                        .style('width:100%;height:650px;display:block')
                    )
                    per_chart._props['config'] = {'responsive': True}

                # 结果表格区域
                with ui.card().classes('w-full'):
                    ui.label('测试结果').classes('text-lg font-bold mb-2')

                    result_table = ui.table(
                        columns=[
                            {'name': 'power', 'label': '功率(dBm)', 'field': 'power', 'align': 'center'},
                            {'name': 'tx_count', 'label': '发包数', 'field': 'tx_count', 'align': 'center'},
                            {'name': 'rx_count', 'label': '收包数', 'field': 'rx_count', 'align': 'center'},
                            {'name': 'per', 'label': 'PER(%)', 'field': 'per', 'align': 'center'},
                            {'name': 'rssi', 'label': 'RSSI(dBm)', 'field': 'rssi', 'align': 'center'},
                            {'name': 'agc', 'label': 'AGC', 'field': 'agc', 'align': 'center'},
                        ],
                        rows=[],
                        row_key='id'
                    ).classes('w-full').style('height: 250px')

        # 测试函数
        def stop_test():
            """停止测试"""
            if is_running.value:
                stop_requested.value = True
                log("正在停止 PER 测试...", color="yellow")
                notify("正在停止测试，请稍候...", type='warning')
            else:
                notify("当前没有正在运行的测试", type='info')

        def start_test():
            """开始测试"""
            if is_running.value:
                log("测试任务正在运行中，请等待完成后再开始新任务")
                notify("任务正在运行中", type='warning')
                return

            # 验证参数
            if not com_port.value:
                log("请选择串口", color="yellow")
                notify("请选择串口", type='warning')
                return

            # 提取串口号（格式: "COM1 - 描述"）
            port_name = com_port.value.split(" - ")[0] if " - " in com_port.value else com_port.value

            # 清空结果表格
            result_table.rows.clear()
            result_table.update()
            test_results.clear()

            # 清空图表
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(x=[], y=[], mode='lines+markers', name='PER',
                          line=dict(color='blue', width=2),
                          marker=dict(size=8, color='blue')),
                secondary_y=False
            )
            fig.add_trace(
                go.Scatter(x=[], y=[], mode='lines+markers', name='RSSI',
                          line=dict(color='green', width=2),
                          marker=dict(size=8, color='green', symbol='square')),
                secondary_y=True
            )
            fig.add_hline(y=30.8, line_dash="dash", line_color="red",
                         annotation_text="PER=30.8%", annotation_position="bottom left",
                         secondary_y=False)
            fig.update_xaxes(title_text="功率 (dBm)")
            fig.update_yaxes(title_text="PER (%)", range=[0, 110], secondary_y=False)
            fig.update_yaxes(title_text="RSSI (dBm)", secondary_y=True)
            fig.update_layout(height=650, hovermode='x unified', showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            margin=dict(l=60, r=20, t=30, b=50), autosize=True)
            per_chart.figure = fig
            per_chart.update()

            # 重置停止标志
            stop_requested.value = False

            # 更新状态和按钮
            is_running.value = True
            stop_btn.set_enabled(True)
            start_btn.set_enabled(False)
            status_label.text = '正在执行 PER 测试...'
            status_label.classes(remove='text-green-600', add='text-blue-600')
            progress_bar.value = 0

            def update_chart():
                """更新图表"""
                # 提取数据
                powers = []
                pers = []
                rssis = []

                for result in test_results:
                    try:
                        power = float(result['power'])
                        powers.append(power)

                        # PER
                        per_str = result['per']
                        if per_str != "N/A":
                            pers.append(float(per_str))
                        else:
                            pers.append(None)

                        # RSSI
                        rssi_str = result['rssi']
                        if rssi_str != "N/A":
                            rssis.append(float(rssi_str))
                        else:
                            rssis.append(None)
                    except:
                        continue

                if not powers:
                    return

                # 创建新图表
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # PER 曲线（左Y轴）
                fig.add_trace(
                    go.Scatter(
                        x=powers, y=pers,
                        mode='lines+markers',
                        name='PER',
                        line=dict(color='blue', width=2),
                        marker=dict(size=8, color='blue')
                    ),
                    secondary_y=False
                )

                # RSSI 曲线（右Y轴）
                fig.add_trace(
                    go.Scatter(
                        x=powers, y=rssis,
                        mode='lines+markers',
                        name='RSSI',
                        line=dict(color='green', width=2),
                        marker=dict(size=8, color='green', symbol='square')
                    ),
                    secondary_y=True
                )

                # 添加 PER=30.8% 参考线
                fig.add_hline(
                    y=30.8,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="PER=30.8%",
                    annotation_position="right",
                    secondary_y=False
                )

                # 设置图表布局
                fig.update_xaxes(title_text="功率 (dBm)")
                fig.update_yaxes(
                    title_text="PER (%)",
                    range=[0, 110],
                    secondary_y=False
                )
                fig.update_yaxes(
                    title_text="RSSI (dBm)",
                    secondary_y=True
                )

                fig.update_layout(
                    height=650,
                    hovermode='x unified',
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=60, r=20, t=30, b=50),
                    autosize=True
                )

                # 更新图表
                per_chart.figure = fig
                per_chart.update()

            def update_result_table(power, tx_count, rx_count, per, rssi, agc_index):
                """更新结果表格的回调函数"""
                result = {
                    'id': len(test_results) + 1,
                    'power': f"{power:.1f}",
                    'tx_count': int(tx_count),
                    'rx_count': rx_count if rx_count >= 0 else "ERROR",
                    'per': f"{per:.2f}" if per >= 0 else "N/A",
                    'rssi': f"{rssi:.2f}" if rssi is not None else "N/A",
                    'agc': agc_index if agc_index is not None else "N/A"
                }
                test_results.append(result)
                result_table.rows.append(result)
                result_table.update()

                # 更新进度
                # 计算总功率点数
                if start_power.value > stop_power.value:
                    step = -abs(power_step.value)
                else:
                    step = abs(power_step.value)
                total_points = abs(int((stop_power.value - start_power.value) / step)) + 1
                progress_bar.value = len(test_results) / total_points

                # 更新图表
                update_chart()

            def run_per_test():
                """PER 测试线程"""
                error_msg = None
                try:
                    per_test(
                        chip_model=chip_model.value,
                        com_port=port_name,
                        baudrate=baudrate.value,
                        channel=int(channel.value),
                        start_power=start_power.value,
                        stop_power=stop_power.value,
                        power_step=power_step.value,
                        num_packets=int(num_packets.value),
                        cable_loss=cable_loss.value,
                        ip_str=ip_addr.value,
                        ble_mode=ble_mode.value,  # 传递 BLE 模式
                        stop_flag=lambda: stop_requested.value,
                        result_callback=update_result_table
                    )

                    if stop_requested.value:
                        notify("测试已停止", type='warning')
                    else:
                        notify("测试完成", type='positive')
                        log(f"PER 测试完成，共测试 {len(test_results)} 个功率点", color="green")

                except PerTestError as e:
                    error_msg = str(e)
                    log(f"PER 测试错误: {error_msg}", color="red")
                except Exception as e:
                    error_msg = str(e)
                    log(f"测试过程中发生错误: {error_msg}", color="red")

                finally:
                    # 恢复状态和按钮
                    is_running.value = False
                    stop_btn.set_enabled(False)
                    start_btn.set_enabled(True)
                    stop_requested.value = False
                    status_label.text = '就绪'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    progress_bar.value = 1.0
                    log("PER 测试任务完成")
                    if error_msg:
                        notify(error_msg, type='negative')

            # 启动测试线程
            threading.Thread(target=run_per_test, daemon=True).start()

        # 绑定按钮事件
        start_btn.on_click(start_test)
        stop_btn.on_click(stop_test)

    return container
