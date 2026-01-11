import pyvisa
from pages.layout import log
from nicegui import ui

def check_connection(ip: str):
    """检测仪表 IP 是否可连"""
    if not ip or ip.strip() == "":
        ui.notify("请先输入IP地址", type='warning')
        log("检测连接失败: IP地址为空", color="red")
        return

    try:
        rm = pyvisa.ResourceManager()
        resource_str = f"TCPIP0::{ip}::inst0::INSTR"
        log(f"尝试连接: {resource_str}", color="blue")
        ui.notify(f"正在连接 {ip}...", type='info')

        inst = rm.open_resource(resource_str)
        idn = inst.query("*IDN?")
        log(f"连接成功: {idn.strip()}", color="green")
        ui.notify(f"连接成功: {idn.strip()}", type='positive')
        inst.close()
        rm.close()
    except Exception as e:
        log(f"连接失败: {e}", color="red")
        ui.notify(f"连接失败: {str(e)}", type='negative')
