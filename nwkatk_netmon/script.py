#     Copyright 2020, Jeremy Schulman
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import sys
import asyncio
from importlib import metadata
from functools import update_wrapper

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

    device_name = inventory_rec["host"]

    if not (os_name := inventory_rec["os_name"]) in config.device_drivers:
        log.error(
            f"{device_name} uses os_name {os_name} not found in config, skipping."
        )
        return

    device = config.device_drivers[os_name].driver(name=device_name)
    creds = config.defaults.credentials

    try:
        device.prepare(inventory_rec=inventory_rec, config=config)
        await device.login(creds=creds)

    except RuntimeError:
        log.error(f"{device_name}: failed to authenticate to device, skipping.")
        return

    # TODO: filter options to not copy all tag values
    #       ....

    # Start each collector on the device

    for c_name, c_spec in config.collectors.items():
        c_start = c_spec.collector.start
        # c_config = c_spec.collector.config
        asyncio.create_task(c_start(device, interval=interval, config=config))


# -----------------------------------------------------------------------------

def set_log_level(ctx, param, value):  # noqa
    log.setLevel(value.upper())


def map_config_inventory(f):
    """
    This decorator is used to map the netmon config model inventory value
    into the kwargs['inventory'] so that the standard nwkatk inventory
    loader will work as expected ;-)
    """

    @click.pass_context
    def mapper(ctx, *args, **kwargs):
        kwargs["inventory"] = str(kwargs["config"].defaults.inventory)
        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(mapper, f)


@click.command()
@click.version_option(version=VERSION)
@click.option(
    "--config",
    "-C",
    type=click.File(),
    is_eager=True,
    default="netmon.toml",
    callback=load_config_file,
)
@opts_inventory
@click.option(
    "--interval", type=click.IntRange(min=30), help="collection interval (seconds)",
)
@click.option(
    "--log-level",
    help="log level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    default="info",
    callback=set_log_level,
)
@map_config_inventory
@pass_inventory_records
def cli_netifdom(inventory_records, config, **kwargs):

    if interval := kwargs["interval"]:
        config.defaults.interval = interval

    loop = asyncio.get_event_loop()
    # loop.run_until_complete(async_main_exporters(config=config))

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
