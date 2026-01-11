"""
IQ Dump 文件解析和重绘工具
支持读取存储的IQ数据文件并重新绘制频谱图和时域图
"""
import os
from logic.iq_analyzer import analyze_iq_signal
from pages.layout import log

def parse_iq_file(file_path: str, fs: float = 24e6, vpp: float = 1.1, nbit: int = 12,
                  sg_pwr: float = -70, dump_noise: int = 0, chn: int = None, ble_mode: str = None):
    """
    解析IQ dump文件并生成频谱和时域图表

    参数:
        file_path: IQ数据文件路径
        fs: 采样率 (Hz)
        vpp: ADC参考电压峰峰值 (V)
        nbit: ADC位数
        sg_pwr: 信号源功率 (dBm)
        dump_noise: 是否为噪声模式 (0=tone, 1=noise)
        chn: 信道号
        ble_mode: BLE制式

    返回:
        包含time_chart和freq_chart的字典,如果失败返回None
    """
    try:
        if not os.path.exists(file_path):
            log(f"文件不存在: {file_path}", color="red")
            return None

        log(f"正在读取文件: {file_path}", color="blue")

        # 读取文件内容
        with open(file_path, 'r') as f:
            lines = f.readlines()

        log(f"文件共有 {len(lines)} 行", color="blue")

        # 解析每行的十六进制数据
        # 数据格式: Gain(2字节) + Q(3字节) + I(3字节)
        # 注意: iqdump.py中使用 [g + i + q for g, i, q in zip(gain, Qdata, Idata)]
        # 所以实际存储顺序是 Gain + Q + I
        Idata = []
        Qdata = []
        error_count = 0

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:  # 跳过空行
                continue

            if len(line) < 8:  # 至少需要8个字符
                error_count += 1
                if error_count <= 5:  # 只显示前5个错误
                    log(f"第{line_num}行长度不足: '{line}' (长度={len(line)})", color="yellow")
                continue

            try:
                # 解析十六进制数据
                # Gain: 前2个字符 (字符0-1, 不使用)
                # Q: 中间3个字符 (字符2-4)
                # I: 最后3个字符 (字符5-7)

                q_hex = line[2:5]
                i_hex = line[5:8]

                # 转换为有符号整数
                i_val = int(i_hex, 16)
                q_val = int(q_hex, 16)

                # 处理有符号数 (12位ADC)
                if i_val >= 2**(nbit-1):
                    i_val -= 2**nbit
                if q_val >= 2**(nbit-1):
                    q_val -= 2**nbit

                Idata.append(i_val)
                Qdata.append(q_val)

            except (ValueError, IndexError) as e:
                error_count += 1
                if error_count <= 5:  # 只显示前5个错误
                    log(f"第{line_num}行解析失败: '{line}', 错误: {e}", color="yellow")
                continue

        if error_count > 5:
            log(f"共有 {error_count} 行解析失败", color="yellow")

        if len(Idata) == 0 or len(Qdata) == 0:
            log("未能从文件中解析出有效的IQ数据", color="red")
            return None

        log(f"成功解析 {len(Idata)} 个IQ数据点", color="green")

        # 检查数据点数量是否足够进行FFT分析
        if len(Idata) < 512:
            log(f"警告: 数据点数量({len(Idata)})可能不足以进行准确的频谱分析 (建议至少512点)", color="yellow")

        # 使用analyze_iq_signal进行分析和绘图
        result = analyze_iq_signal(
            Idata=Idata,
            Qdata=Qdata,
            fs=fs,
            vpp=vpp,
            nbit=nbit,
            sg_pwr=sg_pwr,
            dump_noise=dump_noise,
            figure_off=0,  # 生成图表
            target_tone_freq=1e6,
            chn=chn,
            ble_mode=ble_mode
        )

        return result

    except Exception as e:
        log(f"解析IQ文件时发生错误: {str(e)}", color="red")
        return None


def list_iq_files(directory: str):
    """
    列出指定目录下的所有IQ dump文件

    参数:
        directory: 要搜索的目录路径

    返回:
        IQ文件路径列表
    """
    try:
        if not os.path.exists(directory):
            return []

        iq_files = []
        for file in os.listdir(directory):
            if file.endswith('.txt') and 'iqdata' in file.lower():
                iq_files.append(os.path.join(directory, file))

        return sorted(iq_files, reverse=True)  # 按时间倒序

    except Exception as e:
        log(f"列出IQ文件时发生错误: {str(e)}", color="red")
        return []
