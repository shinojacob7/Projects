# Ultra-Low Latency Order Matching Engine & Algorithmic Portfolio Balancer (C++)

## High-Impact Resume Bullets
* Engineered a high-throughput, price-time priority (FIFO) in-memory Limit Order Book (LOB) in modern C++ supporting sub-microsecond limit/market order execution and Level 2 (L2) market depth generation.
* Architected a lock-free/spin-lock synchronized multi-symbol trading core with fast cancellation and $O(1)$ order index tracking.
* Designed an automated portfolio balancer computing real-time drift vs. target allocation models, generating optimal limit rebalance orders and tracking realized/unrealized PnL.
* Validated with 100% passing unit test suites and an end-to-end multi-symbol market maker liquidity sweep simulation.
