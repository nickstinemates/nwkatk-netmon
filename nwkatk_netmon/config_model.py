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


from typing import Dict, Callable, Optional, List, Type
from operator import itemgetter

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from first import first

from pydantic import (
    BaseModel,
    BaseSettings,
    Field,
    ValidationError,  # noqa
    PositiveInt,
    validator,
    root_validator,
)

# Private Imports

from nwkatk_netmon import consts

from nwkatk.config_model import (
    NoExtraBaseModel,
    EnvExpand,
    EnvSecretStr,
    Credential,
    PackagedEntryPoint,
    EntryPointImportPath,
    ImportPath,
    FilePathEnvExpand,
)

from nwkatk_netmon.collectors import CollectorType, CollectorConfigModel
from nwkatk_netmon.drivers import DriverBase


class DefaultCredential(Credential, BaseSettings):
    username: EnvExpand
    password: EnvSecretStr


class DefaultsModel(NoExtraBaseModel, BaseSettings):
    interval: Optional[PositiveInt] = Field(default=consts.DEFAULT_INTERVAL)
    inventory: FilePathEnvExpand
    credentials: DefaultCredential
    exporters: Optional[List[str]]


class DeviceDriverModel(NoExtraBaseModel):
    driver: Optional[Type[DriverBase]]
    use: Optional[Type[DriverBase]]
    modules: List[ImportPath]

    @validator("driver", pre=True)
    def _from_driver_to_callable(cls, val):
        return EntryPointImportPath.validate(val)

    @validator("use", pre=True)
    def _from_use_to_callable(cls, val):
        driver = PackagedEntryPoint.validate(val)
        return driver

    @root_validator
    def normalize_driver(cls, values):
        driver = values["driver"] = first(itemgetter("driver", "use")(values))
        if not driver:
            raise ValueError("Missing one of ['driver', 'use']")
        return values


class CollectorModel(NoExtraBaseModel):
    use: Optional[Type[CollectorType]]
    collector: Optional[Type[CollectorType]]
    config: Optional[CollectorConfigModel]

    @validator("use", pre=True)
    def _from_use_to_callable(cls, val):
        return PackagedEntryPoint.validate(val)

    @validator("collector", pre=True, always=True)
    def _from_collector_to_callable(cls, val, values):
        return EntryPointImportPath.validate(val) if val else values["use"]

    @validator("config", pre=True, always=True)
    def _xform_config_to_obj(cls, val, values):
        return values["collector"].config.parse_obj(val or {})


class ExporterModel(NoExtraBaseModel):
    exporter: Optional[Type]
    use: Optional[Callable]
    config: Optional[Dict]

    @validator("use", pre=True)
    def _from_use_to_callable(cls, val):
        return PackagedEntryPoint.validate(val)

    @root_validator
    def normalize_exporter(cls, values):
        start = values["exporter"] = first(itemgetter("exporter", "use")(values))
        if not start:
            raise ValueError("Missing one of ['exporter', 'use']")
        return values


class ConfigModel(NoExtraBaseModel):
    defaults: DefaultsModel
    device_drivers: Dict[str, DeviceDriverModel]
    collectors: Dict[str, CollectorModel]
    exporters: Dict[str, ExporterModel]

    @validator("exporters")
    def init_exporters(cls, exporters):
        for e_name, e_val in exporters.items():
            e_cls = e_val.exporter
            e_cfg_model = e_cls.config
            e_val.config = e_cfg_model.validate(e_val.config)
            e_inst = e_cls(e_name)
            e_inst.prepare(e_val.config)
            exporters[e_name] = e_inst

        return exporters
