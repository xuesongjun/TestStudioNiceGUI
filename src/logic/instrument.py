import pyvisa
from pages.layout import log

def check_connection(ip: str):
    """检测仪表 IP 是否可连"""
    try:
        rm = pyvisa.ResourceManager()
        resource_str = f"TCPIP0::{ip}::inst0::INSTR"
        log(f"尝试连接: {resource_str}",color="blue")
        inst = rm.open_resource(resource_str)
        idn = inst.query("*IDN?")
        log(f"连接成功: {idn.strip()}")
        inst.close()
    except Exception as e:
        log(f"连接失败: {e}")
