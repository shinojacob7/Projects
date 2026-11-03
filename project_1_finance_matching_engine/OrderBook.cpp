#include "OrderBook.hpp"
#include <algorithm>
#include <limits>

namespace trading {

OrderBook::OrderBook(std::string symbol) : symbol_(std::move(symbol)) {}

std::vector<Trade> OrderBook::addOrder(Order order) {
    SpinLockGuard lock(bookLock_);
    if (order.symbol != symbol_ || order.remainingQuantity() == 0) {
        return {};
    }

    if (order.side == Side::BUY) {
        return matchBuyOrder(order);
    } else {
        return matchSellOrder(order);
    }
}

std::vector<Trade> OrderBook::matchBuyOrder(Order& buyOrder) {
    std::vector<Trade> trades;

    while (buyOrder.remainingQuantity() > 0 && !asks_.empty()) {
        auto bestAskIt = asks_.begin();
        double bestAskPrice = bestAskIt->first;

        if (buyOrder.type == OrderType::LIMIT && buyOrder.price < bestAskPrice) {
            break; // Limit price does not cross spread
        }

        auto& queue = bestAskIt->second;
        while (!queue.empty() && buyOrder.remainingQuantity() > 0) {
            Order& sellOrder = queue.front();
            uint32_t matchQty = std::min(buyOrder.remainingQuantity(), sellOrder.remainingQuantity());

            buyOrder.filledQuantity += matchQty;
            sellOrder.filledQuantity += matchQty;

            trades.emplace_back(
                nextTradeId_++,
                symbol_,
                buyOrder.id,
                sellOrder.id,
                bestAskPrice,
                matchQty
            );

            if (sellOrder.remainingQuantity() == 0) {
                sellOrder.status = OrderStatus::FILLED;
                orderIndex_.erase(sellOrder.id);
                queue.pop_front();
            } else {
                sellOrder.status = OrderStatus::PARTIALLY_FILLED;
            }
        }

        if (queue.empty()) {
            asks_.erase(bestAskIt);
        }
    }

    if (buyOrder.remainingQuantity() > 0) {
        if (buyOrder.type == OrderType::LIMIT) {
            buyOrder.status = (buyOrder.filledQuantity > 0) ? OrderStatus::PARTIALLY_FILLED : OrderStatus::NEW;
            orderIndex_[buyOrder.id] = {buyOrder.price, Side::BUY};
            bids_[buyOrder.price].push_back(buyOrder);
        } else {
            buyOrder.status = (buyOrder.filledQuantity > 0) ? OrderStatus::PARTIALLY_FILLED : OrderStatus::REJECTED;
        }
    } else {
        buyOrder.status = OrderStatus::FILLED;
    }

    return trades;
}

std::vector<Trade> OrderBook::matchSellOrder(Order& sellOrder) {
    std::vector<Trade> trades;

    while (sellOrder.remainingQuantity() > 0 && !bids_.empty()) {
        auto bestBidIt = bids_.begin();
        double bestBidPrice = bestBidIt->first;

        if (sellOrder.type == OrderType::LIMIT && sellOrder.price > bestBidPrice) {
            break; // Limit price does not cross spread
        }

        auto& queue = bestBidIt->second;
        while (!queue.empty() && sellOrder.remainingQuantity() > 0) {
            Order& buyOrder = queue.front();
            uint32_t matchQty = std::min(sellOrder.remainingQuantity(), buyOrder.remainingQuantity());

            sellOrder.filledQuantity += matchQty;
            buyOrder.filledQuantity += matchQty;

            trades.emplace_back(
                nextTradeId_++,
                symbol_,
                buyOrder.id,
                sellOrder.id,
                bestBidPrice,
                matchQty
            );

            if (buyOrder.remainingQuantity() == 0) {
                buyOrder.status = OrderStatus::FILLED;
                orderIndex_.erase(buyOrder.id);
                queue.pop_front();
            } else {
                buyOrder.status = OrderStatus::PARTIALLY_FILLED;
            }
        }

        if (queue.empty()) {
            bids_.erase(bestBidIt);
        }
    }

    if (sellOrder.remainingQuantity() > 0) {
        if (sellOrder.type == OrderType::LIMIT) {
            sellOrder.status = (sellOrder.filledQuantity > 0) ? OrderStatus::PARTIALLY_FILLED : OrderStatus::NEW;
            orderIndex_[sellOrder.id] = {sellOrder.price, Side::SELL};
            asks_[sellOrder.price].push_back(sellOrder);
        } else {
            sellOrder.status = (sellOrder.filledQuantity > 0) ? OrderStatus::PARTIALLY_FILLED : OrderStatus::REJECTED;
        }
    } else {
        sellOrder.status = OrderStatus::FILLED;
    }

    return trades;
}

bool OrderBook::cancelOrder(uint64_t orderId) {
    SpinLockGuard lock(bookLock_);
    auto it = orderIndex_.find(orderId);
    if (it == orderIndex_.end()) {
        return false;
    }

    double price = it->second.price;
    Side side = it->second.side;
    orderIndex_.erase(it);

    if (side == Side::BUY) {
        auto priceIt = bids_.find(price);
        if (priceIt != bids_.end()) {
            auto& q = priceIt->second;
            for (auto qIt = q.begin(); qIt != q.end(); ++qIt) {
                if (qIt->id == orderId) {
                    qIt->status = OrderStatus::CANCELLED;
                    q.erase(qIt);
                    break;
                }
            }
            if (q.empty()) {
                bids_.erase(priceIt);
            }
            return true;
        }
    } else {
        auto priceIt = asks_.find(price);
        if (priceIt != asks_.end()) {
            auto& q = priceIt->second;
            for (auto qIt = q.begin(); qIt != q.end(); ++qIt) {
                if (qIt->id == orderId) {
                    qIt->status = OrderStatus::CANCELLED;
                    q.erase(qIt);
                    break;
                }
            }
            if (q.empty()) {
                asks_.erase(priceIt);
            }
            return true;
        }
    }

    return false;
}

double OrderBook::getBestBid() const {
    SpinLockGuard lock(bookLock_);
    if (bids_.empty()) return 0.0;
    return bids_.begin()->first;
}

double OrderBook::getBestAsk() const {
    SpinLockGuard lock(bookLock_);
    if (asks_.empty()) return std::numeric_limits<double>::infinity();
    return asks_.begin()->first;
}

double OrderBook::getSpread() const {
    SpinLockGuard lock(bookLock_);
    if (bids_.empty() || asks_.empty()) return -1.0;
    return asks_.begin()->first - bids_.begin()->first;
}

L2Snapshot OrderBook::getDepthSnapshot(size_t maxLevels) const {
    SpinLockGuard lock(bookLock_);
    L2Snapshot snapshot;
    snapshot.symbol = symbol_;

    size_t count = 0;
    for (auto it = bids_.begin(); it != bids_.end(); ++it) {
        if (count++ >= maxLevels) break;
        double price = it->first;
        const auto& queue = it->second;
        uint32_t qty = 0;
        for (const auto& ord : queue) qty += ord.remainingQuantity();
        snapshot.bids.push_back({price, qty, static_cast<uint32_t>(queue.size())});
    }

    count = 0;
    for (auto it = asks_.begin(); it != asks_.end(); ++it) {
        if (count++ >= maxLevels) break;
        double price = it->first;
        const auto& queue = it->second;
        uint32_t qty = 0;
        for (const auto& ord : queue) qty += ord.remainingQuantity();
        snapshot.asks.push_back({price, qty, static_cast<uint32_t>(queue.size())});
    }

    return snapshot;
}

size_t OrderBook::activeOrderCount() const {
    SpinLockGuard lock(bookLock_);
    return orderIndex_.size();
}

} // namespace trading
