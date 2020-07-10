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

    rec_host = inventory_rec["host"]
    host = inventory_rec.get("ipaddr") or rec_host
    if not (os_name := inventory_rec["os_name"]) in config.os_name:
        log.error(f"{rec_host} uses os_name {os_name} not found in config, skipping.")
        return

    device_cls = config.os_name[os_name].driver
    creds = config.defaults.credentials

    device = device_cls(
        host=host,
        creds=(creds.username, creds.password.get_secret_value()),
        private={"tags": inventory_rec.copy()},
    )

    for c_name, c_entry_point in config.collectors.items():
        c_config = config.collector_configs.get(c_name) or {}
        c_config.setdefault("interval", interval)
        asyncio.create_task(c_entry_point(device, **c_config))


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
