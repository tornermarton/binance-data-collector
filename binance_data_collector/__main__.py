# coding=utf-8
import logging

from binance_data_collector.cli import cli


def main() -> None:
    try:
        cli()
    except Exception as e:
        logging.critical(e, exc_info=e)


if __name__ == '__main__':
    main()
