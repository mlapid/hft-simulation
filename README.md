# Pet Project On HFT Simulation

The project implements a simulation of algorithmic trading (without actual trading) on real-time data.

The project includes:
- receiving data via the exchange's WebSocket,
- data analysis in PySpark and generating a trading signal,
- building a MongoDB storage for data retention,
- [trading simulation](https://www.investopedia.com/terms/p/papertrade.asp) on real-time data,
- visualization of logs and the trading simulation results in Grafana.

![Architecture](docs/Architecture.svg)

See [Wiki](https://github.com/mlapid-ya/hft-simulation/wiki) for further details

# About The Project

This project uses open data from the [Deribit websocket](https://docs.deribit.com/?python#json-rpc-over-websocket) as a source.

In particular, data on [Limit Order Book](https://en.wikipedia.org/wiki/Central_limit_order_book) is used - [API link](https://docs.deribit.com/?python#public-get_order_book_by_instrument_id).

## Services

There are 3 main services:
- Exchange Connector
- Processing Engine
- Execution Engine

### Exchange Connector

Responsible for:
1. Getting market data from an exchange.
2. Normalising the data schema.
3. Saving data in MongoDB.
4. Sending data to Redis for the Processing Engine.
5. Visualising the status in Grafana.

### Processing Engine

### Execution Engine

# Usage

```bash
docker compose up -d --build
```

## Testing

```bash
uv run pytest
```

## Type Checking

```bash
uv run ty check
```

# Roadmap

- [x] Exchange Connector
- [ ] Processing Engine
- [ ] Execution Engine
  - [ ] Trading Simulator
  - [ ] P/L Calculation
     
# Built With

* [![Python][Python]][Python-url]
* [![Redis][Redis]][Redis-url]
* [![MongoDB][MongoDB]][MongoDB-url]
* [![Grafana][Grafana]][Grafana-url]

[Python]: https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff
[Python-url]: https://www.python.org/
[Redis]: https://img.shields.io/badge/Redis-%23DD0031.svg?logo=redis&logoColor=white
[Redis-url]: https://redis.io/
[MongoDB]: https://img.shields.io/badge/MongoDB-%234ea94b.svg?logo=mongodb&logoColor=white
[MongoDB-url]: https://www.mongodb.com/
[Grafana]: https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=fff
[Grafana-url]: https://grafana.com/