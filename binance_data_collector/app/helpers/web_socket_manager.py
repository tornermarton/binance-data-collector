# coding=utf-8
import dataclasses
import enum
import logging
import threading
import typing
import uuid

from autobahn.twisted import websocket
from twisted.internet import protocol, reactor
from twisted.internet.interfaces import IAddress, IConnector


try:
    import ujson as json
except ImportError:
    import json

from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.api import Injectable
from binance_data_collector.log import LoggingMixin, get_logger_for
from binance_data_collector.rxpy import Observable, Observer, Subject, Subscription


@dataclasses.dataclass(frozen=True)
class WebSocketMessage(object):
    symbol: str
    channel: str
    data: dict[str, typing.Any]


class WebSocketEventType(enum.Enum):
    CONNECTED = enum.auto()
    CONTROL_MESSAGE = enum.auto()
    DISCONNECTED = enum.auto()


@dataclasses.dataclass(frozen=True)
class WebSocketEvent(object):
    type: WebSocketEventType
    context: dict[str, typing.Any] | None = None


class WebSocketClientProtocol(websocket.WebSocketClientProtocol):
    def __init__(self) -> None:
        super().__init__()

        self._message: Subject[WebSocketMessage] = Subject()
        self._event: Subject[WebSocketEvent] = Subject()

        # self.log is already defined in parent
        self._logger: logging.Logger = get_logger_for(
            cls=WebSocketClientProtocol,
        )

    @property
    def messages(self) -> Observable[WebSocketMessage]:
        return self._message.as_observable()

    @property
    def events(self) -> Observable[WebSocketEvent]:
        return self._event.as_observable()

    def send_message(self, message: dict[str, typing.Any]) -> None:
        self.sendMessage(payload=json.dumps(message).encode(encoding="utf-8"))

    def _init_tcp_keepalive(self) -> None:
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError:
            self._logger.warning("AttributeError silenced at TCP keepalive")

    def _process_payload(self, payload: bytes) -> None:
        try:
            message: dict[str, typing.Any] = json.loads(payload.decode("utf-8"))

            self._logger.debug(f"Message received: {message}")

            if "stream" in message:
                symbol, channel, *_ = message["stream"].split('@')

                self._message.next(
                    value=WebSocketMessage(
                        symbol=symbol,
                        channel=channel,
                        data=message,
                    ),
                )

                self._logger.debug("Message processed.")
            elif "result" in message and message["result"] is None:
                self._event.next(
                    value=WebSocketEvent(
                        type=WebSocketEventType.CONTROL_MESSAGE,
                        context={"id": message["id"]}
                    ),
                )
            else:
                self._logger.warning(f"Unexpected message: {message}")
        except Exception as e:
            self._logger.exception(f"Could not process payload.", exc_info=e)

    def connectionMade(self) -> None:
        super().connectionMade()

        self._init_tcp_keepalive()

        self._logger.info("WebSocket connected!")

        self._event.next(
            value=WebSocketEvent(type=WebSocketEventType.CONNECTED),
        )

    def onClose(self, wasClean: bool, code: int, reason: typing.Any) -> None:
        self._logger.info(
            f"WebSocket disconnected (code: {code}, reason: {reason})!"
        )

        self._event.next(
            value=WebSocketEvent(type=WebSocketEventType.DISCONNECTED),
        )

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if not isBinary:
            self._process_payload(payload=payload)


class WebSocketClientFactory(
    websocket.WebSocketClientFactory,
    protocol.ReconnectingClientFactory
):
    initialDelay: float = 0.1
    maxDelay: int = 60
    # None means never stop trying to reconnect
    maxRetries: int = None

    protocol: websocket.WebSocketClientProtocol = WebSocketClientProtocol

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)

        self._message: Subject[WebSocketMessage] = Subject()
        self._event: Subject[WebSocketEvent] = Subject()

        self._protocol_instance: WebSocketClientProtocol | None = None
        self._subscriptions: list[Subscription] = []

        self.setProtocolOptions(autoPingInterval=300, autoPingTimeout=30)

    @property
    def messages(self) -> Observable[WebSocketMessage]:
        return self._message.as_observable()

    @property
    def events(self) -> Observable[WebSocketEvent]:
        return self._event.as_observable()

    def send_message(self, message: dict[str, typing.Any]) -> None:
        if self._protocol_instance is not None:
            self._protocol_instance.send_message(message=message)

    def _destroy_subscriptions(self) -> None:
        for subscription in self._subscriptions:
            subscription.unsubscribe()

    def buildProtocol(self, addr: IAddress) -> WebSocketClientProtocol:
        self.resetDelay()

        self._destroy_subscriptions()

        self._protocol_instance = self.protocol()
        self._protocol_instance.factory = self
        self._subscriptions.append(
            self._protocol_instance.messages.subscribe(
                on_next=lambda v: self._message.next(value=v),
            ),
        )
        self._subscriptions.append(
            self._protocol_instance.events.subscribe(
                on_next=lambda v: self._event.next(value=v)
            ),
        )

        return self._protocol_instance

    def destroy(self) -> None:
        self._protocol_instance.sendClose(code=1000)

        self._destroy_subscriptions()

        self._message.complete()
        self._event.complete()


class WebSocketConnection(object):
    def __init__(self, factory: WebSocketClientFactory) -> None:
        self._id: str = str(uuid.uuid4())
        self._factory: WebSocketClientFactory = factory

        self._connector: IConnector | None = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def factory(self) -> WebSocketClientFactory:
        return self._factory

    @property
    def messages(self) -> Observable[WebSocketMessage]:
        return self._factory.messages

    @property
    def events(self) -> Observable[WebSocketEvent]:
        return self._factory.events

    def send_message(self, message: dict[str, typing.Any]) -> None:
        self._factory.send_message(message=message)

    def open(self) -> None:
        if self._connector is not None:
            return

        self._connector = websocket.connectWS(factory=self._factory)

    def close(self) -> None:
        if self._connector is None:
            return

        self._factory.stopTrying()
        self._factory.destroy()


@Injectable()
class WebSocketManager(threading.Thread, LoggingMixin, OnInit, OnDestroy):
    def __init__(self) -> None:
        super().__init__()

        self._connections: dict[str, WebSocketConnection] = {}

    def create_connection(self, url: str) -> WebSocketConnection:
        factory: WebSocketClientFactory = WebSocketClientFactory(url=url)
        connection: WebSocketConnection = WebSocketConnection(factory=factory)

        reactor.callFromThread(connection.open)
        self._connections[connection.id] = connection

        return connection

    def delete_connection(self, connection: WebSocketConnection) -> None:
        reactor.callFromThread(connection.close)
        self._connections.pop(connection.id, None)

    def run(self) -> None:
        reactor.run(installSignalHandlers=False)

    def on_init(self) -> None:
        self.start()

    def on_destroy(self) -> None:
        for connection in list(self._connections.values()):
            self.delete_connection(connection=connection)

        reactor.callFromThread(reactor.stop)
        self.join()
