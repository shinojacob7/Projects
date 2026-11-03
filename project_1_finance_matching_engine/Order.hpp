#pragma once
#include <string>
#include <chrono>
#include <cstdint>
#include <iostream>

namespace trading {

enum class Side { BUY, SELL };
enum class OrderType { LIMIT, MARKET };
enum class OrderStatus { NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED };

struct Order {
    uint64_t id;
    std::string symbol;
    Side side;
    OrderType type;
    double price;
    uint32_t totalQuantity;
    uint32_t filledQuantity;
    uint64_t timestamp; // nanoseconds since epoch
    OrderStatus status;

    Order(uint64_t id_, std::string symbol_, Side side_, OrderType type_, double price_, uint32_t qty_)
        : id(id_), symbol(std::move(symbol_)), side(side_), type(type_),
          price(price_), totalQuantity(qty_), filledQuantity(0),
          status(OrderStatus::NEW) {
        timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }

    uint32_t remainingQuantity() const {
        return totalQuantity - filledQuantity;
    }
};

struct Trade {
    uint64_t tradeId;
    std::string symbol;
    uint64_t buyOrderId;
    uint64_t sellOrderId;
    double price;
    uint32_t quantity;
    uint64_t timestamp;

    Trade(uint64_t id, std::string sym, uint64_t bId, uint64_t sId, double p, uint32_t q)
        : tradeId(id), symbol(std::move(sym)), buyOrderId(bId), sellOrderId(sId), price(p), quantity(q) {
        timestamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }
};

} // namespace trading
