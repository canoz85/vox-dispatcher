import logging
import paho.mqtt.client as mqtt

from logging_config import log_extra

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, broker: str, port: int = 1883, client_id: str = ""):
        self.broker = broker
        self.port = port
        self._client = mqtt.Client(client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._message_callbacks: dict[str, list] = {}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, username: str = None, password: str = None,
                keepalive: int = 60) -> None:
        if username:
            self._client.username_pw_set(username, password)
        self._client.connect(self.broker, self.port, keepalive)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    # ------------------------------------------------------------------
    # Publish / Subscribe
    # ------------------------------------------------------------------

    def publish(self, topic: str, payload, qos: int = 0,
                retain: bool = False) -> None:
        # logger.debug(
        #     "topic=%s payload=%s",
        #     topic,
        #     payload,
        #     extra=log_extra("MQTT PUB"),
        # )
        result = self._client.publish(topic, payload, qos=qos, retain=retain)
        # logger.debug(
        #     "rc=%s mid=%s",
        #     result.rc,
        #     result.mid,
        #     extra=log_extra("MQTT ACK"),
        # )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("Publish failed rc=%s topic=%s", result.rc, topic)


    def subscribe(self, topic: str, callback, qos: int = 0) -> None:
        self._message_callbacks.setdefault(topic, []).append(callback)
        self._client.subscribe(topic, qos)
        logger.debug(
            "topic=%s qos=%s",
            topic,
            qos,
            extra=log_extra("MQTT SUB"),
        )

    def unsubscribe(self, topic: str) -> None:
        self._client.unsubscribe(topic)
        self._message_callbacks.pop(topic, None)
        logger.debug(
            "topic=%s",
            topic,
            extra=log_extra("MQTT UNSUB"),
        )

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            logger.info(
                "broker=%s port=%s",
                self.broker,
                self.port,
                extra=log_extra("MQTT CONNECT"),
            )
            # Re-subscribe on reconnect
            for topic in self._message_callbacks:
                client.subscribe(topic)
        else:
            logger.error("Connection failed with code %s", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        logger.warning(
            "rc=%s",
            rc,
            extra=log_extra("MQTT DISCONNECT"),
        )

    def _on_message(self, client, userdata, message) -> None:
        topic = message.topic
        # logger.debug(
        #     "topic=%s payload=%s",
        #     topic,
        #     message.payload.decode(errors="replace"),
        #     extra=log_extra("MQTT RECV"),
        # )
        # Use snapshots because callbacks may subscribe/unsubscribe topics.
        for registered_topic, callbacks in list(self._message_callbacks.items()):
            if mqtt.topic_matches_sub(registered_topic, topic):
                for cb in list(callbacks):
                    try:
                        cb(topic, message.payload)
                    except Exception:
                        logger.exception(
                            "Unhandled exception in message callback for topic %s",
                            topic,
                        )

    def _on_publish(self, client, userdata, mid) -> None:
        # logger.debug(
        #     "mid=%s",
        #     mid,
        #     extra=log_extra("MQTT PUBLISHED"),
        # )
        pass
