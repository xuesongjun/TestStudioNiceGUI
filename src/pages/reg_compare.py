"""
寄存器对比页面
"""
from nicegui import ui
from ex4nicegui import to_ref
from pages.layout import log, notify
from logic.reg_compare_logic import (
    list_serial_ports,
    load_register_config,
    get_register_groups,
    compare_registers,
    RegCompareError,
    CompareResult,
    sync_register,
    sync_registers_batch
)
import threading
import os
from pathlib import Path
from typing import List


def reg_compare_page():
    """寄存器对比页面"""

    # 状态变量
    is_running = to_ref(False)
    stop_requested = to_ref(False)
    device_count = to_ref(2)  # 默认2个设备
    config_file_path = to_ref("")

    # 设备串口列表（最多8个）
    device_ports = [to_ref("") for _ in range(8)]

    # 寄存器组选择状态
    register_groups_data = to_ref([])  # [{name, description, selected}]

    # 对比结果
    compare_results: List[CompareResult] = []

    # 统计数据
    total_regs = to_ref(0)
    diff_regs = to_ref(0)

    with ui.column().classes('p-4 gap-4 w-full') as container:
        ui.label('寄存器对比').classes('text-2xl font-bold mb-4')

        with ui.row().classes('w-full gap-4'):
            # ========== 左侧控制面板 ==========
            with ui.column().classes('flex-none gap-4').style('width: 320px'):

                # 配置文件选择
                with ui.card().classes('w-full'):
                    ui.label('配置文件').classes('text-lg font-bold mb-2')

                    # 扫描配置目录下的 YAML 文件
                    def get_config_files():
                        config_dir = Path(__file__).parent.parent / 'config' / 'register_maps'
                        if config_dir.exists():
                            return [f.name for f in config_dir.glob('*.yaml')] + [f.name for f in config_dir.glob('*.yml')]
                        return []

                    config_files = get_config_files()

                    def on_config_select(ps):
                        if ps.value:
                            config_dir = Path(__file__).parent.parent / 'config' / 'register_maps'
                            config_file_path.value = str(config_dir / ps.value)
                            load_register_groups_ui()
                            log(f"已加载配置: {ps.value}", color="green")

                    with ui.row().classes('w-full gap-2 items-center'):
                        config_select = ui.select(
                            label='选择配置',
                            options=config_files if config_files else ['无配置文件'],
                            value=None
                        ).props('outlined dense').classes('flex-1')

                        config_select.on('update:model-value', lambda: on_config_select(config_select))

                        def refresh_configs():
                            files = get_config_files()
                            config_select.options = files if files else ['无配置文件']
                            config_select.update()

                        ui.button(icon='refresh', on_click=refresh_configs).props('dense flat size=sm')

                # 设备数量配置
                with ui.card().classes('w-full'):
                    ui.label('设备配置').classes('text-lg font-bold mb-2')

                    with ui.row().classes('w-full items-center gap-2'):
                        ui.label('设备数量:')

                        def decrease_devices():
                            if device_count.value > 2:
                                device_count.value -= 1
                                update_device_panels()

                        def increase_devices():
                            if device_count.value < 8:
                                device_count.value += 1
                                update_device_panels()

                        ui.button('-', on_click=decrease_devices).props('dense round size=sm')
                        device_count_label = ui.label('2').classes('text-lg font-bold mx-2')
                        ui.button('+', on_click=increase_devices).props('dense round size=sm')

                    # 波特率选择
                    baudrate = ui.select(
                        label='波特率',
                        options=[9600, 19200, 38400, 57600, 115200, 460800, 921600],
                        value=115200
                    ).props('outlined dense').classes('w-full mt-2')

                # 设备串口选择面板容器
                device_panels_container = ui.column().classes('w-full gap-2')

                device_selects = []  # 保存串口选择器引用

                def create_device_panel(index: int):
                    """创建单个设备串口选择面板"""
                    with ui.card().classes('w-full p-2'):
                        with ui.row().classes('w-full items-center gap-2'):
                            ui.label(f'设备 {index + 1}').classes('font-bold text-sm').style('min-width: 50px')

                            port_select = ui.select(
                                label='串口',
                                options=list_serial_ports(),
                                value=None
                            ).props('outlined dense').classes('flex-1')

                            def refresh_ports(ps=port_select):
                                ports = list_serial_ports()
                                ps.options = ports
                                ps.update()

                            ui.button(icon='refresh', on_click=refresh_ports).props('dense flat size=sm')

                            # 绑定值到对应的响应式变量
                            def on_change(idx=index, ps=port_select):
                                device_ports[idx].value = ps.value if ps.value else ""

                            port_select.on('update:model-value', on_change)
                            device_selects.append(port_select)

                def update_device_panels():
                    """更新设备面板数量"""
                    device_count_label.text = str(device_count.value)
                    device_panels_container.clear()
                    device_selects.clear()

                    with device_panels_container:
                        for i in range(device_count.value):
                            create_device_panel(i)

                # 初始化设备面板
                update_device_panels()

                # 寄存器组选择
                with ui.card().classes('w-full'):
                    ui.label('寄存器组').classes('text-lg font-bold mb-2')

                    reg_group_container = ui.column().classes('w-full')
                    group_checkboxes = []

                    def load_register_groups_ui():
                        """加载寄存器组到UI"""
                        reg_group_container.clear()
                        group_checkboxes.clear()

                        if not config_file_path.value:
                            with reg_group_container:
                                ui.label('请先选择配置文件').classes('text-gray-400 text-sm')
                            return

                        try:
                            groups = get_register_groups(config_file_path.value)
                            register_groups_data.value = groups

                            with reg_group_container:
                                for group in groups:
                                    cb = ui.checkbox(
                                        f"{group['name']} ({group['count']}个)",
                                        value=True
                                    ).props('dense')
                                    group_checkboxes.append((group['name'], cb))
                        except Exception as e:
                            log(f"加载寄存器组失败: {e}", color="red")
                            with reg_group_container:
                                ui.label(f'加载失败: {e}').classes('text-red-500 text-sm')

                    def get_selected_groups():
                        """获取选中的寄存器组名称"""
                        return [name for name, cb in group_checkboxes if cb.value]

                    # 初始提示
                    with reg_group_container:
                        ui.label('请先选择配置文件').classes('text-gray-400 text-sm')

                # 控制按钮
                with ui.row().classes('w-full gap-2'):
                    start_btn = ui.button('开始对比', icon='compare', color='green').classes('flex-1')
                    stop_btn = ui.button('停止', icon='stop', color='red').classes('flex-1')
                    stop_btn.set_enabled(False)

                # 进度显示
                progress_bar = ui.linear_progress(value=0).classes('w-full')
                status_label = ui.label('就绪').classes('text-green-600')

            # ========== 右侧结果区域 ==========
            with ui.column().classes('flex-1 gap-4 min-w-0'):

                # 统计信息
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full justify-around'):
                        total_count_label = ui.label('总寄存器: 0').classes('text-lg')
                        diff_count_label = ui.label('差异: 0').classes('text-lg text-red-600 font-bold')
                        same_count_label = ui.label('相同: 0').classes('text-lg text-green-600')

                # 差异对比表格
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full items-center justify-between mb-2'):
                        ui.label('差异对比结果').classes('text-lg font-bold')
                        with ui.row().classes('gap-2'):
                            # 同步方向选择
                            sync_direction = ui.select(
                                label='同步方向',
                                options=['设备1 -> 设备2', '设备2 -> 设备1'],
                                value='设备1 -> 设备2'
                            ).props('outlined dense').style('width: 150px')

                            # 一键同步按钮
                            sync_all_btn = ui.button('一键同步全部', icon='sync', color='orange')

                    # 初始列定义（包含同步操作列）
                    initial_columns = [
                        {'name': 'group', 'label': '分组', 'field': 'group', 'align': 'left', 'sortable': True},
                        {'name': 'address', 'label': '地址', 'field': 'address', 'align': 'center', 'sortable': True},
                        {'name': 'device_0', 'label': '设备1', 'field': 'device_0', 'align': 'center'},
                        {'name': 'device_1', 'label': '设备2', 'field': 'device_1', 'align': 'center'},
                        {'name': 'sync', 'label': '同步', 'field': 'sync', 'align': 'center'},
                    ]

                    result_table = ui.table(
                        columns=initial_columns,
                        rows=[],
                        row_key='id',
                        pagination={'rowsPerPage': 50},
                        selection='multiple'
                    ).classes('w-full').style('max-height: 500px')

                    # 添加同步按钮的插槽
                    result_table.add_slot('body-cell-sync', '''
                        <q-td :props="props">
                            <q-btn flat dense icon="sync" color="primary" size="sm"
                                   @click="$parent.$emit('sync_row', props.row)" />
                        </q-td>
                    ''')

                    # 选中行同步按钮
                    with ui.row().classes('w-full gap-2 mt-2'):
                        sync_selected_btn = ui.button('同步选中项', icon='sync', color='blue')

                # 导出按钮
                with ui.row().classes('w-full gap-2'):
                    def export_csv():
                        if not compare_results:
                            notify("没有可导出的结果", type='warning')
                            return
                        # TODO: 实现CSV导出
                        notify("CSV导出功能待实现", type='info')

                    ui.button('导出CSV', icon='download', on_click=export_csv)
                    ui.button('清空结果', icon='clear', on_click=lambda: clear_results())

        # ========== 业务逻辑 ==========

        def clear_results():
            """清空结果"""
            compare_results.clear()
            result_table.rows.clear()
            result_table.selected.clear()  # 清除选中状态
            result_table.update()
            total_count_label.text = '总寄存器: 0'
            diff_count_label.text = '差异: 0'
            same_count_label.text = '相同: 0'

        def update_table_columns():
            """根据设备数量更新表格列"""
            columns = [
                {'name': 'group', 'label': '分组', 'field': 'group', 'align': 'left', 'sortable': True},
                {'name': 'address', 'label': '地址', 'field': 'address', 'align': 'center', 'sortable': True},
            ]
            for i in range(device_count.value):
                columns.append({
                    'name': f'device_{i}',
                    'label': f'设备{i+1}',
                    'field': f'device_{i}',
                    'align': 'center'
                })
            # 添加同步操作列
            columns.append({'name': 'sync', 'label': '同步', 'field': 'sync', 'align': 'center'})
            result_table.columns = columns
            result_table.update()

            # 更新同步方向选项
            options = []
            for i in range(device_count.value):
                for j in range(device_count.value):
                    if i != j:
                        options.append(f'设备{i+1} -> 设备{j+1}')
            sync_direction.options = options
            if options:
                sync_direction.value = options[0]
            sync_direction.update()

        def start_compare():
            """开始对比"""
            if is_running.value:
                notify("任务正在运行中", type='warning')
                return

            # 验证配置
            if not config_file_path.value:
                notify("请选择配置文件", type='warning')
                return

            # 获取有效的串口
            valid_ports = []
            for i in range(device_count.value):
                port = device_ports[i].value
                if not port:
                    notify(f"请选择设备{i+1}的串口", type='warning')
                    return
                valid_ports.append(port)

            # 检查串口是否重复
            if len(set(valid_ports)) != len(valid_ports):
                notify("不能选择相同的串口", type='warning')
                return

            # 获取选中的寄存器组
            selected_groups = get_selected_groups()
            if not selected_groups:
                notify("请至少选择一个寄存器组", type='warning')
                return

            # 更新表格列
            update_table_columns()

            # 重置状态
            stop_requested.value = False
            is_running.value = True
            start_btn.set_enabled(False)
            stop_btn.set_enabled(True)
            progress_bar.value = 0
            status_label.text = '正在连接设备...'
            status_label.classes(remove='text-green-600', add='text-blue-600')

            # 清空结果
            clear_results()

            def run_compare():
                error_msg = None
                total = 0
                diff = 0

                try:
                    # 加载寄存器配置
                    chip_model, all_registers = load_register_config(config_file_path.value)

                    # 过滤选中的寄存器组
                    registers = [r for r in all_registers if r.group in selected_groups]
                    total = len(registers)

                    log(f"开始对比 {len(valid_ports)} 个设备，共 {total} 个寄存器", color="blue")

                    def on_progress(current, total_count, msg):
                        progress_bar.value = current / total_count
                        status_label.text = msg

                    def on_result(result: CompareResult):
                        nonlocal diff
                        diff += 1

                        # 构建表格行
                        row = {
                            'id': len(compare_results) + 1,
                            'group': result.group,
                            'address': f'0x{result.address:08X}',
                        }

                        # 添加各设备的值
                        for i, value in result.values.items():
                            row[f'device_{i}'] = f'0x{value:08X}' if value is not None else 'ERROR'

                        compare_results.append(result)
                        result_table.rows.append(row)
                        result_table.update()

                        # 更新统计
                        diff_count_label.text = f'差异: {diff}'

                    # 执行对比
                    compare_registers(
                        device_ports=valid_ports,
                        baudrate=baudrate.value,
                        registers=registers,
                        stop_flag=lambda: stop_requested.value,
                        progress_callback=on_progress,
                        result_callback=on_result,
                        log_func=lambda msg: log(msg, color="blue")
                    )

                    # 更新统计
                    total_count_label.text = f'总寄存器: {total}'
                    same_count_label.text = f'相同: {total - diff}'

                    if stop_requested.value:
                        notify("对比已停止", type='warning')
                    else:
                        notify(f"对比完成，发现 {diff} 处差异", type='positive')
                        log(f"对比完成: 总共 {total} 个寄存器，{diff} 处差异", color="green")

                except RegCompareError as e:
                    error_msg = str(e)
                    log(f"对比错误: {error_msg}", color="red")
                except Exception as e:
                    error_msg = str(e)
                    log(f"对比过程发生错误: {error_msg}", color="red")
                finally:
                    is_running.value = False
                    start_btn.set_enabled(True)
                    stop_btn.set_enabled(False)
                    stop_requested.value = False
                    status_label.text = '就绪'
                    status_label.classes(remove='text-blue-600', add='text-green-600')
                    progress_bar.value = 1.0 if not error_msg else 0
                    if error_msg:
                        notify(error_msg, type='negative')

            threading.Thread(target=run_compare, daemon=True).start()

        def stop_compare():
            """停止对比"""
            if is_running.value:
                stop_requested.value = True
                log("正在停止对比...", color="yellow")

        def parse_sync_direction():
            """解析同步方向，返回 (源设备索引, 目标设备索引)"""
            direction = sync_direction.value
            if not direction:
                return 0, 1
            # 格式: "设备1 -> 设备2"
            parts = direction.replace('设备', '').split(' -> ')
            if len(parts) == 2:
                try:
                    src = int(parts[0]) - 1
                    dst = int(parts[1]) - 1
                    return src, dst
                except:
                    pass
            return 0, 1

        def sync_single_row(row):
            """同步单行寄存器"""
            if is_running.value:
                notify("请等待当前任务完成", type='warning')
                return

            src_idx, dst_idx = parse_sync_direction()
            src_port = device_ports[src_idx].value
            dst_port = device_ports[dst_idx].value

            if not src_port or not dst_port:
                notify("请先配置设备串口", type='warning')
                return

            # 从行数据中获取地址和源设备的值
            address_str = row.get('address', '')
            address = int(address_str, 16) if address_str.startswith('0x') else int(address_str)

            value_str = row.get(f'device_{src_idx}', '')
            if value_str == 'ERROR' or not value_str:
                notify("源设备值无效，无法同步", type='warning')
                return
            value = int(value_str, 16) if value_str.startswith('0x') else int(value_str)

            def do_sync():
                success = sync_register(
                    source_port=src_port,
                    target_port=dst_port,
                    baudrate=baudrate.value,
                    address=address,
                    value=value,
                    log_func=lambda msg: log(msg, color="blue")
                )
                if success:
                    notify(f"同步成功: 0x{address:08X}", type='positive')
                else:
                    notify(f"同步失败: 0x{address:08X}", type='negative')

            threading.Thread(target=do_sync, daemon=True).start()

        def sync_selected_rows():
            """同步选中的行"""
            if is_running.value:
                notify("请等待当前任务完成", type='warning')
                return

            selected = result_table.selected
            if not selected:
                notify("请先选择要同步的寄存器", type='warning')
                return

            src_idx, dst_idx = parse_sync_direction()
            src_port = device_ports[src_idx].value
            dst_port = device_ports[dst_idx].value

            if not src_port or not dst_port:
                notify("请先配置设备串口", type='warning')
                return

            # 收集要同步的寄存器
            registers = []
            for row in selected:
                address_str = row.get('address', '')
                address = int(address_str, 16) if address_str.startswith('0x') else int(address_str)

                value_str = row.get(f'device_{src_idx}', '')
                if value_str == 'ERROR' or not value_str:
                    continue
                value = int(value_str, 16) if value_str.startswith('0x') else int(value_str)
                registers.append((address, value))

            if not registers:
                notify("没有有效的寄存器可同步", type='warning')
                return

            def do_sync():
                is_running.value = True
                try:
                    success, fail = sync_registers_batch(
                        source_port=src_port,
                        target_port=dst_port,
                        baudrate=baudrate.value,
                        registers=registers,
                        log_func=lambda msg: log(msg, color="blue"),
                        progress_callback=lambda cur, total: setattr(progress_bar, 'value', cur / total)
                    )
                    notify(f"同步完成: 成功 {success}, 失败 {fail}", type='positive' if fail == 0 else 'warning')
                finally:
                    is_running.value = False
                    progress_bar.value = 0

            threading.Thread(target=do_sync, daemon=True).start()

        def sync_all_rows():
            """同步所有差异寄存器"""
            if is_running.value:
                notify("请等待当前任务完成", type='warning')
                return

            if not compare_results:
                notify("没有差异结果可同步", type='warning')
                return

            src_idx, dst_idx = parse_sync_direction()
            src_port = device_ports[src_idx].value
            dst_port = device_ports[dst_idx].value

            if not src_port or not dst_port:
                notify("请先配置设备串口", type='warning')
                return

            # 收集所有差异寄存器
            registers = []
            for result in compare_results:
                value = result.values.get(src_idx)
                if value is not None:
                    registers.append((result.address, value))

            if not registers:
                notify("没有有效的寄存器可同步", type='warning')
                return

            def do_sync():
                is_running.value = True
                sync_all_btn.set_enabled(False)
                try:
                    log(f"开始一键同步 {len(registers)} 个寄存器: {src_port} -> {dst_port}", color="blue")
                    success, fail = sync_registers_batch(
                        source_port=src_port,
                        target_port=dst_port,
                        baudrate=baudrate.value,
                        registers=registers,
                        log_func=lambda msg: log(msg, color="blue"),
                        progress_callback=lambda cur, total: setattr(progress_bar, 'value', cur / total)
                    )
                    notify(f"一键同步完成: 成功 {success}, 失败 {fail}", type='positive' if fail == 0 else 'warning')
                    log(f"一键同步完成: 成功 {success}, 失败 {fail}", color="green" if fail == 0 else "yellow")
                finally:
                    is_running.value = False
                    sync_all_btn.set_enabled(True)
                    progress_bar.value = 0

            threading.Thread(target=do_sync, daemon=True).start()

        # 绑定事件
        start_btn.on_click(start_compare)
        stop_btn.on_click(stop_compare)
        result_table.on('sync_row', lambda e: sync_single_row(e.args))
        sync_selected_btn.on_click(sync_selected_rows)
        sync_all_btn.on_click(sync_all_rows)

    return container
