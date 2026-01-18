"""
寄存器对比业务逻辑模块
"""
import yaml
import serial
import serial.tools.list_ports
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Tuple, Any
from pathlib import Path


class RegCompareError(Exception):
    """寄存器对比相关错误"""
    pass


@dataclass
class RegisterInfo:
    """寄存器信息"""
    address: int
    name: str
    size: int = 4
    group: str = ""
    description: str = ""


@dataclass
class CompareResult:
    """对比结果"""
    address: int
    name: str
    group: str
    values: Dict[int, Optional[int]]  # {device_index: value}
    has_difference: bool


def list_serial_ports() -> List[str]:
    """列出可用的串口"""
    try:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    except Exception:
        return []


def load_register_config(yaml_path: str) -> Tuple[str, List[RegisterInfo]]:
    """
    加载寄存器配置文件

    Args:
        yaml_path: YAML配置文件路径

    Returns:
        (chip_model, register_list)
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    chip_model = config.get('chip_model', 'Unknown')
    registers = []

    for group in config.get('register_groups', []):
        group_name = group['name']
        base_addr = group['base_address']
        # 获取排除的偏移地址列表
        exclude_offsets = set(group.get('exclude_offsets', []))

        # 方式1: 显式定义的寄存器列表
        if 'registers' in group:
            for reg in group['registers']:
                offset = reg['offset']
                if offset in exclude_offsets:
                    continue  # 跳过排除的寄存器
                registers.append(RegisterInfo(
                    address=base_addr + offset,
                    name=reg.get('name', f"REG_0x{base_addr + offset:08X}"),
                    size=reg.get('size', 4),
                    group=group_name,
                    description=reg.get('description', '')
                ))

        # 方式2: 范围定义
        if 'range' in group:
            r = group['range']
            for offset in range(r['start'], r['end'] + 1, r.get('step', 4)):
                if offset in exclude_offsets:
                    continue  # 跳过排除的寄存器
                addr = base_addr + offset
                registers.append(RegisterInfo(
                    address=addr,
                    name=f"{group_name}_0x{offset:02X}",
                    size=r.get('size', 4),
                    group=group_name
                ))

    return chip_model, registers


def get_register_groups(yaml_path: str) -> List[Dict[str, Any]]:
    """获取配置文件中的寄存器组列表"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    groups = []
    for group in config.get('register_groups', []):
        # 获取排除的偏移地址列表
        exclude_offsets = set(group.get('exclude_offsets', []))

        # 计算寄存器数量（排除后的）
        count = 0
        if 'registers' in group:
            for reg in group['registers']:
                if reg['offset'] not in exclude_offsets:
                    count += 1
        if 'range' in group:
            r = group['range']
            for offset in range(r['start'], r['end'] + 1, r.get('step', 4)):
                if offset not in exclude_offsets:
                    count += 1

        groups.append({
            'name': group['name'],
            'description': group.get('description', ''),
            'base_address': group['base_address'],
            'count': count
        })
    return groups


class DeviceReader:
    """单设备寄存器读取器"""

    def __init__(self, port_name: str, baudrate: int = 115200):
        self.port_name = port_name
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None

    def connect(self):
        """建立串口连接"""
        self.serial = serial.Serial(self.port_name, self.baudrate, timeout=1)
        time.sleep(0.1)  # 等待连接稳定

        # 关闭回显，避免时间戳等信息干扰解析
        self.serial.reset_input_buffer()
        self.serial.write(b"echoclose 0\r\n")
        time.sleep(0.05)
        self.serial.reset_input_buffer()  # 清除响应

    def disconnect(self):
        """断开连接"""
        if self.serial and self.serial.is_open:
            self.serial.close()

    def read_register(self, address: int, size: int = 4) -> Optional[int]:
        """
        读取单个寄存器

        Args:
            address: 寄存器地址
            size: 读取字节数

        Returns:
            寄存器值，读取失败返回 None
        """
        if not self.serial or not self.serial.is_open:
            return None

        try:
            # 清空缓冲区
            self.serial.reset_input_buffer()

            # 发送读取命令: read 0x{addr:08x} {size}
            cmd = f"read 0x{address:08x} {size}\r\n"
            self.serial.write(cmd.encode())
            time.sleep(0.02)

            # 读取响应
            response = self.serial.readline()

            # 解析响应格式: {addr}: {value}
            # 示例: 0x2020d400: 0x12345678
            if b':' in response:
                parts = response.decode(errors='ignore').split(':')
                if len(parts) >= 2:
                    value_str = parts[1].strip().split()[0]  # 取第一个值
                    if value_str.startswith('0x') or value_str.startswith('0X'):
                        return int(value_str, 16)
                    else:
                        return int(value_str)

            return None

        except Exception:
            return None

    def read_register_block(self, address: int, byte_count: int) -> Optional[Dict[int, int]]:
        """
        批量读取寄存器块

        Args:
            address: 起始地址
            byte_count: 读取字节数

        Returns:
            {地址: 值} 字典，失败返回 None
        """
        if not self.serial or not self.serial.is_open:
            return None

        try:
            self.serial.reset_input_buffer()

            # 发送批量读取命令
            cmd = f"read 0x{address:08x} {byte_count}\r\n"
            self.serial.write(cmd.encode())

            # 等待响应（批量读取需要更长时间）
            time.sleep(0.1 + byte_count * 0.001)

            # 读取所有响应行
            results = {}
            expected_regs = byte_count // 4
            max_wait = 50  # 最多等待次数

            for _ in range(max_wait):
                while self.serial.in_waiting > 0:
                    line = self.serial.readline()
                    line_str = line.decode(errors='ignore').strip()

                    # 跳过 OK 或空行
                    if not line_str or line_str == 'OK':
                        continue

                    if ':' in line_str:
                        try:
                            parts = line_str.split(':')
                            if len(parts) >= 2:
                                addr_str = parts[0].strip()
                                value_str = parts[1].strip().split()[0]

                                # 解析地址（可能有或没有 0x 前缀）
                                if addr_str.startswith('0x') or addr_str.startswith('0X'):
                                    addr = int(addr_str, 16)
                                else:
                                    addr = int(addr_str, 16)  # 默认按16进制解析

                                # 解析值
                                if value_str.startswith('0x') or value_str.startswith('0X'):
                                    value = int(value_str, 16)
                                else:
                                    value = int(value_str, 16)  # 默认按16进制解析

                                results[addr] = value
                        except:
                            pass

                if len(results) >= expected_regs:
                    break
                time.sleep(0.02)

            return results if results else None

        except Exception:
            return None


def compare_registers(
    device_ports: List[str],
    baudrate: int,
    registers: List[RegisterInfo],
    stop_flag: Callable[[], bool] = None,
    progress_callback: Callable[[int, int, str], None] = None,
    result_callback: Callable[[CompareResult], None] = None,
    log_func: Callable[[str], None] = None
) -> List[CompareResult]:
    """
    多设备寄存器对比（批量读取 + 多设备并行）

    Args:
        device_ports: 设备串口列表
        baudrate: 波特率
        registers: 要读取的寄存器列表
        stop_flag: 停止标志函数
        progress_callback: 进度回调 (current, total, message)
        result_callback: 单条结果回调
        log_func: 日志函数

    Returns:
        对比结果列表（仅包含有差异的寄存器）
    """
    results = []
    total = len(registers)

    def _log(msg):
        if log_func:
            log_func(msg)

    # 按组分组寄存器，计算每组的起始地址和字节数
    groups = {}
    for reg in registers:
        if reg.group not in groups:
            groups[reg.group] = []
        groups[reg.group].append(reg)

    # 计算每个组的读取参数
    group_params = []
    for group_name, group_regs in groups.items():
        addresses = [r.address for r in group_regs]
        start_addr = min(addresses)
        end_addr = max(addresses)
        byte_count = end_addr - start_addr + 4  # +4 是因为最后一个寄存器也要读取
        group_params.append({
            'name': group_name,
            'start_addr': start_addr,
            'byte_count': byte_count,
            'registers': group_regs
        })

    # 创建设备读取器
    readers = []
    for i, port in enumerate(device_ports):
        reader = DeviceReader(port, baudrate)
        try:
            reader.connect()
            readers.append(reader)
            _log(f"设备{i+1} ({port}) 连接成功")
        except Exception as e:
            _log(f"设备{i+1} ({port}) 连接失败: {e}")
            for r in readers:
                r.disconnect()
            raise RegCompareError(f"设备{i+1}连接失败: {e}")

    try:
        processed = 0
        for gp in group_params:
            if stop_flag and stop_flag():
                _log("用户停止对比")
                break

            group_name = gp['name']
            start_addr = gp['start_addr']
            byte_count = gp['byte_count']
            group_regs = gp['registers']

            _log(f"读取 {group_name}: 0x{start_addr:08X}, {byte_count} 字节")

            if progress_callback:
                progress_callback(processed, total, f"正在读取 {group_name}")

            # 多设备并行读取
            device_data = {}

            def read_device(device_idx, reader):
                return device_idx, reader.read_register_block(start_addr, byte_count)

            with ThreadPoolExecutor(max_workers=len(readers)) as executor:
                futures = [executor.submit(read_device, i, r) for i, r in enumerate(readers)]
                for future in as_completed(futures):
                    idx, data = future.result()
                    device_data[idx] = data or {}
                    reg_count = len(data) if data else 0
                    _log(f"设备{idx+1} 读取完成，获取 {reg_count} 个寄存器")

            # 对比每个寄存器
            for reg in group_regs:
                values = {}
                for device_idx in range(len(readers)):
                    data = device_data.get(device_idx, {})
                    values[device_idx] = data.get(reg.address)

                # 判断是否有差异
                valid_values = [v for v in values.values() if v is not None]
                has_diff = len(set(valid_values)) > 1 if len(valid_values) > 1 else False

                if has_diff:
                    result = CompareResult(
                        address=reg.address,
                        name=reg.name,
                        group=reg.group,
                        values=values,
                        has_difference=has_diff
                    )
                    results.append(result)
                    if result_callback:
                        result_callback(result)

                processed += 1

            if progress_callback:
                progress_callback(processed, total, f"完成 {group_name}")

    finally:
        for reader in readers:
            reader.disconnect()

    return results
