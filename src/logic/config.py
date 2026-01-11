from ex4nicegui import to_ref
from datetime import datetime
import os

# 网络配置
ip_addr = to_ref("")  # VISA仪器IP地址

# 串口配置
com_num = to_ref("")  # 串口号,默认空字符串

# DUT和批次信息
dut_id = to_ref("")  # DUT编号,如 #3, #4
batch_id = to_ref(datetime.now().strftime("%Y%m%d_%H%M"))  # 批次编号,默认当前时间

# 测试参数默认值
default_signal_amptd = to_ref(-70)  # 默认信号功率(dBm)
default_cable_loss = to_ref(0.65)   # 默认线损(dB)
default_dump_type = to_ref(0)       # 默认Dump类型: 0=noise, 1=tone, 2=wave

# IQ 数据采集参数
fs = to_ref(24e6)  # 采样率(Hz)
SN = to_ref(4096)  # 采样点数
vpp = to_ref(1.1)  # ADC参考电压峰峰值(V)
nbit = to_ref(12)  # ADC位数

# 文件存储配置
dump_file_path = to_ref(os.path.join(os.getcwd(), "data", "iq_dumps"))  # IQ dump文件存放路径

# 信道配置
channel_count = 40  # 总信道数量
default_channels = [0]  # 默认选择的信道

# BLE制式配置
ble_modes = ["LE1M", "LE2M", "LES2", "LES8"]  # 支持的BLE制式
default_ble_mode = ["LE1M"]  # 默认选择的BLE制式

# 应用配置
app_port = 8080  # 应用运行端口
app_title = "测试工作室"  # 应用标题

# 数据库配置
db_path = "data/test_results.db"  # 数据库文件路径

# 日志配置
log_max_lines = 1000  # 日志区域最大显示行数