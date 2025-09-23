#!/usr/bin/env python
# coding: utf-8


import serial
import time

class SerialCommunication():

    def __init__(self,com_num,buand,dump_cfg_en=False, file_path=None):
        '''打开port口'''
        self.port = serial.Serial('com%d'%(com_num), buand, timeout=1, write_timeout=1)
        self.dump_cfg_en = dump_cfg_en
        if dump_cfg_en and file_path:
            self.f = open(file_path, 'w')
        else:
            self.f = None
        
    def close(self):
        self.port.close()
        
    def write_reg(self,addr,value):
        '''写寄存器'''
        self.port.write(("write 0x%x 0x%x\r\n"%(addr,value)).encode())  #windows里\r\n一起才表示有效的回车换行
        if self.dump_cfg_en and self.f:
                    self.f.write("%x %x\n" % (addr, value))
                    self.f.flush()  # 确保数据立即写入文件
            #print(("%x %x"%(addr,value)))
        time.sleep(0.1)

    def write_cmd(self,command):
        '''写字符串格式的指令'''
        self.port.write(("%s\r\n"%(command)).encode())  #windows里\r\n一起才表示有效的回车换行
        time.sleep(0.01)
    
    def read_line(self):
        '''读串口打印出来的内容'''
        #self.port.write(("read 0x%x %d\r\n"%(addr,size)).encode())
        line = self.port.readline()
        time.sleep(0.1)
        return line
    
    def read_reg(self,address, num_bytes):
        '''Function to read a value from a register'''
        self.port.flushInput()
        self.port.write(f"read {hex(address)} {num_bytes} \r\n".encode())
        time.sleep(0.1)
        response = self.port.readline()
        start_index = response.find(b':') + 1
        end_index = response.find(b'\r\nOK')
        value = response[start_index:end_index-1].decode()       
        return int(value,16)

    def read_bytes(self):
        '''读串口打印出来的内容 但是一次只能读取65536个字节的数据'''
        read_data = self.port.read(self.port.inWaiting()) #in_waiting:Return the number of bytes in the receive buffer.即可读出串口中的#所有内容，超时时间内一直接收
        time.sleep(0.1)
        return read_data
    def reset_output_buffer(self):
        '''清除输出缓冲区'''
        self.port.reset_output_buffer()
        time.sleep(0.1)
        
    def reset_input_buffer(self):
        '''清除输入缓冲区'''
        self.port.reset_input_buffer()
        time.sleep(0.1)
     
    def flush_Output(self):
        self.port.flushOutput()
        time.sleep(0.1)
    
    def flush_Input(self):
        self.port.flushInput()
        time.sleep(0.1)
    
    def read_all_bytes(self):
        total_data = b''
        while True:
            chunk = self.port.read(8192)  # 适当调整每次读取的字节数
            if not chunk:
                break
            total_data += chunk
        return total_data
        


