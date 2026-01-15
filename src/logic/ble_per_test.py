"""
BLE PER (Packet Error Rate) 测试逻辑模块
支持 N5182B 信号源和串口通信
参考 ECW6700_BLE_PER.ipynb 实现
"""
import pyvisa
import serial
import serial.tools.list_ports
import time
import re
from pages.layout import log


class PerTestError(Exception):
    """PER 测试相关错误"""
    pass


def list_serial_ports():
    """列出可用的串口"""
    try:
        ports = serial.tools.list_ports.comports()
        return [f"{port.device} - {port.description}" for port in ports]
    except Exception as e:
        log(f"列出串口失败: {e}", color="red")
        return []


def u2s_fixed(val, n_int, n_frac):
    """
    Qm.n 格式
    无符号整数 -> 有符号定点数
    n_int  : 整数位数 (包含1位符号位)
    n_frac : 小数位数
    """
    total_bits = n_int + n_frac
    max_val = 1 << total_bits  # 2^(n_int+n_frac)

    # 如果最高位（符号位）为1，表示负数
    if val & (1 << (total_bits - 1)):
        val -= max_val

    # 转换成浮点（定点缩放）
    return val / (1 << n_frac)


def per_test(
    chip_model: str,
    com_port: str,
    baudrate: int,
    channel: int,
    start_power: float,
    stop_power: float,
    power_step: float,
    num_packets: int,
    cable_loss: float,
    ip_str: str = '169.254.252.37',
    ble_mode: int = 0,  # 0:1M, 1:2M, 2:LR500K(S2), 3:LR125K(S8)
    stop_flag=None,
    result_callback=None
):
    """
    BLE PER 测试

    参数:
        chip_model: 芯片型号 (ECR2560 或 ECW6700)
        com_port: 串口号
        baudrate: 波特率
        channel: RF信道 (0-39)
        start_power: 起始功率 (dBm)
        stop_power: 截止功率 (dBm)
        power_step: 功率步进 (dB)
        num_packets: 发包数
        cable_loss: 线损 (dB)
        ip_str: N5182B IP地址
        ble_mode: BLE模式 (0:1M, 1:2M, 2:LR500K, 3:LR125K)
        stop_flag: 停止标志，callable返回True时停止测试
        result_callback: 结果回调函数 (power, tx_count, rx_count, per, rssi, agc_index)

    返回:
        测试结果列表 [(power, tx_count, rx_count, per, rssi, agc_index), ...]
    """

    # BLE 模式映射
    ble_mode_names = {
        0: '1M',
        1: '2M',
        2: 'LR500K',
        3: 'LR125K'
    }

    # 波形文件映射
    waveforms = {
        0: 'WFM1:LE1M_PN9',
        1: 'WFM1:LE2M_PN9',
        2: 'WFM1:LES2_PN9',
        3: 'WFM1:LES8_PN9'
    }

    # 信号播放时间（秒）
    signal_play_time = {
        0: 1.0,    # 1M: 1500pkt = 932ms
        1: 1.0,    # 2M: 1500pkt = 932ms
        2: 2.9,    # S2: 2.8s
        3: 5.7     # S8: 5.7s
    }

    # 生成功率列表
    power_list = []
    if start_power > stop_power:
        step = -abs(power_step)
    else:
        step = abs(power_step)

    current = start_power
    if step > 0:
        while current <= stop_power:
            power_list.append(current)
            current += step
    else:
        while current >= stop_power:
            power_list.append(current)
            current += step

    total = len(power_list)
    results = []

    # 连接 N5182B 信号源
    try:
        rm = pyvisa.ResourceManager()
        N5182B = rm.open_resource(f'TCPIP0::{ip_str}::INSTR')
        log(f"成功连接信号源: {ip_str}", color="green")
    except pyvisa.VisaIOError as e:
        log(f"连接信号源失败: {e}", color="red")
        raise PerTestError(f"连接信号源失败: {e}")

    # 连接串口
    SerialPort = None
    try:
        SerialPort = serial.Serial(
            port=com_port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        # 禁用DTR/RTS自动控制，防止触发芯片复位
        SerialPort.dtr = False
        SerialPort.rts = False
        log(f"串口 {com_port} 已连接", color="green")

        # 等待串口稳定
        time.sleep(0.2)

        # 清空可能的残留数据
        SerialPort.reset_input_buffer()
        SerialPort.reset_output_buffer()

        # 关闭回显
        send_serial_command(SerialPort, 'echoclose 0\r\n')

    except Exception as e:
        N5182B.close()
        rm.close()
        se_str = str(e)
        if "PermissionError" in se_str or "Access is denied" in se_str:
            msg = f"{com_port} 被占用"
        elif "FileNotFoundError" in se_str:
            msg = f"未发现 {com_port}"
        else:
            msg = f"串口错误: {e}"
        raise PerTestError(msg)

    try:
        # 初始化 N5182B - 加载 BLE 波形
        log("加载 BLE 波形文件...", color="blue")

        # 清空错误队列
        N5182B.write('*CLS')
        while True:
            err = N5182B.query(':SYSTem:ERRor?')
            if '+0' in err or 'No error' in err:
                break

        def load_waveform(N5182B, wfm_name):
            """加载波形文件，如果失败则尝试带.WFM后缀，返回实际成功的波形名称"""
            # 清空错误队列
            N5182B.write('*CLS')
            # 先尝试不带后缀
            cmd = f':MEMory:COPY:NAME "NVWFM:{wfm_name}","WFM1:{wfm_name}"'
            N5182B.write(cmd)
            N5182B.query('*OPC?')  # 等待操作完成
            # 查询错误状态
            err = N5182B.query(':SYSTem:ERRor?')
            if '+0' not in err and 'No error' not in err:
                # 有错误，清空队列后尝试带.WFM后缀
                N5182B.write('*CLS')
                log(f"波形 {wfm_name} 加载失败，尝试带.WFM后缀...", color="yellow")
                cmd_wfm = f':MEMory:COPY:NAME "NVWFM:{wfm_name}.WFM","WFM1:{wfm_name}.WFM"'
                N5182B.write(cmd_wfm)
                N5182B.query('*OPC?')  # 等待操作完成
                err2 = N5182B.query(':SYSTem:ERRor?')
                if '+0' not in err2 and 'No error' not in err2:
                    log(f"波形 {wfm_name} 加载失败: {err2}", color="red")
                    return f'WFM1:{wfm_name}'  # 返回原始名称（虽然失败）
                else:
                    log(f"波形 {wfm_name}.WFM 加载成功", color="green")
                    return f'WFM1:{wfm_name}.WFM'  # 返回带后缀的名称
            else:
                log(f"波形 {wfm_name} 加载成功", color="green")
                return f'WFM1:{wfm_name}'  # 返回不带后缀的名称

        # 加载波形并更新waveforms字典中的实际名称
        waveforms[0] = load_waveform(N5182B, 'LE1M_PN9')
        waveforms[1] = load_waveform(N5182B, 'LE2M_PN9')
        waveforms[2] = load_waveform(N5182B, 'LES2_PN9')
        waveforms[3] = load_waveform(N5182B, 'LES8_PN9')

        # 设置触发方式为单次触发且重复发送指定次数
        N5182B.write(':RADio:ARB:TRIGger:TYPE SINGle')
        N5182B.write(f':RADio:ARB:TRIGger:TYPE:SINGle:REPeat {num_packets}')

        # 设置单次触发模式类型为No Retrigger
        N5182B.write(':RADio:ARB:RETRigger IMM')

        # 设置触发源为BUS
        N5182B.write(':RADio:ARB:TRIGger:SOURce BUS')

        # 选择波形
        N5182B.write(f':SOURce:RADio:ARB:WAVeform "{waveforms[ble_mode]}"')

        # 使能ARB
        N5182B.write(':SOURce:RADio:ARB:STATe ON')

        # 使能Mod
        N5182B.write(':OUTPut:MODulation:STATe ON')

        log(f"N5182B 初始化完成，模式: {ble_mode_names[ble_mode]}", color="green")

        # 设置频率（信道转频率）
        # ECW6700 信道从1开始，协议信道0对应ECW6700的1
        ecw6700_channel = channel + 1
        freq_mhz = 2400 + ecw6700_channel * 2
        N5182B.write(f':FREQuency:FIXed {freq_mhz} MHz')
        log(f"信号源频率: {freq_mhz} MHz (信道 {channel})", color="blue")

        # 获取延迟时间
        delay_time = signal_play_time.get(ble_mode, 1.0)

        # 预热测试（第一次测试结果通常不准确，丢弃）
        log("执行预热测试...", color="blue")
        warmup_power = start_power
        N5182B.write(f':POWer:LEVel {warmup_power + cable_loss} dBm')
        send_serial_command(SerialPort, f'amtBleRxStart {ble_mode} {ecw6700_channel}\r\n')
        time.sleep(0.1)
        N5182B.write(':OUTPut:STATe ON')
        N5182B.write('*TRG')
        time.sleep(delay_time + 0.2)
        send_serial_command(SerialPort, 'amtBleRxStop\r\n')
        N5182B.write(':OUTPut:STATe OFF')
        time.sleep(0.1)
        log("预热完成", color="green")

        # 遍历功率点进行测试
        for idx, power in enumerate(power_list):
            # 检查停止标志
            if stop_flag and callable(stop_flag) and stop_flag():
                log("用户请求停止测试", color="yellow")
                break

            log(f"[{idx+1}/{total}] 测试功率: {power:.1f} dBm")

            # 设置信号源功率（补偿线损）
            N5182B.write(f':POWer:LEVel {power + cable_loss} dBm')

            # 启动 DUT 接收
            send_serial_command(SerialPort, f'amtBleRxStart {ble_mode} {ecw6700_channel}\r\n')
            time.sleep(0.1)

            # 打开RF输出
            N5182B.write(':OUTPut:STATe ON')

            # 触发信号发生器
            N5182B.write('*TRG')
            time.sleep(0.2)

            # 读取同步后的RSSI（从寄存器0x20470c40读取）
            rssi = None
            agc_index = None
            try:
                rssi_reg_value = read_reg(SerialPort, 0x20470c40, 4)
                if rssi_reg_value is not None:
                    # 提取 RSSI (bit29:16)
                    rssi_value_sync_ok = rssi_reg_value >> 16
                    rssi = u2s_fixed(rssi_value_sync_ok, 12, 2)

                    # 提取 AGC index (bit2:0)
                    agc_index = rssi_reg_value & 0x07
            except Exception as e:
                log(f"  读取RSSI/AGC失败: {e}", color="yellow")

            # 等待发包完成
            time.sleep(delay_time)

            # 停止接收
            send_serial_command(SerialPort, 'amtBleRxStop\r\n')

            # 关闭RF输出
            N5182B.write(':OUTPut:STATe OFF')

            # 读取接收包数（从寄存器0x204600d8读取）
            rx_count = -1
            try:
                rx_count = read_reg(SerialPort, 0x204600d8, 4)
                if rx_count is None:
                    rx_count = -1
            except Exception as e:
                log(f"  读取收包数失败: {e}", color="yellow")

            if rx_count < 0:
                log(f"  获取收包数失败", color="red")
                per = -1
            else:
                per = (num_packets - rx_count) / num_packets * 100
                if rssi is not None and agc_index is not None:
                    log(f"  结果: TX={num_packets}, RX={rx_count}, PER={per:.2f}%, RSSI={rssi:.2f}dBm, AGC={agc_index}", color="green")
                elif rssi is not None:
                    log(f"  结果: TX={num_packets}, RX={rx_count}, PER={per:.2f}%, RSSI={rssi:.2f}dBm", color="green")
                else:
                    log(f"  结果: TX={num_packets}, RX={rx_count}, PER={per:.2f}%", color="green")

            results.append((power, num_packets, rx_count, per, rssi, agc_index))

            # 调用结果回调
            if result_callback:
                try:
                    result_callback(power, num_packets, rx_count, per, rssi, agc_index)
                except Exception as e:
                    log(f"更新结果表格失败: {e}", color="yellow")

    finally:
        # 清理资源
        if SerialPort and SerialPort.is_open:
            SerialPort.close()
            log("串口已关闭", color="green")
        N5182B.close()
        rm.close()
        log("测试完成，资源已释放", color="green")

    return results


def send_serial_command(serial_port, cmd):
    """发送串口命令"""
    if not serial_port:
        return ""

    # 清空接收缓冲区
    serial_port.reset_input_buffer()

    # 发送命令
    serial_port.write(cmd.encode())
    serial_port.flush()

    # 等待响应
    time.sleep(0.3)

    # 读取响应
    response = ""
    max_retries = 10
    for _ in range(max_retries):
        if serial_port.in_waiting > 0:
            data = serial_port.read(serial_port.in_waiting)
            response += data.decode('utf-8', errors='ignore')
            time.sleep(0.05)
        else:
            if response:
                break
            time.sleep(0.05)

    return response


def read_reg(serial_port, addr, length):
    """
    读取寄存器值

    参数:
        serial_port: 串口对象
        addr: 寄存器地址
        length: 读取长度（字节）

    返回:
        寄存器值（整数），失败返回None
    """
    cmd = f'read 0x{addr:08x} {length}\r\n'
    response = send_serial_command(serial_port, cmd)

    if not response or "OK" not in response:
        return None

    try:
        # 解析响应格式: "地址: 值"
        # 例如: "20470c40: 12345678"
        pattern = f'{addr:08x}:\\s*([0-9a-fA-F]+)'
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return int(match.group(1), 16)
        return None
    except Exception as e:
        log(f"解析寄存器值失败: {e}", color="yellow")
        return None


def sensitivity_scan(
    chip_model: str,
    com_port: str,
    baudrate: int,
    channels: list,
    start_power: float,
    stop_power: float,
    power_step: float,
    num_packets: int,
    cable_loss: float,
    per_threshold: float = 30.8,
    ip_str: str = '169.254.252.37',
    ble_mode: int = 0,
    stop_flag=None,
    progress_callback=None,
    result_callback=None
):
    """
    灵敏度扫描 - 遍历所有信道，测试每个信道的灵敏度上限

    参数:
        chip_model: 芯片型号
        com_port: 串口号
        baudrate: 波特率
        channels: 信道列表 (0-39)
        start_power: 起始功率 (dBm)
        stop_power: 截止功率 (dBm)
        power_step: 功率步进 (dB)
        num_packets: 发包数
        cable_loss: 线损 (dB)
        per_threshold: PER 阈值 (%)，默认 30.8%
        ip_str: N5182B IP地址
        ble_mode: BLE模式
        stop_flag: 停止标志
        progress_callback: 进度回调 (current, total, channel, power, per)
        result_callback: 结果回调 (channel, sensitivity, rssi)

    返回:
        灵敏度结果列表 [(channel, sensitivity, rssi), ...]
    """
    ble_mode_names = {0: '1M', 1: '2M', 2: 'LR500K', 3: 'LR125K'}
    waveforms = {
        0: 'WFM1:LE1M_PN9',
        1: 'WFM1:LE2M_PN9',
        2: 'WFM1:LES2_PN9',
        3: 'WFM1:LES8_PN9'
    }
    signal_play_time = {0: 1.0, 1: 1.0, 2: 2.9, 3: 5.7}

    # 生成功率列表（从高功率到低功率）
    power_list = []
    step = -abs(power_step)
    current = start_power
    while current >= stop_power:
        power_list.append(current)
        current += step

    total_channels = len(channels)
    total_points = total_channels * len(power_list)
    results = []

    # 连接 N5182B
    try:
        rm = pyvisa.ResourceManager()
        N5182B = rm.open_resource(f'TCPIP0::{ip_str}::INSTR')
        log(f"成功连接信号源: {ip_str}", color="green")
    except pyvisa.VisaIOError as e:
        raise PerTestError(f"连接信号源失败: {e}")

    # 连接串口
    SerialPort = None
    try:
        SerialPort = serial.Serial(
            port=com_port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        SerialPort.dtr = False
        SerialPort.rts = False
        log(f"串口 {com_port} 已连接", color="green")
        time.sleep(0.2)
        SerialPort.reset_input_buffer()
        SerialPort.reset_output_buffer()
        send_serial_command(SerialPort, 'echoclose 0\r\n')
    except Exception as e:
        N5182B.close()
        rm.close()
        se_str = str(e)
        if "PermissionError" in se_str or "Access is denied" in se_str:
            msg = f"{com_port} 被占用"
        elif "FileNotFoundError" in se_str:
            msg = f"未发现 {com_port}"
        else:
            msg = f"串口错误: {e}"
        raise PerTestError(msg)

    try:
        # 初始化信号源
        log("加载 BLE 波形文件...", color="blue")
        N5182B.write('*CLS')
        while True:
            err = N5182B.query(':SYSTem:ERRor?')
            if '+0' in err or 'No error' in err:
                break

        def load_waveform(N5182B, wfm_name):
            N5182B.write('*CLS')
            cmd = f':MEMory:COPY:NAME "NVWFM:{wfm_name}","WFM1:{wfm_name}"'
            N5182B.write(cmd)
            N5182B.query('*OPC?')
            err = N5182B.query(':SYSTem:ERRor?')
            if '+0' not in err and 'No error' not in err:
                N5182B.write('*CLS')
                cmd_wfm = f':MEMory:COPY:NAME "NVWFM:{wfm_name}.WFM","WFM1:{wfm_name}.WFM"'
                N5182B.write(cmd_wfm)
                N5182B.query('*OPC?')
                err2 = N5182B.query(':SYSTem:ERRor?')
                if '+0' not in err2 and 'No error' not in err2:
                    return f'WFM1:{wfm_name}'
                else:
                    return f'WFM1:{wfm_name}.WFM'
            else:
                return f'WFM1:{wfm_name}'

        waveforms[0] = load_waveform(N5182B, 'LE1M_PN9')
        waveforms[1] = load_waveform(N5182B, 'LE2M_PN9')
        waveforms[2] = load_waveform(N5182B, 'LES2_PN9')
        waveforms[3] = load_waveform(N5182B, 'LES8_PN9')

        N5182B.write(':RADio:ARB:TRIGger:TYPE SINGle')
        N5182B.write(f':RADio:ARB:TRIGger:TYPE:SINGle:REPeat {num_packets}')
        N5182B.write(':RADio:ARB:RETRigger IMM')
        N5182B.write(':RADio:ARB:TRIGger:SOURce BUS')
        N5182B.write(f':SOURce:RADio:ARB:WAVeform "{waveforms[ble_mode]}"')
        N5182B.write(':SOURce:RADio:ARB:STATe ON')
        N5182B.write(':OUTPut:MODulation:STATe ON')
        log(f"N5182B 初始化完成，模式: {ble_mode_names[ble_mode]}", color="green")

        delay_time = signal_play_time.get(ble_mode, 1.0)
        current_point = 0

        # 遍历所有信道
        for ch_idx, channel in enumerate(channels):
            if stop_flag and callable(stop_flag) and stop_flag():
                log("用户请求停止测试", color="yellow")
                break

            ecw6700_channel = channel + 1
            freq_mhz = 2400 + ecw6700_channel * 2
            N5182B.write(f':FREQuency:FIXed {freq_mhz} MHz')
            log(f"[信道 {channel}] 频率: {freq_mhz} MHz", color="blue")

            # 预热
            warmup_power = start_power
            N5182B.write(f':POWer:LEVel {warmup_power + cable_loss} dBm')
            send_serial_command(SerialPort, f'amtBleRxStart {ble_mode} {ecw6700_channel}\r\n')
            time.sleep(0.1)
            N5182B.write(':OUTPut:STATe ON')
            N5182B.write('*TRG')
            time.sleep(delay_time + 0.2)
            send_serial_command(SerialPort, 'amtBleRxStop\r\n')
            N5182B.write(':OUTPut:STATe OFF')
            time.sleep(0.1)

            sensitivity = None
            sensitivity_rssi = None

            # 从高功率到低功率扫描，找到PER刚超过阈值的点
            for power in power_list:
                if stop_flag and callable(stop_flag) and stop_flag():
                    break

                current_point += 1
                N5182B.write(f':POWer:LEVel {power + cable_loss} dBm')
                send_serial_command(SerialPort, f'amtBleRxStart {ble_mode} {ecw6700_channel}\r\n')
                time.sleep(0.1)
                N5182B.write(':OUTPut:STATe ON')
                N5182B.write('*TRG')
                time.sleep(0.2)

                # 读取 RSSI
                rssi = None
                try:
                    rssi_reg_value = read_reg(SerialPort, 0x20470c40, 4)
                    if rssi_reg_value is not None:
                        rssi_value_sync_ok = rssi_reg_value >> 16
                        rssi = u2s_fixed(rssi_value_sync_ok, 12, 2)
                except:
                    pass

                time.sleep(delay_time)
                send_serial_command(SerialPort, 'amtBleRxStop\r\n')
                N5182B.write(':OUTPut:STATe OFF')

                # 读取收包数
                rx_count = -1
                try:
                    rx_count = read_reg(SerialPort, 0x204600d8, 4)
                    if rx_count is None:
                        rx_count = -1
                except:
                    pass

                if rx_count < 0:
                    per = 100.0
                else:
                    per = (num_packets - rx_count) / num_packets * 100

                log(f"  功率: {power:.1f} dBm, PER: {per:.2f}%", color="green" if per <= per_threshold else "yellow")

                # 更新进度
                if progress_callback:
                    try:
                        progress_callback(current_point, total_points, channel, power, per)
                    except:
                        pass

                # 检查是否找到灵敏度点
                if per > per_threshold:
                    # 上一个功率点是灵敏度上限
                    sensitivity = power + abs(power_step)
                    sensitivity_rssi = rssi
                    log(f"  信道 {channel} 灵敏度: {sensitivity:.1f} dBm (PER @ {power:.1f}dBm = {per:.2f}%)", color="green")
                    break

            # 如果扫描完所有功率点都没有超过阈值，则灵敏度为最低功率
            if sensitivity is None:
                sensitivity = stop_power
                sensitivity_rssi = rssi
                log(f"  信道 {channel} 灵敏度 < {stop_power:.1f} dBm", color="green")

            results.append((channel, sensitivity, sensitivity_rssi))

            # 结果回调
            if result_callback:
                try:
                    result_callback(channel, sensitivity, sensitivity_rssi)
                except:
                    pass

    finally:
        if SerialPort and SerialPort.is_open:
            SerialPort.close()
            log("串口已关闭", color="green")
        N5182B.close()
        rm.close()
        log("灵敏度扫描完成，资源已释放", color="green")

    return results
