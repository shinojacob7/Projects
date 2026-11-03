#pragma once
#include "Order.hpp"
#include "OrderBook.hpp"
#include <unordered_map>
#include <vector>
#include <string>

namespace trading {

struct Position {
    std::string symbol;
    uint32_t quantity{0};
    double costBasis{0.0};
    double realizedPnL{0.0};
};

class PortfolioBalancer {
public:
    explicit PortfolioBalancer(double initialCash);

    void setTargetWeight(const std::string& symbol, double targetWeight);
    void updateMarketPrice(const std::string& symbol, double price);
    void executeTrade(const Trade& trade, Side executedSide);

    double getCash() const { return cash_; }
    double getTotalPortfolioValue() const;
    double getUnrealizedPnL() const;
    double getRealizedPnL() const;

    std::unordered_map<std::string, double> getCurrentWeights() const;
    std::vector<Order> generateRebalanceOrders(double toleranceThreshold = 0.02);

    const Position* getPosition(const std::string& symbol) const;

private:
    double cash_;
    std::unordered_map<std::string, Position> positions_;
    std::unordered_map<std::string, double> targetWeights_;
    std::unordered_map<std::string, double> marketPrices_;
    uint64_t nextOrderId_{10000};
};

} // namespace trading
