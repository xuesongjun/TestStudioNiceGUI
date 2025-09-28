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
    else:
        log("无效的 dump_type 值")

    
    for ble_mode in ble_modes_list:
        rate_num = ble_rate_map[ble_mode]
        if_offset = ble_if_offset_map[ble_mode]
        for chn in chn_list:
            chn = chn + 1
            N5182B.write(f':FREQuency:FIXed {2400+chn*2+tone_freq} MHz')
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
            
            # 输出分析结果
            #log(f"分析结果: {analysis_result}", color="green")
            # if dump_type == 0:  # noise
            #     log(f"噪声功率: {analysis_result.get('noise', 'N/A')} dBm", color="green")
            # else:  # tone or wave
            #     log(f"信号功率: {analysis_result.get('signal', 'N/A')} dBm", color="green")
            #     log(f"增益: {analysis_result.get('gain', 'N/A')} dB", color="green")
            #     log(f"DC功率: {analysis_result.get('dc', 'N/A')} dBm", color="green")
            #     log(f"镜像功率: {analysis_result.get('image', 'N/A')} dBm", color="green")
            #     log(f"SNR: {analysis_result.get('snr', 'N/A')} dB", color="green")
            #     log(f"IMRR: {analysis_result.get('imrr', 'N/A')} dB", color="green")
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
