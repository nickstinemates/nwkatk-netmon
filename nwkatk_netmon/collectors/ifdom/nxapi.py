# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import asyncio
from functools import lru_cache

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from lxml.etree import Element
from asyncnxapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon.collectors import Metric, b64encodestr, interval_collector
from nwkatk_netmon.collectors.ifdom import ifdom_start
from nwkatk_netmon.exporters.circonus import export_metrics
from nwkatk_netmon.log import log


@ifdom_start.register
async def start(device: Device, interval, **kwargs):
    log.info(f"{device.host}: Connecting to NX-OS device")

    try:
        res = await device.exec(["show hostname"])
    except Exception as exc:
        log.error(f"{device.host} No API access: {str(exc)}, skipping.")
        return

    device.host = res[0].output.findtext("hostname")
    log.info(f"{device.host}: Starting Interface DOM collection")

    asyncio.create_task(get_dom_metrics(device, interval=interval, **kwargs))


@interval_collector()
async def get_dom_metrics(device: Device, interval: int, **kwargs):  # noqa
    log.info(f"{device.host}: Process DOM metrics")
    ifs_status_res, ifs_dom_res = await device.exec(
        ["show interface status", "show interface transceiver details"]
    )

    def generate_ifstatus():
        ifs_status_el = ifs_status_res.output.xpath(".//ROW_interface")
        res_dict = dict()
        for ele in ifs_status_el:
            as_dict = row_to_dict(ele)
            if_name = as_dict.pop("interface")
            res_dict[if_name] = as_dict

        return res_dict

    ifs_status = generate_ifstatus()

    ifs_dom_el = ifs_dom_res.output.xpath('.//ROW_interface[sfp="present"]')

    def ok_for_dom(_if_name, if_data):
        if ifs_status[_if_name]["state"] != "connected":
            return False

        if "temperature" not in if_data:
            return False

        return True

    def generate_metrics():
        for ele in ifs_dom_el:
            as_dict = row_to_dict(ele)
            if_name = as_dict["interface"]

            if not ok_for_dom(if_name, as_dict):
                continue

            if_tags = {
                "if_name": if_name,
                "if_desc": b64encodestr(ifs_status[if_name]["name"].strip()),
                "media": b64encodestr((as_dict["type"] or as_dict["partnum"]).strip()),
            }

            try:
                yield Metric(
                    name="voltage", value=float(as_dict["voltage"]), tags=if_tags
                )
                yield Metric(
                    name="txpower", value=float(as_dict["tx_pwr"]), tags=if_tags
                )
                yield Metric(
                    name="rxpower", value=float(as_dict["rx_pwr"]), tags=if_tags
                )
                yield Metric(
                    name="temp", value=float(as_dict["temperature"]), tags=if_tags
                )

                yield Metric(
                    "rxpower_status",
                    from_flag_to_status(as_dict["rx_pwr_flag"]),
                    if_tags,
                )
                yield Metric(
                    "txpower_status",
                    from_flag_to_status(as_dict["tx_pwr_flag"]),
                    if_tags,
                )
                yield Metric(
                    "voltage_status", from_flag_to_status(as_dict["volt_flag"]), if_tags
                )
                yield Metric(
                    "temp_status", from_flag_to_status(as_dict["temp_flag"]), if_tags
                )

            except KeyError as exc:
                log.error(f"{device.host}: unable to obtain DOM metric {str(exc)}")
                return

    if_dom_metrics = list(generate_metrics())
    if if_dom_metrics:
        asyncio.create_task(
            export_metrics(device=device, metric_prefix="ifdom", metrics=if_dom_metrics)
        )


@lru_cache
def from_flag_to_status(flag):
    """
     ++  high-alarm; +  high-warning; --  low-alarm; -  low-warning
    """
    return {"++": 2, "--": 2, "+": 1, "-": 1}.get(flag.strip(), 0)


def row_to_dict(row: Element):
    return {ele.tag: ele.text for ele in row.iterchildren()}
