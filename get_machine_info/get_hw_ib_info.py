#!/usr/bin/env python3
# coding=utf-8
# @File    : get_hw_ib_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-25 重构完成&测试通过
# @Cmd : mlxfwmanager,modinfo,ibv_devices,ibstat,ibdev2netdev,lspci
import re
import subprocess

import netifaces
from pydantic import BaseModel


class HwIbInfoModel(BaseModel):
    """
    IB卡 信息模型
    """

    name: str = None
    pn: str = None
    speed: str = None
    fw: str = None
    bn: str = None
    driver: str = None
    ib_name: str = None
    eth_name: str = None
    vendor: str = None
    guid: str = None
    psid: str = None
    ip: str = None


class GetHwIbInfo:
    # 获取IB卡信息部分重构完成

    def get_ib_info(self):
        """
        获取IB卡的信息
        :return:
        """
        # 如函数名获取IB卡信息
        ib_info_list = []
        ib_sn_list = []
        ib_speed_list = []
        # mlxfwmanager 会消耗8M内存 并释放
        my_ib_ori_info = subprocess.getoutput("sudo mlxfwmanager")
        ib_ori_info_list = my_ib_ori_info.split("Device #")[1:]

        def get_ib_pcie_number(hw_ib_info_model, ib_info):
            ib_dev_or_pcie_name = re.search(
                "PCI Device Name:\\s*([a-zA-Z0-9_/:.]+)", ib_info
            )
            if ib_dev_or_pcie_name:
                # 因为PCI Device Name存在两种情况 81:00.0 或 /dev/mst/mt4123_pciconf0
                if re.search("/dev/mst", ib_dev_or_pcie_name.group(1)):
                    #   需要进一步处理
                    ib_dev_ori_info = subprocess.getoutput(
                        f"sudo cat {ib_dev_or_pcie_name.group(1)}"
                    )
                    ib_bn = re.search(
                        r"domain:bus:dev.fn=\s*([a-zA-Z0-9:.]+)", ib_dev_ori_info
                    )
                    if ib_bn:
                        hw_ib_info_model.bn = ib_bn.group(1)
                else:
                    hw_ib_info_model.bn = ib_dev_or_pcie_name.group(1)

        def get_ib_sn(hw_ib_info_model, ib_pcie_info):
            ib_sn = re.search("Serial number:\\s*([a-zA-Z0-9]+)", ib_pcie_info)
            if ib_sn:
                hw_ib_info_model.name = ib_sn.group(1)

        def get_ib_pn(hw_ib_info_model, ib_info):
            ib_pn = re.search("Part Number:\\s*([a-zA-Z0-9_\\-\\s]+)\n", ib_info)
            if ib_pn:
                hw_ib_info_model.pn = ib_pn.group(1)

        def get_driver_version(hw_ib_info_model, ib_pcie_info):
            # 通过模块名 去 modinfo 找具体的版本信息
            ib_driver = re.search("Kernel modules:\\s([a-zA-Z0-9_]+)", ib_pcie_info)
            if ib_driver:
                mod_info = subprocess.getoutput(f"modinfo {ib_driver.group(1)}")
                ib_driver_version = re.search("version:\\s*([0-9.\\-]*)", mod_info)
                if ib_driver_version:
                    hw_ib_info_model.driver = ib_driver_version.group(1)

        def get_ib_vendor_and_psid(hw_ib_info_model, ib_ori_info):
            ib_psid = re.search("PSID:\\s*(.*)", ib_ori_info)
            if ib_psid:
                hw_ib_info_model.psid = ib_psid.group(1)
                if re.search("MT", ib_psid.group(1)):
                    hw_ib_info_model.vendor = "Mellanox"
                if re.search("LNV", ib_psid.group(1)):
                    hw_ib_info_model.vendor = "Lenovo"

        def get_ib_guid(hw_ib_info_model, ib_ori_info):
            ib_guid = re.search("Base GUID:\\s*(.*)", ib_ori_info)
            if ib_guid:
                hw_ib_info_model.guid = ib_guid.group(1)

        def get_ib_name(hw_ib_info_model):
            ibv_dev_info = subprocess.getoutput("ibv_devices")
            ib_name = re.search(
                f"\\s*(mlx5_.+)\\s*{hw_ib_info_model.guid}", ibv_dev_info
            )
            if ib_name:
                hw_ib_info_model.ib_name = ib_name.group(1).strip()

        def get_eth_name(hw_ib_info_model):
            ibv_dev_info = subprocess.getoutput("ibdev2netdev")
            eth_name = re.search(
                f"{hw_ib_info_model.ib_name}\\sport\\s\d\\s==>\\s(\w*)\\s", ibv_dev_info
            )
            if eth_name:
                hw_ib_info_model.eth_name = eth_name.group(1)
            return eth_name.group(1)

        def get_ib_speed(hw_ib_info_model, ib_ori_info):
            ib_rate = re.search(r"Description:.*?(\d{3}G|\d{2}G)", ib_ori_info)

            if ib_rate:
                hw_ib_info_model.speed = f"{ib_rate.group(1)}"

            ib_speed_list.append(hw_ib_info_model.speed)

        def get_ib_fw(hw_ib_info_model, ib_stat_info):
            ib_fw = re.search(r"Firmware version: (.*)", ib_stat_info)
            if ib_fw:
                hw_ib_info_model.fw = ib_fw.group(1).strip()

        def get_ip(hw_ib_info_model):
            if netifaces.ifaddresses(hw_ib_info_model.eth_name).__contains__(
                netifaces.AF_INET
            ):
                # ip地址在合理范围内
                if (
                    len(
                        netifaces.ifaddresses(hw_ib_info_model.eth_name)[
                            netifaces.AF_INET
                        ][0]["addr"]
                    )
                    <= 16
                ):
                    ib_ip = netifaces.ifaddresses(hw_ib_info_model.eth_name)[
                        netifaces.AF_INET
                    ][0]["addr"]
                    hw_ib_info_model.ip = ib_ip

        # 有几张IB卡就循环几次
        for my_ib_info in ib_ori_info_list:
            my_ib_info = str(my_ib_info)
            my_hw_ib_info_model = HwIbInfoModel()

            get_ib_pn(my_hw_ib_info_model, my_ib_info)
            get_ib_pcie_number(my_hw_ib_info_model, my_ib_info)
            my_ib_pcie_info = subprocess.getoutput(
                f"sudo lspci -s {my_hw_ib_info_model.bn} -vv"
            )
            get_ib_sn(my_hw_ib_info_model, my_ib_pcie_info)
            get_driver_version(my_hw_ib_info_model, my_ib_pcie_info)
            get_ib_vendor_and_psid(my_hw_ib_info_model, my_ib_info)
            get_ib_guid(my_hw_ib_info_model, my_ib_info)
            get_ib_name(my_hw_ib_info_model)
            get_eth_name(my_hw_ib_info_model)
            get_ip(my_hw_ib_info_model)

            my_ib_stat_info = subprocess.getoutput(
                "ibstat " + my_hw_ib_info_model.ib_name
            )
            get_ib_speed(my_hw_ib_info_model, my_ib_info)
            get_ib_fw(my_hw_ib_info_model, my_ib_stat_info)
            # 最后需要将basemodel 深拷贝到 列表中
            ib_info_list.append(my_hw_ib_info_model.model_dump())

        final_dict = {
            "plugin_name": self.__class__.__name__,
            "contains": ib_info_list,
        }

        return final_dict


if __name__ == "__main__":
    import json

    get_ib_info = GetHwIbInfo().get_ib_info()
    # 重构返回json结构
    # 获取contians 中的 list
    data_list = get_ib_info["contains"]
    # 再存入新列表
    new_list = []
    for data in data_list:
        tmp_dict = {
            "name": data["name"],
            "type": "ib",
            "updatedAt": None,
        }
        data.pop("name")
        tmp_dict["data"] = data
        new_list.append(tmp_dict)
    final_dict = {
        "plugin_name": get_ib_info["plugin_name"],
        "contains": new_list,
    }
    print(json.dumps(final_dict, indent=4))
