# coding=utf-8
__all__ = ["cli"]

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Any

import click
import schedule

from binance_data_collector_old.collectors import (
    BinanceStreamDataCollector,
    BinanceSnapshotDataCollector,
)
from binance_data_collector.app.models.currency_pair import CurrencyPair
from binance_data_collector_old.data_file_manager import create_data_file_manager
from binance_data_collector_old.exit_handler import ExitHandler
from log.json_formatter import JsonFormatter


def parse_config_file(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text())

    config["currency_pairs"] = [
        CurrencyPair(base=c["base"], quote=c["quote"])
        for c in config["currency_pairs"]
    ]

    config["data_root"] = Path(config["data_root"])
    config["depth"] = int(config["depth"])
    config["snapshot_frequency"] = int(config["snapshot_frequency"])

    return config


@click.group()
@click.option("--log-file", type=Path, help="Log to this path.")
@click.option("--debug", type=bool, is_flag=True, help="Use debug logging.")
@click.version_option()
def cli(debug: bool = False, log_file: Optional[Path] = None) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        filename=log_file,
    )

    logger: logging.Logger = logging.getLogger()
    logger.handlers[0].setFormatter(
        JsonFormatter(
            fields=["levelname", "name", "message", "exc_info"],
            rename_fields={"levelname": "log.level", "name": "log.logger"},
        )
    )


@cli.command()
@click.argument("config_file", type=Path)
def updates(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    with create_data_file_manager(path=config["data_root"], name="updates") as data_file_manager:
        BinanceStreamDataCollector(
            data_file_manager=data_file_manager,
            channel="depth@100ms",
            currency_pairs=config["currency_pairs"],
        ).run()


@cli.command()
@click.argument("config_file", type=Path)
def trades(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    with create_data_file_manager(path=config["data_root"], name="trades") as data_file_manager:
        collector: BinanceStreamDataCollector = BinanceStreamDataCollector(
            data_file_manager=data_file_manager,
            channel="trade",
            currency_pairs=config["currency_pairs"],
        )

        thread: threading.Thread = threading.Thread(target=collector.run)

        thread.start()

        while ExitHandler.ok():
            try:
                time.sleep(1)
            except Exception as e:
                logging.exception(e)


@cli.command()
@click.argument("config_file", type=Path)
def snapshots(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    with create_data_file_manager(path=config["data_root"], name="snapshots") as data_file_manager:
        collector: BinanceSnapshotDataCollector = BinanceSnapshotDataCollector(
            data_file_manager=data_file_manager,
            depth=config["depth"],
            currency_pairs=config["currency_pairs"]
        )

        collector.run()

        schedule.every().minute.do(collector.run)

        while ExitHandler.ok():
            try:
                schedule.run_pending()

                time.sleep(1)
            except Exception as e:
                logging.exception(e)
