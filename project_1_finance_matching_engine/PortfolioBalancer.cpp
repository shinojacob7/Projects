#include "PortfolioBalancer.hpp"
#include <cmath>
#include <iostream>

namespace trading {

PortfolioBalancer::PortfolioBalancer(double initialCash) : cash_(initialCash) {}

void PortfolioBalancer::setTargetWeight(const std::string& symbol, double targetWeight) {
    targetWeights_[symbol] = targetWeight;
}

void PortfolioBalancer::updateMarketPrice(const std::string& symbol, double price) {
    marketPrices_[symbol] = price;
}

void PortfolioBalancer::executeTrade(const Trade& trade, Side executedSide) {
    double tradeCost = trade.price * trade.quantity;
    Position& pos = positions_[trade.symbol];
    pos.symbol = trade.symbol;

    if (executedSide == Side::BUY) {
        cash_ -= tradeCost;
        pos.costBasis += tradeCost;
        pos.quantity += trade.quantity;
    } else {
        // SELL
        cash_ += tradeCost;
        if (pos.quantity > 0) {
            double avgCost = pos.costBasis / pos.quantity;
            double costSold = avgCost * trade.quantity;
            pos.realizedPnL += (tradeCost - costSold);
            pos.costBasis -= costSold;
            pos.quantity -= trade.quantity;
        }
    }
}

double PortfolioBalancer::getTotalPortfolioValue() const {
    double total = cash_;
    for (const auto& kv : positions_) {
        const std::string& symbol = kv.first;
        const Position& pos = kv.second;
        auto it = marketPrices_.find(symbol);
        double price = (it != marketPrices_.end()) ? it->second : (pos.quantity > 0 ? pos.costBasis / pos.quantity : 0.0);
        total += pos.quantity * price;
    }
    return total;
}

double PortfolioBalancer::getRealizedPnL() const {
    double totalRealized = 0.0;
    for (const auto& kv : positions_) {
        totalRealized += kv.second.realizedPnL;
    }
    return totalRealized;
}

double PortfolioBalancer::getUnrealizedPnL() const {
    double totalUnrealized = 0.0;
    for (const auto& kv : positions_) {
        const std::string& symbol = kv.first;
        const Position& pos = kv.second;
        if (pos.quantity > 0) {
            auto it = marketPrices_.find(symbol);
            if (it != marketPrices_.end()) {
                double currentVal = pos.quantity * it->second;
                totalUnrealized += (currentVal - pos.costBasis);
            }
        }
    }
    return totalUnrealized;
}

std::unordered_map<std::string, double> PortfolioBalancer::getCurrentWeights() const {
    double totalVal = getTotalPortfolioValue();
    std::unordered_map<std::string, double> weights;
    if (totalVal <= 0.0) return weights;

    for (const auto& kv : positions_) {
        const std::string& symbol = kv.first;
        const Position& pos = kv.second;
        auto it = marketPrices_.find(symbol);
        double price = (it != marketPrices_.end()) ? it->second : 0.0;
        weights[symbol] = (pos.quantity * price) / totalVal;
    }
    return weights;
}

std::vector<Order> PortfolioBalancer::generateRebalanceOrders(double toleranceThreshold) {
    std::vector<Order> orders;
    double totalVal = getTotalPortfolioValue();
    if (totalVal <= 0.0) return orders;

    auto currentWeights = getCurrentWeights();

    for (const auto& kv : targetWeights_) {
        const std::string& symbol = kv.first;
        double targetWeight = kv.second;
        double currentWeight = currentWeights[symbol]; // defaults to 0.0 if not present
        double weightDiff = targetWeight - currentWeight;

        if (std::abs(weightDiff) > toleranceThreshold) {
            double targetValueDelta = weightDiff * totalVal;
            auto priceIt = marketPrices_.find(symbol);
            if (priceIt == marketPrices_.end() || priceIt->second <= 0.0) {
                continue;
            }

            double price = priceIt->second;
            int32_t qtyDelta = static_cast<int32_t>(targetValueDelta / price);

            if (qtyDelta > 0) {
                // Buy order
                orders.emplace_back(
                    nextOrderId_++,
                    symbol,
                    Side::BUY,
                    OrderType::LIMIT,
                    price,
                    static_cast<uint32_t>(qtyDelta)
                );
            } else if (qtyDelta < 0) {
                // Sell order
                uint32_t sellQty = static_cast<uint32_t>(-qtyDelta);
                auto posIt = positions_.find(symbol);
                if (posIt != positions_.end() && posIt->second.quantity > 0) {
                    sellQty = std::min(sellQty, posIt->second.quantity);
                    if (sellQty > 0) {
                        orders.emplace_back(
                            nextOrderId_++,
                            symbol,
                            Side::SELL,
                            OrderType::LIMIT,
                            price,
                            sellQty
                        );
                    }
                }
            }
        }
    }

    return orders;
}

const Position* PortfolioBalancer::getPosition(const std::string& symbol) const {
    auto it = positions_.find(symbol);
    if (it != positions_.end()) {
        return &(it->second);
    }
    return nullptr;
}

} // namespace trading
