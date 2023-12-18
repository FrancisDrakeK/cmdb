#!/usr/bin/env python3
# coding=utf-8
# @File    : get_host_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-25 重构完成&测试通过
# @Cmd : dmidecode,ipmitool,lsb_release,lscpu
import logging as llog
import platform
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel


class HostInfoModel(BaseModel):
    """
    主机信息模型
    """

    host_ip: str = None
    host_name: str = None
    host_sn: str = None
    host_vendor: str = None
    host_pn: str = None
    host_bios_version: str = None
    host_bmc_ip: str = None
    host_bmc_version: str = None


class OsInfoModel(BaseModel):
    """
    操作系统信息模型
    """

    os_name: str = None
    os_version: str = None
    os_arch: str = None
    os_bit: str = None
    os_type: str = None


class CpuInfoModel(BaseModel):
    """
    CPU信息模型
    """

    cpu_model: str = None
    cpu_logic_cores: int = None
    cpu_physical_cores: int = None
    cpu_sockets: int = None
    cpu_frequency: str = None
    cpu_hyperthreading: bool = True


class GetHostInfo:
    """
    # 获取基础信息：内网IP,设备SN,主机名称,厂商,设备型号,BIOS固件版本
    # 操作系统:操作系统类型,操作系统名称,操作系统版本,操作系统位数
    # CPU:CPU物理核心数,CPU逻辑核心数,CPU型号,CPU主频,CPU路数
    """

    def __init__(self):
        self.os_info_model = OsInfoModel()
        self.host_info_model = HostInfoModel()
        self.cpu_info_model = CpuInfoModel()

        # 获取 GetHostBaseInfo 中的所有非内置方法对象
        all_methods = [
            getattr(self, method_name)
            for method_name in dir(self)
            if callable(getattr(self, method_name)) and not method_name.startswith("__")
        ]
        # 顺序执行列表
        seq_exe_methods_list = [
            "get_hostname",
            "get_sn",
            "get_ip",
        ]

        # 多线程执行
        with ThreadPoolExecutor(
            len(all_methods) - len(seq_exe_methods_list)
        ) as executor:
            for method in all_methods:
                if method.__name__ not in seq_exe_methods_list:
                    try:
                        executor.submit(method)
                        llog.debug(f"多线程提交了{method.__name__}")
                    except Exception as e:
                        llog.exception(f"获取主机{method.__name__}基础信息异常{e}")
        # 存在依赖关系的串行执行
        hostname = self.get_hostname()
        self.get_sn(hostname)
        self.get_ip(hostname)
        self.final_dict = {
            "plugin_name": self.__class__.__name__,
            "os_info": self.os_info_model.model_dump(),
            "host_info": self.host_info_model.model_dump(),
            "cpu_info": self.cpu_info_model.model_dump(),
        }

    def get_hostname(self):
        """
        获取主机名
        :return: 主机名
        """
        host_name = socket.gethostname()
        self.host_info_model.host_name = host_name
        return host_name

    def get_vendor(self):
        """
        获取供应商信息
        """
        self.host_info_model.host_vendor = subprocess.getoutput(
            "sudo dmidecode -s  system-manufacturer"
        )

    def get_ip(self, hostname):
        """
        获取以太网卡IP
        :param hostname: 原始主机名
        :return: 以太网卡IP
        """

        ip = socket.gethostbyname(f"{hostname}.hf")
        self.host_info_model.host_ip = ip
        return ip

    def get_pn(self):
        pn = subprocess.getoutput("sudo dmidecode -s  system-product-name")
        if pn == "Th -[7Z01CTO1WW]-":
            pn = "ThinkSystem SR655 -[7Z01CTO1WW]-"
        self.host_info_model.host_pn = pn

    def get_sn(self, hostname):
        if re.search("dgx", hostname):
            sn = subprocess.getoutput("sudo dmidecode -s chassis-serial-number")
        else:
            sn = subprocess.getoutput("sudo dmidecode -s system-serial-number").strip()
        self.host_info_model.host_sn = sn

    def get_bios_version(self):
        bios_info = subprocess.getoutput("sudo dmidecode  -t bios")

        res = re.search("BIOS Revision:\\s*(.*)", bios_info)
        other_res = re.search("Version:\\s*(.*)", bios_info)
        if res:
            bios = res.group(1).strip()
        elif other_res:
            bios = other_res.group(1).strip()
        else:
            bios = None
            llog.warning("没有捕获到bios版本信息")

        self.host_info_model.host_bios_version = bios

    def get_bmc_addr(self):
        """
        会先测试 IPMI是否正常并获取BMC IP地址
        :return: bmc_addr
        """
        subprocess.check_call(
            "ipmitool -V",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        bmc_info = subprocess.getoutput("sudo ipmitool lan print")
        # 定义正则表达式，匹配 IP 地址
        ip_pattern = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
        # 使用正则表达式搜索字符串中的 IP 地址
        match = re.search(f"IP Address.*\\s({ip_pattern})", bmc_info)
        if match:
            bmc_addr = match.group(1)
        else:
            bmc_addr = None
            llog.warning("没有获取到本机bmc地址")
        self.host_info_model.host_bmc_ip = bmc_addr

    def get_bmc_version(self):
        ori_ipmi_info = subprocess.getoutput("sudo ipmitool mc info")
        bmc_version = re.search("Firmware Revision\\s*:\\s*(.*)", ori_ipmi_info)
        child_version_hex = (
            re.split("Aux Firmware Rev Info\\s*:", ori_ipmi_info)[-1].strip().split()[0]
        )
        # 进制转换
        child_version = int(child_version_hex, 16)

        if bmc_version and child_version:
            self.host_info_model.host_bmc_version = (
                bmc_version.group(1) + "." + str(child_version)
            )

    def get_os_type(self):
        self.os_info_model.os_type = platform.system()

    def get_os_bit(self):
        self.os_info_model.os_bit = platform.architecture()[0]

    def get_os_arch(self):
        self.os_info_model.os_arch = platform.machine()

    def get_os_name_and_version(self):
        lsb_info = subprocess.getoutput("sudo lsb_release -a")

        os_name = re.search("Distributor ID:\\s(.*)", lsb_info)
        os_version = re.search("Release:\\s*(.*)", lsb_info)
        if os_name:
            self.os_info_model.os_name = os_name.group(1)
        else:
            llog.warning("没有成功获取到操作系统名！")

        if os_version:
            self.os_info_model.os_version = os_version.group(1)
        else:
            llog.warning("没有成功获取到操作系统名！")

    def get_cpu_info(self):
        # 默认超线程开启
        cpu_info = subprocess.getoutput("lscpu")

        def get_cpu_cores():
            try:
                cpu_logic_core = re.search("CPU\\(s\\):\\s*(.*)", cpu_info)
                cpu_physical_core = re.search(
                    "Core\\(s\\) per socket:\\s*(.*)", cpu_info
                )
                cpu_hyper_thread = re.search(
                    "Thread\\(s\\) per core:\\s*(.*)", cpu_info
                )

                if cpu_logic_core:
                    self.cpu_info_model.cpu_logic_cores = int(cpu_logic_core.group(1))
                else:
                    llog.warning("未获取到CPU逻辑核心数！")

                if cpu_physical_core:
                    self.cpu_info_model.cpu_physical_cores = int(
                        cpu_physical_core.group(1)
                    )
                else:
                    llog.warning("未获取到CPU物理核心数！")

                if cpu_hyper_thread:
                    if int(cpu_hyper_thread.group(1)) != 2:
                        self.cpu_info_model.cpu_hyperthreading = False
                else:
                    llog.warning("未获取到CPU是否开启超线程")

            except Exception as e:
                llog.exception(f"{e}")

        def get_cpu_socket():
            cpu_socket = re.search("Socket\\(s\\).*:\\s*(.*)", cpu_info)
            if cpu_socket:
                self.cpu_info_model.cpu_sockets = int(cpu_socket.group(1))
            else:
                llog.warning("未获取到CPU物理socket数！")

        def get_cpu_model():
            cpu_model = re.search("Model name:\\s*(.*)", cpu_info)
            if cpu_model:
                self.cpu_info_model.cpu_model = cpu_model.group(1)
            else:
                llog.warning("未获取到CPU型号！")

        def get_cpu_frequency():
            cpu_frequency = re.search("CPU max MHz:\\s*(.*)", cpu_info)

            if cpu_frequency:
                self.cpu_info_model.cpu_frequency = (
                    f"{int(float(cpu_frequency.group(1)))} MHz"
                )
            else:
                llog.warning("未获取到CPU频率！")

        get_cpu_cores()
        get_cpu_socket()
        get_cpu_model()
        get_cpu_frequency()


if __name__ == "__main__":
    import json

    get_host_info = GetHostInfo().final_dict
    # 重构返回json结构

    # os_info,host_info,cpu_info 三个字典合成一个字典
    merge_dict = get_host_info["host_info"].copy()
    merge_dict.update(get_host_info["cpu_info"])
    merge_dict.update(get_host_info["os_info"])

    final_dict = {
        "plugin_name": get_host_info["plugin_name"],
        "name": merge_dict["host_name"],
        "type": "node",
        "desc": None,
        "updatedAt": None,
    }
    merge_dict.pop("host_name")
    final_dict["data"] = merge_dict

    print(json.dumps(final_dict, indent=4))
