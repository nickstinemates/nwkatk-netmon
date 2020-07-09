import toml
from functools import lru_cache
from contextvars import ContextVar              # noqa


from nwkatk.config_model import config_validation_errors

from .config_model import ConfigModel, ValidationError


_config = ContextVar("config")


def load_config_file(ctx, param, value):
    """ click option callback for processing the config option """
    try:
        config_data = toml.load(value)
        config_obj = ConfigModel.parse_obj(config_data)

    except ValidationError as exc:
        raise RuntimeError(
            config_validation_errors(errors=exc.errors(), filepath=value.name)
        )

    _config.set(config_obj)
    return config_obj


@lru_cache
def get_config():
    return _config.get()


# @lru_cache
# def get_driver(import_path):
#     try:
#         return EntryPoint.parse(f"device = {import_path}").resolve()
#
#     except Exception as exc:
#         breakpoint()
#         x = 2
#
#
# @lru_cache
# def get_collector_entry_point(import_path):
#     try:
#         return EntryPoint.parse(f"ep = {import_path}").resolve()
#
#     except Exception as exc:
#         breakpoint()
#         x = 2
