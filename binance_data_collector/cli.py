# coding=utf-8
__all__ = ["cli"]

import json
import logging
import time
from pathlib import Path
from typing import Optional, Any

import click
import schedule

from binance_data_collector.collectors import (
    BinanceStreamDataCollector,
    BinanceSnapshotDataCollector,
)
from binance_data_collector.compressors import BufferCompressor
from binance_data_collector.currency_pair import CurrencyPair
from binance_data_collector.json_formatter import JsonFormatter


def parse_config_file(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text())

    config["currency_pairs"] = [
        CurrencyPair(base=c["base"], quote=c["quote"])
        for c in config["currency_pairs"]
    ]

    config["buffers_root"] = Path(config["buffers_root"])
    config["compressed_root"] = Path(config["compressed_root"])

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
@click.argument("config_file", type=Path, help="Path to a config.json file.")
def updates(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    BinanceStreamDataCollector(
        buffers_root=config["buffers_root"],
        channel="depth@100ms",
        currency_pairs=config["currency_pairs"],
    ).run()


@cli.command()
@click.argument("config_file", type=Path, help="Path to a config.json file.")
def trades(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    BinanceStreamDataCollector(
        buffers_root=config["buffers_root"],
        channel="trade",
        currency_pairs=config["currency_pairs"],
    ).run()


@cli.command()
@click.argument("config_file", type=Path, help="Path to a config.json file.")
def snapshots(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    BinanceSnapshotDataCollector(
        buffers_root=config["buffers_root"],
        depth=config["depth"],
        currency_pairs=config["currency_pairs"]
    ).run()


@cli.command()
@click.argument("config_file", type=Path, help="Path to a config.json file.")
def compress_buffers(config_file: Path) -> None:
    config: dict[str, Any] = parse_config_file(path=config_file)

    bc = BufferCompressor(
        buffers_root=config["buffers_root"],
        compressed_root=config["compressed_root"],
    )

    schedule.every().day.at("00:01").do(bc.run)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logging.exception(e)

        time.sleep(1)
