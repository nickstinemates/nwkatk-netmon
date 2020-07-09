# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import sys
import os
import asyncio
from importlib import metadata

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import click
from nwkatk.cli.inventory import opts_inventory, pass_inventory_records

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from nwkatk_netmon.config import load_config_file
from nwkatk_netmon.config_model import ConfigModel
from nwkatk_netmon.log import log

VERSION = metadata.version(__package__)


async def async_main_device(inventory_rec, config: ConfigModel):
    interval = config.defaults.interval

    rec_host = inventory_rec['host']
    host = inventory_rec.get("ipaddr") or rec_host
    if not (os_name := inventory_rec['os_name']) in config.os_name:
        log.error(f"{rec_host} uses os_name {os_name} not found in config, skipping.")
        return

    device_cls = config.os_name[os_name].driver
    creds = config.defaults.credentials

    device = device_cls(
        host=host, creds=(creds.username, creds.password.get_secret_value()),
        private={"tags": inventory_rec.copy()}
    )

    for c_name, c_entry_point in config.collectors.items():
        c_config = config.collector_configs.get(c_name) or {}
        c_config.setdefault('interval', interval)
        asyncio.create_task(c_entry_point(device, **c_config))


def set_log_level(ctx, param, value):
    log.setLevel(value.upper())


@click.command()
@click.version_option(version=VERSION)
@click.option(
    "--config",
    "-C",
    type=click.File(),
    default="netmon.toml",
    callback=load_config_file,
)
@opts_inventory
@click.option(
    "--interval",
    type=click.IntRange(min=10),
    help="collection interval (seconds)",
)
@click.option(
    "--log-level",
    help="log level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    default="info",
    callback=set_log_level,
)
@pass_inventory_records
def cli_netifdom(inventory_records, config, **kwargs):
    if interval := kwargs['interval']:
        config.defaults.interval = interval

    loop = asyncio.get_event_loop()
    for rec in inventory_records:
        loop.create_task(async_main_device(rec, config=config))

    loop.run_forever()


def main():
    try:
        cli_netifdom()

    except Exception:  # noqa
        import traceback

        content = traceback.format_exc(limit=-1)
        sys.exit(content)


if __name__ == "__main__":
    main()
