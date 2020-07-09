import asyncio
from asynceapi import Device

from nwkatk_netmon.collectors import Metric, interval_collector, b64encodestr
from nwkatk_netmon.collectors.ifdom import ifdom_start
from nwkatk_netmon.exporters.circonus import export_metrics
from nwkatk_netmon.log import log


@ifdom_start.register
async def start(device: Device, interval, **kwargs):
    log.info(f"{device.host}: Connecting to EOS device")

    try:
        res = await device.exec(["show hostname"])
    except Exception as exc:
        log.error(f"{device.host} No API access: {str(exc)}, skipping.")
        return

    device.host = res[0].output["hostname"]
    log.info(f"{device.host}: Starting Interface DOM collection")
    asyncio.create_task(get_dom_metrics(device, interval=interval, **kwargs))


@interval_collector()
async def get_dom_metrics(device: Device, interval: int, **kwargs):  # noqa
    log.debug(f"{device.host}: Getting DOM information")

    if_dom_res, if_desc_res = await device.exec(
        ["show interfaces transceiver detail", "show interfaces description"]
    )

    if not if_dom_res.ok:
        log.error(
            f"{device.host}: failed to collect DOM information: {if_dom_res.output}, aborting device."
        )
        return

    # both ifs_desc and ifs_dom are dict[<if_name>]

    ifs_desc = if_desc_res.output["interfaceDescriptions"]
    ifs_dom = if_dom_res.output["interfaces"]

    def ok_process_if(if_name):

        # if the interface name does not exist in the interface description data it likely means that the interface name
        # is an unused transciever lane; and if so then it would be the same data as the "first lane".  In this case we
        # don't need to record a duplicate metric.

        if not (if_desc := ifs_desc.get(if_name)):
            return False

        # do not report on interfaces that are administratively disabled.

        if if_desc["interfaceStatus"] == "adminDown":
            return False

        return True

    if_metrics = [
        measurement
        for if_name, if_dom_data in ifs_dom.items()
        if if_dom_data and ok_process_if(if_name)
        for measurement in make_if_metrics(
            if_name, if_dom_data, if_desc=ifs_desc[if_name]["description"]
        )
    ]

    if if_metrics:
        asyncio.create_task(
            export_metrics(device=device, metric_prefix="ifdom", metrics=if_metrics)
        )


def make_if_metrics(if_name, if_dom_data, if_desc):
    c_tags = {
        "if_name": if_name,
        "if_desc": b64encodestr(if_desc),
        "media": b64encodestr(if_dom_data["mediaType"]),
    }

    m_values = {
        "txpower": if_dom_data["txPower"],
        "rxpower": if_dom_data["rxPower"],
        "temp": if_dom_data["temperature"],
        "voltage": if_dom_data["voltage"],
    }

    thresholds = if_dom_data["details"]
    m_values.update(
        {
            "txpower_status": threshold_outside(
                value=m_values["txpower"], thresholds=thresholds["txPower"]
            ),
            "rxpower_status": threshold_outside(
                value=m_values["rxpower"], thresholds=thresholds["rxPower"]
            ),
            "temp_status": threshold_outside(
                value=m_values["temp"], thresholds=thresholds["temperature"]
            ),
            "voltage_status": threshold_outside(
                value=m_values["voltage"], thresholds=thresholds["voltage"]
            ),
        }
    )

    for m_name in m_values:
        yield Metric(
            name=m_name, value=m_values[m_name], tags=c_tags,
        )


def threshold_inside(value, thresholds):
    if thresholds["lowAlarm"] >= value >= thresholds["highAlarm"]:
        return 2

    if thresholds["lowWarn"] >= value >= thresholds["highWarn"]:
        return 1

    return 0


def threshold_outside(value, thresholds):
    if value <= thresholds["lowAlarm"] or value >= thresholds["highAlarm"]:
        return 2

    if value <= thresholds["lowWarn"] or value >= thresholds["highWarn"]:
        return 1

    return 0
