import pyvisa
from logic import serial_lib
import time
import numpy as np
import re
import serial #必须导入 不然捕获异常出错
import plotly.graph_objects as go
from colorama import Fore, Style
from pages.layout import log
from nicegui import ui
from logic.iq_analyzer import analyze_iq_signal
from db.db_manager import insert_test_data, query_results  # 导入数据库插入函数


def calculate_nf(gain_dB, noise_power_dBm, bandwidth_Hz=1e6, temperature_K=290):
    """
    计算噪声系数（Noise Figure, dB）
    
    参数:
        gain_dB (float): 系统增益（单位 dB）
        noise_power_dBm (float): 测得的输出噪声功率（单位 dBm）
        bandwidth_Hz (float): 噪声测量带宽（单位 Hz），默认 1 MHz
        temperature_K (float): 参考温度，默认 290K（标准室温）
    
    返回:
        NF_dB (float): 噪声系数（单位 dB）
    """
    # 计算热噪声底（dBm）
    k = 1.38e-23  # Boltzmann 常数 (J/K)
    thermal_noise_W = k * temperature_K * bandwidth_Hz
    thermal_noise_dBm = 10 * np.log10(thermal_noise_W) + 30  # W 转 dBm
    
    # 计算 NF
    ideal_output_noise_dBm = thermal_noise_dBm + gain_dB
    NF_dB = noise_power_dBm - ideal_output_noise_dBm
    
    # 显示中间步骤（可选）
    log(f"带宽: {bandwidth_Hz/1e6:.2f} MHz", color="cyan")
    log(f"热噪声底: {thermal_noise_dBm:.2f} dBm", color="cyan")
    log(f"理想输出噪声: {ideal_output_noise_dBm:.2f} dBm", color="cyan")
    log(f"测得输出噪声: {noise_power_dBm:.2f} dBm", color="cyan")
    log(f"噪声系数 NF: {NF_dB:.2f} dB", color="cyan")
    
    return NF_dB


ble_if_offset_map = {
    "LE1M": 1,
    "LE2M": 2,
    "LES2": 1,
    "LES8": 1
}

ble_rate_map = {
   'LE1M' : 0,
   'LE2M' : 1,
   'LES2' : 2,
   'LES8' : 3
}

def hex2sint_list(hex_string_list,bits):
    result_list = []
    
    for hex_string in hex_string_list:
        hex_value = int(hex_string, 16)& (2**bits-1) # 转换为整数

        # 处理负数情况
        if(hex_value > (2**(bits-1)-1)):
            decimal_value = hex_value - 2**bits
        else:
            decimal_value = hex_value

        result_list.append(decimal_value)
    
    return result_list


def iqdump(
        fs:float=24e6,
        SN:int=4096,
        ip_str:str='169.254.252.37',
        tone_freq:float=0.0,
        com_num:int=46,
        buand:int=115200,
        cable_loss:float=0.65,
        AMPTD:float=-70,
        vpp:float=1.1,
        nbit:int=12,
        dump_type:int=0,
        chn_list:list[int]=list(range(40)),
        ble_modes_list:list[str]=list(["LE1M","LE2M","LES2","LES8"]),
        chart_update_callback=None
):
    # log("log INFO .................... start",color="blue")
    log(com_num)
    # log(ip_str)
    # log(chn_list)
    # log(ble_modes_list)
    # log(dump_type)
    # log(cable_loss)
    # log(AMPTD)
    # log("log INFO .................... end",color="red")

    try:
        rm = pyvisa.ResourceManager()
        N5182B = rm.open_resource(f'TCPIP0::{ip_str}::INSTR')
        log("成功连接到设备:", N5182B)
        is_connected = True
    except pyvisa.VisaIOError as e:
        log("连接设备时出现错误:", e)
        # 创建一个模拟对象
        class DummyInstrument:
            def write(self, command):
                log(f"设备未连接，忽略命令: {command}")
                return None, None
            
            def query(self, command):
                log(f"设备未连接，忽略查询: {command}")
                return None
                
            def close(self):
                pass
        N5182B = DummyInstrument()
        is_connected = False
    # 猴子补丁：在未连接时覆盖 write 方法
    if not is_connected:
        original_write = N5182B.write
        
        def safe_write(command):
            try:
                return original_write(command)
            except pyvisa.VisaIOError as e:
                print(f"写入命令时出错 ({command}): {e}")
                return None, None
        
        N5182B.write = safe_write


    try:
        SerialPort = None
        SerialPort = serial_lib.SerialCommunication(com_num,buand)
    except serial.SerialException as se:
        if "PermissionError" in str(se): 
            log(f"COM{com_num}正在被其他程序占用")
            raise SystemExit
        elif "FileNotFoundError" in str(se):
            log(f"未发现COM{com_num}串口")
            raise SystemExit
    except Exception as e:
        log(f"发生未知错误: {e}")
        raise SystemExit
    else:
        log("打开串口")
        SerialPort.write_cmd('echoclose 0')

    N5182B.write(f':POWer:LEVel {AMPTD+cable_loss} dBm')
    if(dump_type == 0):
        #log("dump noise")
        dump_type_str = "noise"
    elif(dump_type == 1):
        #log("dump tone")
        dump_type_str = "tone"
        #N5182B.write(f':FREQuency:FIXed {2400+chn*2+tone_freq} MHz')
        N5182B.write(':SOURce:RADio:ARB:STATe OFF')
        N5182B.write(':OUTPut:MODulation:STATe OFF')
        N5182B.write(':OUTPut:STATe ON')
    elif dump_type == 2:
        dump_type_str = "wave"
        #log("dump BLE wave")
        #N5182B.write(f':FREQuency:FIXed {2400+chn*2} MHz')
        # 设置触发方式为单次触发且重复发送1500次
        N5182B.write(':RADio:ARB:TRIGger:TYPE SINGle')
        N5182B.write(':RADio:ARB:TRIGger:TYPE:SINGle:REPeat 1500')
        # 设置单次触发模式类型为No Retrigger
        N5182B.write(':RADio:ARB:RETRigger IMM')
        N5182B.write(':SOURce:RADio:ARB:STATe ON')
        N5182B.write(':OUTPut:MODulation:STATe ON')
        N5182B.write(':OUTPut:STATe ON')
    elif dump_type == 3:
        dump_type_str = "NF"
        log("开始NF测试：先进行Noise测试，再进行Tone测试")
        # NF测试需要先配置为tone模式的设备设置
        N5182B.write(':SOURce:RADio:ARB:STATe OFF')
        N5182B.write(':OUTPut:MODulation:STATe OFF')
    else:
        log("无效的 dump_type 值")

    
    for ble_mode in ble_modes_list:
        rate_num = ble_rate_map[ble_mode]
        if_offset = ble_if_offset_map[ble_mode]
        for chn in chn_list:
            chn = chn + 1
            N5182B.write(f':FREQuency:FIXed {2400+chn*2+tone_freq} MHz')
            
            # NF测试需要进行两次dump：先noise后tone
            if dump_type == 3:  # NF测试
                log(f"开始NF测试 - 信道{chn}, 制式{ble_mode}")
                
                # ========== 第一步：Noise Dump ==========
                log("第一步：进行Noise测试")
                N5182B.write(':OUTPut:STATe OFF')  # 关闭输出进行noise测试
                
                log(f'amtBleRxStartInf {rate_num} {chn}')
                SerialPort.write_cmd(f'amtBleRxStartInf {rate_num} {chn}')
                N5182B.write('*TRG')
                SerialPort.write_cmd(f'amtbleiqdump 0 0 0x7fff 0x3a98')
                time.sleep(0.1)
                SerialPort.write_reg(0x2020e000,0x0)
                N5182B.write(':OUTPut:STATe OFF')
                SerialPort.write_cmd(f'amtBleRxStop')
                SerialPort.flush_Input()
                SerialPort.write_cmd(f'read 0x20000000 {SN*4}')
                temp = SerialPort.read_all_bytes()
                rxdump_data = temp.decode('UTF-8')
                hex_list = re.findall(r': ([0-9a-fA-F]+)\r\n', rxdump_data)
                gain_noise = [hex_value[0:2] for hex_value in hex_list]
                Idata_noise = [hex_value[2:5] for hex_value in hex_list]
                Qdata_noise = [hex_value[5:8] for hex_value in hex_list]
                Idata_dec_noise = hex2sint_list(Idata_noise, 12)
                Qdata_dec_noise = hex2sint_list(Qdata_noise, 12)
                
                # 分析noise数据
                noise_analysis = analyze_iq_signal(
                    Idata=Idata_dec_noise,
                    Qdata=Qdata_dec_noise,
                    fs=fs, vpp=vpp, nbit=nbit, sg_pwr=AMPTD,
                    dump_noise=1,  # noise模式
                    figure_off=1,  # 不显示图表，只获取数据
                    target_tone_freq=tone_freq*1e6 if tone_freq > 0 else 1e6
                )
                noise_power = noise_analysis.get('noise')
                log(f"Noise功率: {noise_power} dBm", color="blue")
                
                # ========== 第二步：Tone Dump ==========
                log("第二步：进行Tone测试")
                N5182B.write(':OUTPut:STATe ON')  # 打开输出进行tone测试
                
                log(f'amtBleRxStartInf {rate_num} {chn}')
                SerialPort.write_cmd(f'amtBleRxStartInf {rate_num} {chn}')
                N5182B.write('*TRG')
                SerialPort.write_cmd(f'amtbleiqdump 0 0 0x7fff 0x3a98')
                time.sleep(0.1)
                SerialPort.write_reg(0x2020e000,0x0)
                N5182B.write(':OUTPut:STATe OFF')
                SerialPort.write_cmd(f'amtBleRxStop')
                SerialPort.flush_Input()
                SerialPort.write_cmd(f'read 0x20000000 {SN*4}')
                temp = SerialPort.read_all_bytes()
                rxdump_data = temp.decode('UTF-8')
                hex_list = re.findall(r': ([0-9a-fA-F]+)\r\n', rxdump_data)
                gain_tone = [hex_value[0:2] for hex_value in hex_list]
                Idata_tone = [hex_value[2:5] for hex_value in hex_list]
                Qdata_tone = [hex_value[5:8] for hex_value in hex_list]
                Idata_dec_tone = hex2sint_list(Idata_tone, 12)
                Qdata_dec_tone = hex2sint_list(Qdata_tone, 12)
                
                # 分析tone数据
                tone_analysis = analyze_iq_signal(
                    Idata=Idata_dec_tone,
                    Qdata=Qdata_dec_tone,
                    fs=fs, vpp=vpp, nbit=nbit, sg_pwr=AMPTD,
                    dump_noise=0,  # tone模式
                    figure_off=0,  # 显示图表
                    target_tone_freq=tone_freq*1e6 if tone_freq > 0 else 1e6
                )
                
                # 通过回调函数更新UI中的图表（使用tone的图表）
                if chart_update_callback and 'time_chart' in tone_analysis and 'freq_chart' in tone_analysis:
                    try:
                        chart_update_callback(tone_analysis['time_chart'], tone_analysis['freq_chart'])
                        log("图表已更新到UI", color="blue")
                    except Exception as chart_error:
                        log(f"更新图表到UI时出错: {str(chart_error)}", color="red")
                
                signal_power = tone_analysis.get('signal')
                signal_gain = tone_analysis.get('gain')
                log(f"Signal功率: {signal_power} dBm", color="blue")
                log(f"Signal增益: {signal_gain} dB", color="blue")
                
                # ========== 第三步：计算NF ==========
                if noise_power is not None and signal_gain is not None:
                    # 根据BLE制式自动选择带宽
                    if ble_mode == "LE2M":
                        bandwidth_Hz = 2e6  # LE2M使用2MHz带宽
                    else:  # LE1M, LES2, LES8
                        bandwidth_Hz = 1e6  # 其他制式使用1MHz带宽
                    
                    log(f"BLE制式: {ble_mode}, 使用带宽: {bandwidth_Hz/1e6:.0f} MHz", color="green")
                    log("开始计算噪声系数NF:", color="green")
                    nf_value = calculate_nf(
                        gain_dB=signal_gain,
                        noise_power_dBm=noise_power,
                        bandwidth_Hz=bandwidth_Hz,
                        temperature_K=290  # 标准室温
                    )
                    log(f"最终计算得到NF: {nf_value:.2f} dB", color="green")
                else:
                    nf_value = None
                    log("无法计算NF：缺少必要的测量数据", color="red")
                
                # 获取其他分析结果
                dc_val = tone_analysis.get('dc')
                snr_val = tone_analysis.get('snr')
                image_val = tone_analysis.get('image')
                imrr_val = tone_analysis.get('imrr')
                
                # 将结果插入数据库
                insert_test_data(
                    table_name="ble_test_results",
                    chn=chn,
                    rate=ble_mode,
                    noise=noise_power,
                    signal=signal_power,
                    gain=signal_gain,
                    dc=dc_val,
                    snr=snr_val,
                    image=image_val,
                    imrr=imrr_val,
                    nf=nf_value,
                    sensitive=None
                )
                
                # 保存文件（使用tone的数据）
                IQSWAP_HEX = [g + i + q for g, i, q in zip(gain_tone, Qdata_tone, Idata_tone)]
                file_path = r'C:\workspace\ECW6700\MPW\tools\ECR6600_6600U_6630 Configuration Software1.0.0-IQswaq\ECR6600_6600U_6630 Configuration Software1.0.0\builds\ECR6600series Configuration Software1.0.2\RX Dump\iqdata_%s_%d_%s.txt'%(ble_mode,2400+chn*2-if_offset,dump_type_str)
                with open(file_path, 'w') as file:
                    for item in IQSWAP_HEX:
                        file.write(item + '\n')
                log("数据已成功写入 iqdata_%s_%d_%s.txt 文件。"%(ble_mode,2400+chn*2-if_offset,dump_type_str),color="red")
                
            else:  # 原有的单次dump逻辑
                if(dump_type == 0):
                    N5182B.write(':OUTPut:STATe OFF')
                else:
                    N5182B.write(':OUTPut:STATe ON')
                log(f'amtBleRxStartInf {rate_num} {chn}')
                SerialPort.write_cmd(f'amtBleRxStartInf {rate_num} {chn}')
                N5182B.write('*TRG')
                SerialPort.write_cmd(f'amtbleiqdump 0 0 0x7fff 0x3a98')
                time.sleep(0.1)
                SerialPort.write_reg(0x2020e000,0x0)
                N5182B.write(':OUTPut:STATe OFF')
                SerialPort.write_cmd(f'amtBleRxStop')
                SerialPort.flush_Input()
                SerialPort.write_cmd(f'read 0x20000000 {SN*4}')
                temp = SerialPort.read_all_bytes()    #读取串口缓冲区的值                
                rxdump_data = temp.decode('UTF-8')      #串口读出来的bytes解码成字符串
                hex_list = re.findall(r': ([0-9a-fA-F]+)\r\n', rxdump_data)
                gain  = [hex_value[0:2] for hex_value in hex_list]
                Idata = [hex_value[2:5] for hex_value in hex_list]
                Qdata = [hex_value[5:8] for hex_value in hex_list]
                Idata_dec_tmp = hex2sint_list(Idata,12)
                Qdata_dec_tmp = hex2sint_list(Qdata,12)
                
                # ========== 调用IQ数据分析 ==========
                analysis_result = analyze_iq_signal(
                    Idata=Idata_dec_tmp,
                    Qdata=Qdata_dec_tmp,
                    fs=fs,
                    vpp=vpp,
                    nbit=nbit,
                    sg_pwr=AMPTD,
                    dump_noise=1 if dump_type == 0 else 0,
                    figure_off=0,  # 显示图表
                    target_tone_freq=tone_freq*1e6 if tone_freq > 0 else 1e6
                )
                
                # 通过回调函数更新UI中的图表
                if chart_update_callback and 'time_chart' in analysis_result and 'freq_chart' in analysis_result:
                    try:
                        chart_update_callback(analysis_result['time_chart'], analysis_result['freq_chart'])
                        log("图表已更新到UI", color="blue")
                    except Exception as chart_error:
                        log(f"更新图表到UI时出错: {str(chart_error)}", color="red")
                # 获取分析结果
                noise_val = analysis_result.get('noise')
                signal_val = analysis_result.get('signal')
                gain_val = analysis_result.get('gain')
                dc_val = analysis_result.get('dc')
                snr_val = analysis_result.get('snr')
                image_val = analysis_result.get('image')
                imrr_val = analysis_result.get('imrr')
                log(f"分析结果: {noise_val}", color="green")
                # 将结果插入数据库
                insert_test_data(
                    table_name="ble_test_results",
                    chn=chn,
                    rate=ble_mode,
                    noise=noise_val,
                    signal=signal_val,
                    gain=gain_val,
                    dc=dc_val,
                    snr=snr_val,
                    image=image_val,
                    imrr=imrr_val,
                    nf=None,         # NF 后续可计算
                    sensitive=None   # sensitivity 可选
                )
                
                #交换IQ，并拼接成新的list
                IQSWAP_HEX = [g + i + q for g, i, q in zip(gain, Qdata, Idata)]
                # 指定文件路径
                file_path = r'C:\workspace\ECW6700\MPW\tools\ECR6600_6600U_6630 Configuration Software1.0.0-IQswaq\ECR6600_6600U_6630 Configuration Software1.0.0\builds\ECR6600series Configuration Software1.0.2\RX Dump\iqdata_%s_%d_%s.txt'%(ble_mode,2400+chn*2-if_offset,dump_type_str)
                
                # 将 iqdata 列表写入文件
                with open(file_path, 'w') as file:
                    for item in IQSWAP_HEX:
                        file.write(item + '\n')
                
                log("数据已成功写入 iqdata_%s_%d_%s.txt 文件。"%(ble_mode,2400+chn*2-if_offset,dump_type_str),color="red")

    SerialPort.close()
    N5182B.close()
    rm.close()
