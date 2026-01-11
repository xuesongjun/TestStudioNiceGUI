from nicegui import ui
from ex4nicegui import to_ref, rxui
from db.db_manager import query_results, get_all_dut_ids, get_all_batch_ids
import sqlite3
from pathlib import Path

DB_FILE = Path("data/test_results.db")

def data_view_page():
    """数据查看页面"""

    # 响应式变量存储表格数据
    table_data = to_ref([])

    # 筛选条件
    selected_dut = to_ref(None)
    selected_batch = to_ref(None)

    # 定义表格列
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
        {'name': 'dut_id', 'label': 'DUT编号', 'field': 'dut_id', 'align': 'center', 'sortable': True},
        {'name': 'batch_id', 'label': '批次编号', 'field': 'batch_id', 'align': 'center', 'sortable': True},
        {'name': 'chn', 'label': '信道', 'field': 'chn', 'align': 'center', 'sortable': True},
        {'name': 'rate', 'label': '制式', 'field': 'rate', 'align': 'center', 'sortable': True},
        {'name': 'noise', 'label': 'Noise(dBm)', 'field': 'noise', 'align': 'center', 'sortable': True},
        {'name': 'signal', 'label': 'Signal(dBm)', 'field': 'signal', 'align': 'center', 'sortable': True},
        {'name': 'gain', 'label': 'Gain(dB)', 'field': 'gain', 'align': 'center', 'sortable': True},
        {'name': 'dc', 'label': 'DC(dBm)', 'field': 'dc', 'align': 'center', 'sortable': True},
        {'name': 'snr', 'label': 'SNR(dB)', 'field': 'snr', 'align': 'center', 'sortable': True},
        {'name': 'image', 'label': 'Image(dBm)', 'field': 'image', 'align': 'center', 'sortable': True},
        {'name': 'imrr', 'label': 'IMRR(dB)', 'field': 'imrr', 'align': 'center', 'sortable': True},
        {'name': 'nf', 'label': 'NF(dB)', 'field': 'nf', 'align': 'center', 'sortable': True},
        {'name': 'sensitive', 'label': 'Sensitive(dBm)', 'field': 'sensitive', 'align': 'center', 'sortable': True},
        {'name': 'timestamp', 'label': '时间戳', 'field': 'timestamp', 'align': 'center', 'sortable': True},
    ]

    def load_data():
        """从数据库加载所有数据"""
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row  # 使用Row工厂以便按列名访问

                # 构建查询语句,支持筛选
                query = """
                    SELECT id, dut_id, batch_id, chn, rate, noise, signal, gain, dc, snr, image, imrr, nf, sensitive, timestamp
                    FROM ble_test_results
                    WHERE 1=1
                """
                params = []

                if selected_dut.value and selected_dut.value != "全部":
                    query += " AND dut_id = ?"
                    params.append(selected_dut.value)

                if selected_batch.value and selected_batch.value != "全部":
                    query += " AND batch_id = ?"
                    params.append(selected_batch.value)

                query += " ORDER BY dut_id, batch_id, chn, rate"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # 转换为字典列表,并格式化数值
                data = []
                for row in rows:
                    # 格式化信道显示为 "0(2402)" 格式
                    chn_display = f"{row['chn']}({2400 + row['chn'] * 2})" if row['chn'] is not None else '-'

                    data.append({
                        'id': row['id'],
                        'dut_id': row['dut_id'] if row['dut_id'] else '-',
                        'batch_id': row['batch_id'] if row['batch_id'] else '-',
                        'chn': chn_display,
                        'rate': row['rate'],
                        'noise': f"{row['noise']:.2f}" if row['noise'] is not None else '-',
                        'signal': f"{row['signal']:.2f}" if row['signal'] is not None else '-',
                        'gain': f"{row['gain']:.2f}" if row['gain'] is not None else '-',
                        'dc': f"{row['dc']:.2f}" if row['dc'] is not None else '-',
                        'snr': f"{row['snr']:.2f}" if row['snr'] is not None else '-',
                        'image': f"{row['image']:.2f}" if row['image'] is not None else '-',
                        'imrr': f"{row['imrr']:.2f}" if row['imrr'] is not None else '-',
                        'nf': f"{row['nf']:.2f}" if row['nf'] is not None else '-',
                        'sensitive': f"{row['sensitive']:.2f}" if row['sensitive'] is not None else '-',
                        'timestamp': row['timestamp']
                    })

                table_data.value = data
                ui.notify(f'已加载 {len(data)} 条记录', type='positive')

        except Exception as e:
            ui.notify(f'加载数据失败: {str(e)}', type='negative')

    def confirm_clear_data():
        """显示确认对话框"""
        with ui.dialog() as dialog, ui.card():
            ui.label('确认清空数据').classes('text-lg font-bold mb-4')
            ui.label('此操作将永久删除所有测试数据,无法恢复!').classes('text-red-600 mb-4')
            ui.label(f'当前共有 {len(table_data.value)} 条记录').classes('mb-4')

            with ui.row().classes('gap-2 w-full justify-end'):
                ui.button('取消', on_click=dialog.close, color='grey')
                ui.button('确认清空', on_click=lambda: clear_all_data(dialog), color='red')

        dialog.open()

    def clear_all_data(dialog):
        """清空所有数据"""
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("DELETE FROM ble_test_results")
                conn.commit()
            table_data.value = []
            ui.notify('数据已清空', type='positive')
            dialog.close()
        except Exception as e:
            ui.notify(f'清空数据失败: {str(e)}', type='negative')

    def export_to_txt():
        """导出数据到txt文件"""
        try:
            if not table_data.value:
                ui.notify('没有数据可导出', type='warning')
                return

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"data/export_{timestamp}.txt"

            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入表头
                f.write("ID\tDUT编号\t批次编号\t信道\t制式\tNoise(dBm)\tSignal(dBm)\tGain(dB)\tDC(dBm)\tSNR(dB)\tImage(dBm)\tIMRR(dB)\tNF(dB)\tSensitive(dBm)\t时间戳\n")
                f.write("-" * 200 + "\n")

                # 写入数据
                for row in table_data.value:
                    f.write(f"{row['id']}\t{row['dut_id']}\t{row['batch_id']}\t{row['chn']}\t{row['rate']}\t{row['noise']}\t{row['signal']}\t{row['gain']}\t{row['dc']}\t{row['snr']}\t{row['image']}\t{row['imrr']}\t{row['nf']}\t{row['sensitive']}\t{row['timestamp']}\n")

            ui.notify(f'数据已导出到 {file_path}', type='positive')
        except Exception as e:
            ui.notify(f'导出失败: {str(e)}', type='negative')

    with ui.column().classes('p-4 gap-4 w-full') as container:
        ui.label('数据查看').classes('text-2xl font-bold')

        # 筛选条件行
        with ui.row().classes('gap-4 mb-2'):
            # DUT 筛选下拉框
            dut_select = ui.select(
                label='筛选DUT',
                options=["全部"],
                value="全部",
                on_change=load_data
            ).props('outlined').style('min-width: 150px')

            # 批次筛选下拉框
            batch_select = ui.select(
                label='筛选批次',
                options=["全部"],
                value="全部",
                on_change=load_data
            ).props('outlined').style('min-width: 200px')

            # 刷新筛选选项按钮
            ui.button('刷新筛选项', on_click=lambda: update_filter_options(), icon='filter_list', color='blue')

        def update_filter_options():
            """更新筛选下拉框选项"""
            try:
                # 获取所有 DUT 编号
                dut_ids = get_all_dut_ids()
                dut_options = ["全部"] + dut_ids
                dut_select.options = dut_options

                # 获取所有批次编号
                batch_ids = get_all_batch_ids()
                batch_options = ["全部"] + batch_ids
                batch_select.options = batch_options

                # 更新绑定值
                dut_select.update()
                batch_select.update()

                ui.notify('筛选选项已更新', type='positive')
            except Exception as e:
                ui.notify(f'更新筛选选项失败: {str(e)}', type='negative')

        # 同步下拉框选择到响应式变量
        def sync_dut_selection():
            selected_dut.value = dut_select.value

        def sync_batch_selection():
            selected_batch.value = batch_select.value

        dut_select.on('update:model-value', sync_dut_selection)
        batch_select.on('update:model-value', sync_batch_selection)

        # 操作按钮行
        with ui.row().classes('gap-2 mb-4'):
            ui.button('刷新数据', on_click=load_data, icon='refresh', color='primary')
            ui.button('导出TXT', on_click=export_to_txt, icon='download', color='green')
            ui.button('清空数据', on_click=confirm_clear_data, icon='delete', color='red')

        # 数据表格
        table = rxui.table(
            columns=columns,
            rows=table_data,
            row_key='id',
            pagination={'rowsPerPage': 20, 'sortBy': 'dut_id', 'descending': False}
        ).classes('w-full')

        # 页面加载时自动刷新筛选选项和数据
        ui.timer(0.1, update_filter_options, once=True)
        ui.timer(0.2, load_data, once=True)

    return container
