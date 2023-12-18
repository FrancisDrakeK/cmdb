#!/usr/bin/env python3
# coding=utf-8
# @File    : get_hw_disk_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-25 重构完成&测试通过
# @Cmd : nvme,smartctl,lsblk
import json
import re
import subprocess

from pydantic import BaseModel


class HwDiskInfoModel(BaseModel):
    """
    磁盘 信息模型
    """

    # 将SN变更为name
    name: str = None
    pn: str = None
    size: str = None
    fw: str = None
    dev_name: str = None
    vendor: str = None


class GetHwDiskInfo:
    # 获取disk信息部分重构完成
    def get_disk_info(self):
        disk_info_list = []

        def get_nvme_disk_info():
            process = subprocess.Popen(
                "sudo nvme list -o json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            output, error = process.communicate()
            nvme_info_ori_dict = json.loads(output.decode("utf-8"))

            def get_disk_pn_and_vendor(hw_disk_info_model, nvme_dict):
                pn = nvme_dict["ModelNumber"]
                if re.search("Micron", pn):
                    hw_disk_info_model.pn = pn
                    hw_disk_info_model.vendor = "Micron"

                elif re.search("Dell", pn):
                    hw_disk_info_model.pn = "AGN"
                    hw_disk_info_model.vendor = "Dell"
                else:
                    hw_disk_info_model.pn = pn
                    hw_disk_info_model.vendor = pn.split()[0]

            # 遍历当前 NVME设备列表
            for nvme in nvme_info_ori_dict["Devices"]:
                my_hw_disk_info_model = HwDiskInfoModel()
                my_nvme_name = nvme["DevicePath"]
                # 获取硬盘位置
                my_hw_disk_info_model.dev_name = my_nvme_name
                get_disk_pn_and_vendor(my_hw_disk_info_model, nvme)
                # 获取硬盘固件版本
                my_hw_disk_info_model.fw = nvme["Firmware"]
                # 获取序列号
                my_hw_disk_info_model.name = nvme["SerialNumber"]

                # 获取磁盘容量 单位TB
                single_disk_size = round(int(nvme["PhysicalSize"]) / (1000**4), 2)
                my_hw_disk_info_model.size = f"{single_disk_size} TB"

                disk_info_list.append(my_hw_disk_info_model.model_dump())

        def get_sata_disk_info():
            #  获取sata 设备列表
            sata_info_ori_list = subprocess.getoutput(
                "lsblk -d -e 259 -n -o NAME"
            ).split("\n")
            # 过滤掉设备列表中以非sd开头的元素
            sata_info_list = list(
                filter(lambda x: x.startswith("sd"), sata_info_ori_list)
            )

            for sata_dev in sata_info_list:
                my_hw_disk_info_model = HwDiskInfoModel()
                # 获取硬盘位置
                my_hw_disk_info_model.dev_name = f"/dev/{sata_dev}"
                # 查询smart信息
                sata_dev_dict = json.loads(
                    subprocess.getoutput(
                        f"sudo smartctl -j -a {my_hw_disk_info_model.dev_name}"
                    )
                )

                # 防止出现 product不存在:
                if "product" in sata_dev_dict.keys():
                    # 获取硬盘型号
                    my_hw_disk_info_model.pn = sata_dev_dict["product"]
                else:
                    my_hw_disk_info_model.pn = sata_dev_dict["model_name"]

                # 获取硬盘固件版本
                my_hw_disk_info_model.fw = sata_dev_dict["firmware_version"]
                # 获取序列号
                my_hw_disk_info_model.name = sata_dev_dict["serial_number"]

                # 防止出现 product不存在:
                if "vendor" in sata_dev_dict.keys():
                    # 获取厂商信息
                    my_hw_disk_info_model.vendor = sata_dev_dict["vendor"]
                else:
                    my_hw_disk_info_model.vendor = None

                # 获取磁盘容量 单位TB
                single_disk_size = round(
                    int(sata_dev_dict["user_capacity"]["bytes"]) / (1000**4), 2
                )
                my_hw_disk_info_model.size = f"{single_disk_size} TB"

                disk_info_list.append(my_hw_disk_info_model.model_dump())

        get_nvme_disk_info()
        get_sata_disk_info()

        final_dict = {
            "plugin_name": self.__class__.__name__,
            "contains": disk_info_list,
        }

        return final_dict


if __name__ == "__main__":
    get_host_info = GetHwDiskInfo().get_disk_info()
    # 重构返回json结构
    # 获取contians 中的 list
    data_list = get_host_info["contains"]
    # 再存入新列表
    new_list = []
    for data in data_list:
        tmp_dict = {
            "name": data["name"],
            "type": "disk",
            "updatedAt": None,
        }
        data.pop("name")
        tmp_dict["data"] = data
        new_list.append(tmp_dict)
    final_dict = {
        "plugin_name": get_host_info["plugin_name"],
        "contains": new_list,
    }
    print(json.dumps(final_dict, indent=4))
