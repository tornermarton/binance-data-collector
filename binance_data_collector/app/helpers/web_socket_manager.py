# coding=utf-8
import dataclasses
import enum
import threading
import typing
import uuid

from autobahn.twisted import websocket
from twisted.internet import protocol, reactor
from twisted.internet.interfaces import IAddress, IConnector

from binance_data_collector.api.lifecycle import OnDestroy, OnInit
from binance_data_collector.app.utils import LoggingMixin

try:
    import ujson as json
except ImportError:
    import json

from binance_data_collector.api import Injectable
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


class WebSocketClientProtocol(LoggingMixin, websocket.WebSocketClientProtocol):
    def __init__(self) -> None:
        super().__init__()

        self._message: Subject[WebSocketMessage] = Subject()
        self._event: Subject[WebSocketEvent] = Subject()

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
            self.log.warning("AttributeError silenced at TCP keepalive")

    def _process_payload(self, payload: bytes) -> None:
        try:
            message: dict[str, typing.Any] = json.loads(payload.decode("utf-8"))

            self.log.debug(f"Message received: {message}")

            if "stream" in message:
                symbol, channel, *_ = message["stream"].split('@')

                self._message.next(
                    value=WebSocketMessage(
                        symbol=symbol,
                        channel=channel,
                        data=message,
                    ),
                )

                self.log.debug("Message processed.")
            elif "result" in message and message["result"] is None:
                self._event.next(
                    value=WebSocketEvent(
                        type=WebSocketEventType.CONTROL_MESSAGE,
                        context={"id": message["id"]}
                    ),
                )
            else:
                self.log.warning(f"Unexpected message: {message}")
        except Exception as e:
            self.log.exception(f"Could not process payload.", exc_info=e)

    def connectionMade(self) -> None:
        super().connectionMade()

        self._init_tcp_keepalive()

        self.log.info("WebSocket connected!")

        self._event.next(
            value=WebSocketEvent(type=WebSocketEventType.CONNECTED),
        )

    def onClose(self, wasClean: bool, code: int, reason: typing.Any) -> None:
        self.log.info(
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

    def destroy_subscription(self) -> None:
        for subscription in self._subscriptions:
            subscription.unsubscribe()

    def buildProtocol(self, addr: IAddress) -> WebSocketClientProtocol:
        self.resetDelay()

        self.destroy_subscription()

        self._protocol_instance = self.protocol()
        self._protocol_instance.factory = self
        self._subscriptions.append(
            self._protocol_instance.messages.subscribe(
                observer=Observer(
                    next=lambda message: self._message.next(value=message)
                ),
            )
        )
        self._subscriptions.append(
            self._protocol_instance.events.subscribe(
                observer=Observer(
                    next=lambda event: self._event.next(value=event)
                ),
            )
        )

        return self._protocol_instance


class WebSocketConnection(object):
    def __init__(self, factory: WebSocketClientFactory) -> None:
        self._id: str = str(uuid.uuid4())
        self._factory: WebSocketClientFactory = factory

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


@Injectable()
class WebSocketManager(threading.Thread, OnInit, OnDestroy):
    def __init__(self) -> None:
        super().__init__()

        self._connectors: dict[str, IConnector] = {}

    def _add_connection(self, connection: WebSocketConnection) -> None:
        self._connectors[connection.id] = websocket.connectWS(
            factory=connection.factory,
        )

    def create_connection(self, url: str) -> WebSocketConnection:
        connection: WebSocketConnection = WebSocketConnection(
            factory=WebSocketClientFactory(url=url),
        )

        reactor.callFromThread(self._add_connection, connection)

        return connection

    def remove_connection(self, connection: WebSocketConnection) -> None:
        connector: IConnector = self._connectors.pop(connection.id)

        connector.factory.reconnect = False
        connector.disconnect()

    def run(self) -> None:
        reactor.run(installSignalHandlers=False)

    def on_init(self) -> None:
        self.start()

    def on_destroy(self) -> None:
        for connector in self._connectors.values():
            connector.factory.reconnect = False
            connector.disconnect()

        reactor.stop()
        self.join()
