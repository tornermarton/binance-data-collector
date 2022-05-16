# coding=utf-8
__all__ = ["BufferCompressor"]

import dataclasses
import datetime
import logging
import multiprocessing
import os
from pathlib import Path

from binance_data_collector.file import File


def compress_file(compressed_root: Path, file: File) -> None:
    try:
        if (
            not file.path.match(f"*{datetime.date.today()}.json") and
            not file.path.match("*.gz")
        ):
            logging.debug(f"Start compressing: {file}")

            d: datetime.date = datetime.date.fromisoformat(
                file.path.stem.split("_")[1]
            )

            compressed: File = file.compress(delete_source=True)

            compressed.move(
                path=Path(
                    compressed_root,
                    compressed.path.parent.name,
                    f"{d.year}",
                    f"{d.month:02}",
                    f"{d.day:02}",
                    compressed.path.name,
                )
            )

            logging.debug(f"Compressed: {file}, result: {compressed}")
    except Exception as e:
        logging.exception(e)


@dataclasses.dataclass(frozen=True)
class BufferCompressor(object):
    buffers_root: Path
    compressed_root: Path

    def run(self) -> None:
        logging.info("Start compressing buffers...")

        _, dirs, _ = next(os.walk(self.buffers_root))
        for source_dir in [self.buffers_root / d for d in dirs]:
            for _, _, files in os.walk(source_dir):
                with multiprocessing.Pool(8) as pool:
                    pool.starmap(
                        compress_file,
                        [(self.compressed_root, File(source_dir / f)) for f in files]
                    )

        logging.info("Buffers compressed.")
