#pragma once
#include "Order.hpp"
#include <map>
#include <deque>
#include <vector>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <iomanip>

namespace trading {

// Ultra-fast low-latency spinlock for HFT matching engines
class SpinLock {
public:
    void lock() {
        while (flag_.test_and_set(std::memory_order_acquire)) {
        }
    }
    void unlock() {
        flag_.clear(std::memory_order_release);
    }
private:
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
};

class SpinLockGuard {
public:
    explicit SpinLockGuard(SpinLock& lock) : lock_(lock) {
        lock_.lock();
    }
    ~SpinLockGuard() {
        lock_.unlock();
    }
    SpinLockGuard(const SpinLockGuard&) = delete;
    SpinLockGuard& operator=(const SpinLockGuard&) = delete;
private:
    SpinLock& lock_;
};

struct LevelInfo {
    double price;
    uint32_t quantity;
    uint32_t orderCount;
};

struct L2Snapshot {
    std::string symbol;
    std::vector<LevelInfo> bids;
    std::vector<LevelInfo> asks;
};

class OrderBook {
public:
    explicit OrderBook(std::string symbol);

    std::vector<Trade> addOrder(Order order);
    bool cancelOrder(uint64_t orderId);
    
    double getBestBid() const;
    double getBestAsk() const;
    double getSpread() const;
    
    L2Snapshot getDepthSnapshot(size_t maxLevels = 5) const;
    const std::string& getSymbol() const { return symbol_; }
    size_t activeOrderCount() const;

private:
    std::string symbol_;
    uint64_t nextTradeId_{1};
    mutable SpinLock bookLock_;

    // Price -> Queue of Orders (Price-Time Priority)
    // Bids: highest price first (std::greater)
    std::map<double, std::deque<Order>, std::greater<double>> bids_;
    // Asks: lowest price first (std::less)
    std::map<double, std::deque<Order>, std::less<double>> asks_;

    // Lookup index: orderId -> (Price, Side)
    struct OrderIndex {
        double price;
        Side side;
    };
    std::unordered_map<uint64_t, OrderIndex> orderIndex_;

    std::vector<Trade> matchBuyOrder(Order& buyOrder);
    std::vector<Trade> matchSellOrder(Order& sellOrder);
};

} // namespace trading
