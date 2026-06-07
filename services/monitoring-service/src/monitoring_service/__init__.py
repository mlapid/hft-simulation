def main() -> None:
    print("Hello from monitoring-service!")

    # await grafana_client.send_event(
    #     channel_name=message.channel,
    #     data={
    #         'offset': message.offset,
    #         'latency': (message.timestamp + message.offset) - message.data['timestamp'],
    #         'heartbeat_age': message.heartbeat_age,
    #         'stream_length': redis_producer.stream_length
    #     },
    #     timestamp=int(message.data['timestamp'] * 1e6)
    # )