# coding=utf-8
__all__ = ["cli"]

import logging.config
import typing
from pathlib import Path

import click
from ruamel.yaml import YAML

from binance_data_collector.api import Application

from binance_data_collector.app.app_module import AppModule
from binance_data_collector.log import DEFAULT_LOGGING_CONFIG


def parse_config_file(path: Path) -> None:
    config: dict[str, typing.Any] = YAML().load(path.read_text())
    logging.config.dictConfig(config=config["logging"])


@click.group()
@click.option("--config", type=Path, help="Path to logging config.")
@click.option("--debug", type=bool, is_flag=True, help="Use debug logging.")
@click.version_option()
def cli(config: typing.Optional[Path] = None, debug: bool = False) -> None:
    logger: logging.Logger = logging.getLogger()

    if config is not None and config.exists():
        parse_config_file(path=config)
    else:
        logging.config.dictConfig(config=YAML().load(DEFAULT_LOGGING_CONFIG))

    if debug:
        logger.setLevel(level=logging.DEBUG)


@cli.command()
def start() -> None:
    app: Application = Application(AppModule)

    app.listen(port=3000)
