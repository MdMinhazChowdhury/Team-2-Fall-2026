# Performance workload

Run `pytest tests/performance` with the shared explicit PostgreSQL test URL. The workload seeds ten private accounts with 500 tasks each and measures retrieval/update requests from ten simultaneous ASGI clients. The recorded JSON includes request count, page size, median/p95/max and transport limitations. It excludes network/proxy and is not a production capacity claim.
