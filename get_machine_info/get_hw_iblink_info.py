#!/usr/bin/env python3
# coding=utf-8
# @File    : get_hw_iblink_info.py
# @Time    : 23-3-3 PM 3:00
# @Email   : xin.liu@high-flyer.cn
# @Description : 23-9-26 重构完成&测试通过
# @Cmd : ibdev2netdev,mlxlink,iblinkinfo
import re
import subprocess

from pydantic import BaseModel


class HwLinkInfoModel(BaseModel):
    """
    IB 线缆 信息模型
    """

    name: str = None
    pn: str = None
    length: int = None
    vendor: str = None
    speed: str = None
    swport: str = None


class GetHwIbLinkInfo:
    def get_ib_name(self):
        ib_dev_info = subprocess.getoutput("ibdev2netdev")
        ib_name_list = re.findall(r"(mlx\d_\d+).*==>.*", ib_dev_info)
        if ib_name_list:
            return ib_name_list
        else:
            return None

    def get_cable_info(self):
        ib_name_list = self.get_ib_name()
        ib_link_list = []
        if ib_name_list:
            for ib_name in ib_name_list:
                hw_link_info_model = HwLinkInfoModel()
                ibcables_ori_info = subprocess.getoutput(
                    f"sudo mlxlink -d  {ib_name} -m"
                )
                iblinki_ori_info = subprocess.getoutput(
                    f"sudo iblinkinfo -C  {ib_name} "
                )
                sn = re.search(r"Vendor\sSerial\sNumber\s*:\s(.+)", ibcables_ori_info)
                if sn and sn.group(1) != "N/A":
                    hw_link_info_model.name = sn.group(1)
                else:
                    continue

                vendor = re.search(r"Vendor\sName\s*:\s(.+)", ibcables_ori_info)
                if vendor and vendor.group(1) != "N/A":
                    hw_link_info_model.vendor = vendor.group(1)

                pn = re.search(r"Vendor\sPart\sNumber\s*:\s(.+)", ibcables_ori_info)
                if pn and pn.group(1) != "N/A":
                    hw_link_info_model.pn = pn.group(1)

                #     因为字体会被设置为绿色，需要把 \x1b\[32m 匹配在内
                speed = re.search(r"Speed\s{30}:\s\x1b\[32m(.+)", ibcables_ori_info)
                if speed and speed.group(1) != "N/A":
                    hw_link_info_model.speed = speed.group(1)
                length = re.search(r"Transfer\sDistance\s.*:\s(\d+)", ibcables_ori_info)
                if length:
                    hw_link_info_model.length = int(length.group(1))
                # 如果倒数第二行没有 ibwarn 则iblink 执行成功
                ib_link = iblinki_ori_info.split("\n")[-2]
                if "ibwarn" not in ib_link:
                    # 获取iblinkinfo 的倒数第一行的 内容 然后以”分割取倒数第二个为连接点
                    hw_link_info_model.swport = iblinki_ori_info.split("\n")[-1].split(
                        '"'
                    )[-2]

                ib_link_list.append(hw_link_info_model.model_dump())

            final_dict = {
                "plugin_name": self.__class__.__name__,
                "contains": ib_link_list,
            }

            return final_dict


if __name__ == "__main__":
    import json

    get_cable_info = GetHwIbLinkInfo().get_cable_info()

    # 重构返回json结构
    # 获取contians 中的 list
    data_list = get_cable_info["contains"]
    # 再存入新列表
    new_list = []
    for data in data_list:
        tmp_dict = {
            "name": data["name"],
            "type": "iblink",
            "updatedAt": None,
        }
        data.pop("name")
        tmp_dict["data"] = data
        new_list.append(tmp_dict)
    final_dict = {
        "plugin_name": get_cable_info["plugin_name"],
        "contains": new_list,
    }
    print(json.dumps(final_dict, indent=4))
