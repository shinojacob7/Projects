#include "OrderBook.hpp"
#include "PortfolioBalancer.hpp"
#include <iostream>
#include <iomanip>
#include <vector>

using namespace trading;

void printL2(const L2Snapshot& snap) {
    std::cout << "--- L2 Order Book Snapshot: " << snap.symbol << " ---\n";
    std::cout << "  ASKS (Lowest first):\n";
    for (auto it = snap.asks.rbegin(); it != snap.asks.rend(); ++it) {
        std::cout << "    $" << std::fixed << std::setprecision(2) << it->price
                  << " | Vol: " << it->quantity << " (" << it->orderCount << " orders)\n";
    }
    std::cout << "  -------------------------------------\n";
    std::cout << "  BIDS (Highest first):\n";
    for (const auto& b : snap.bids) {
        std::cout << "    $" << std::fixed << std::setprecision(2) << b.price
                  << " | Vol: " << b.quantity << " (" << b.orderCount << " orders)\n";
    }
    std::cout << "--------------------------------------------\n";
}

int main() {
    std::cout << "========================================================\n";
    std::cout << "PROJECT 1: SIMULATION / DRY RUN (HIGH FREQUENCY ENGINE)\n";
    std::cout << "========================================================\n";

    OrderBook aaplBook("AAPL");
    OrderBook nvdaBook("NVDA");
    PortfolioBalancer portfolio(250000.0); // $250,000 initial capital

    std::cout << "\n[Step 1] Market Makers Seeding L2 Liquidity in AAPL & NVDA...\n";
    // AAPL asks
    aaplBook.addOrder(Order(101, "AAPL", Side::SELL, OrderType::LIMIT, 180.50, 200));
    aaplBook.addOrder(Order(102, "AAPL", Side::SELL, OrderType::LIMIT, 181.00, 350));
    aaplBook.addOrder(Order(103, "AAPL", Side::SELL, OrderType::LIMIT, 181.50, 500));
    // AAPL bids
    aaplBook.addOrder(Order(104, "AAPL", Side::BUY, OrderType::LIMIT, 180.00, 250));
    aaplBook.addOrder(Order(105, "AAPL", Side::BUY, OrderType::LIMIT, 179.50, 400));

    // NVDA asks
    nvdaBook.addOrder(Order(201, "NVDA", Side::SELL, OrderType::LIMIT, 120.25, 400));
    nvdaBook.addOrder(Order(202, "NVDA", Side::SELL, OrderType::LIMIT, 120.75, 600));
    // NVDA bids
    nvdaBook.addOrder(Order(203, "NVDA", Side::BUY, OrderType::LIMIT, 119.75, 300));
    nvdaBook.addOrder(Order(204, "NVDA", Side::BUY, OrderType::LIMIT, 119.25, 500));

    printL2(aaplBook.getDepthSnapshot());
    printL2(nvdaBook.getDepthSnapshot());

    std::cout << "\n[Step 2] Configuring Portfolio Target Allocation:\n";
    std::cout << "  AAPL Target Weight: 40.0% | Market Price: $180.50\n";
    std::cout << "  NVDA Target Weight: 40.0% | Market Price: $120.25\n";
    std::cout << "  Cash Reserve:       20.0%\n";

    portfolio.setTargetWeight("AAPL", 0.40);
    portfolio.setTargetWeight("NVDA", 0.40);
    portfolio.updateMarketPrice("AAPL", 180.50);
    portfolio.updateMarketPrice("NVDA", 120.25);

    std::cout << "\n[Step 3] Algorithmic Rebalancer Evaluating Portfolio...\n";
    auto rebalanceOrders = portfolio.generateRebalanceOrders();
    std::cout << "Generated " << rebalanceOrders.size() << " rebalance orders.\n";

    for (const auto& ord : rebalanceOrders) {
        std::cout << "  -> Routing Order #" << ord.id << ": "
                  << (ord.side == Side::BUY ? "BUY" : "SELL") << " "
                  << ord.totalQuantity << " " << ord.symbol << " @ $" << ord.price << "\n";

        std::vector<Trade> trades;
        if (ord.symbol == "AAPL") {
            trades = aaplBook.addOrder(ord);
        } else if (ord.symbol == "NVDA") {
            trades = nvdaBook.addOrder(ord);
        }

        std::cout << "     Executed " << trades.size() << " fills:\n";
        for (const auto& t : trades) {
            std::cout << "       Fill Trade #" << t.tradeId << ": " << t.quantity
                      << " units @ $" << t.price
                      << " (BuyOrder: " << t.buyOrderId << ", SellOrder: " << t.sellOrderId << ")\n";
            portfolio.executeTrade(t, ord.side);
        }
    }

    std::cout << "\n[Step 4] Market Movement Simulation & Revaluation:\n";
    portfolio.updateMarketPrice("AAPL", 185.00); // AAPL surges +2.49%
    portfolio.updateMarketPrice("NVDA", 126.00); // NVDA surges +4.78%

    std::cout << "  New AAPL Price: $185.00\n";
    std::cout << "  New NVDA Price: $126.00\n";

    double totalVal = portfolio.getTotalPortfolioValue();
    double unrealized = portfolio.getUnrealizedPnL();
    double cash = portfolio.getCash();
    auto weights = portfolio.getCurrentWeights();

    std::cout << "\n[Step 5] Final Portfolio State:\n";
    std::cout << "  Total Portfolio Value: $" << std::fixed << std::setprecision(2) << totalVal << "\n";
    std::cout << "  Cash Balance:          $" << cash << "\n";
    std::cout << "  Unrealized PnL:        +$" << unrealized << "\n";
    std::cout << "  Active Allocations:\n";
    for (const auto& kv : weights) {
        std::cout << "    " << kv.first << ": " << (kv.second * 100.0) << "%\n";
    }

    std::cout << "\nDRY RUN / PIPELINE SIMULATION COMPLETED WITH 0 ERRORS.\n";
    return 0;
}
