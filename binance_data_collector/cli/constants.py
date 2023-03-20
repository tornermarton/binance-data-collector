# coding=utf-8
__all__ = ["DEFAULT_LOGGING_CONFIG"]

DEFAULT_LOGGING_CONFIG = """
version: 1
disable_existing_loggers: false
root:
  level: INFO
  handlers:
    - console
handlers:
  console:
    class: logging.StreamHandler
    stream: ext://sys.stderr
    formatter: json_formatter
formatters:
  json_formatter:
    '()': binance_data_collector.log.JsonLoggingFormatter
    fields:
      - levelname
      - name
      - message
      - exc_info
    rename_fields:
      levelname: log.level
      name: log.logger
"""
