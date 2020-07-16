# Copyright 2020, Jeremy Schulman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup, find_packages
from itertools import chain

package_name = "nwkatk_netmon"
package_version = open("VERSION").read().strip()


def requirements(filename="requirements.txt"):
    return open(filename.strip()).readlines()


with open("README.md", "r") as fh:
    long_description = fh.read()

# -----------------------------------------------------------------------------
#
#                           Extras Requirements
#
# -----------------------------------------------------------------------------

# builtin extras to support Cisco NX-API and Arista EOS device driver.

extras_require = {
    "nxapi": requirements("requirements-drivers-nxapi.txt"),
    "eapi": requirements("requirements-drivers-eapi.txt"),
    "ios": requirements("requirements-drivers-ssh.txt"),
}

# add the option for all optional extras
extras_require["all"] = list(chain.from_iterable(extras_require.values()))


# -----------------------------------------------------------------------------
#
#                                 Main Setup
#
# -----------------------------------------------------------------------------

setup(
    name=package_name,
    version=package_version,
    description="Network Automation Monitoring Toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jeremy Schulman",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements(),
    extras_require=extras_require,
    entry_points={
        "console_scripts": ["nwka-netmon = nwkatk_netmon.script:main"],
        "nwka_netmon.device_drivers": [
            "cisco.nxapi = nwkatk_netmon.drivers.nxapi:Device",
            "arista.eos = nwkatk_netmon.drivers.eapi:Device",
        ],
        "nwka_netmon.collectors": [
            "ifdom = nwkatk_netmon.collectors.ifdom:IFdomCollector"
        ],
        "nwka_netmon.exporters": [
            "circonus = nwkatk_netmon.exporters.circonus:CirconusExporter",
            "influxdb = nwkatk_netmon.exporters.influxdb:InfluxDBExporter",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
    ],
)
