#include "OrderBook.hpp"
#include "PortfolioBalancer.hpp"
#include <iostream>
#include <cassert>
#include <cmath>

using namespace trading;

void run_test(const std::string& name, void (*func)()) {
    std::cout << "[TEST] Running: " << name << " ... ";
    func();
    std::cout << "PASSED\n";
}

void test_limit_order_placement_and_spread() {
    OrderBook book("AAPL");
    assert(book.getSpread() == -1.0); // empty book

    // Bid 150.00 qty 10
    auto trades1 = book.addOrder(Order(1, "AAPL", Side::BUY, OrderType::LIMIT, 150.00, 10));
    assert(trades1.empty());
    assert(book.getBestBid() == 150.00);

    // Ask 152.00 qty 15
    auto trades2 = book.addOrder(Order(2, "AAPL", Side::SELL, OrderType::LIMIT, 152.00, 15));
    assert(trades2.empty());
    assert(book.getBestAsk() == 152.00);

    assert(std::abs(book.getSpread() - 2.00) < 1e-6);
    assert(book.activeOrderCount() == 2);
}

void test_exact_match_execution() {
    OrderBook book("AAPL");
    book.addOrder(Order(1, "AAPL", Side::SELL, OrderType::LIMIT, 150.00, 50));

    // Buy matching exactly 50 at 150.00
    auto trades = book.addOrder(Order(2, "AAPL", Side::BUY, OrderType::LIMIT, 150.00, 50));
    assert(trades.size() == 1);
    assert(trades[0].price == 150.00);
    assert(trades[0].quantity == 50);
    assert(trades[0].buyOrderId == 2);
    assert(trades[0].sellOrderId == 1);
    assert(book.activeOrderCount() == 0);
}

void test_partial_fill_and_queue_persistence() {
    OrderBook book("AAPL");
    book.addOrder(Order(1, "AAPL", Side::SELL, OrderType::LIMIT, 100.00, 100));

    // Buy 40 at 100.00
    auto trades1 = book.addOrder(Order(2, "AAPL", Side::BUY, OrderType::LIMIT, 100.00, 40));
    assert(trades1.size() == 1);
    assert(trades1[0].quantity == 40);
    assert(book.activeOrderCount() == 1); // sell order partially filled, 60 remaining

    auto snapshot = book.getDepthSnapshot();
    assert(snapshot.asks.size() == 1);
    assert(snapshot.asks[0].quantity == 60);

    // Buy remaining 60 at 100.00
    auto trades2 = book.addOrder(Order(3, "AAPL", Side::BUY, OrderType::LIMIT, 100.00, 60));
    assert(trades2.size() == 1);
    assert(trades2[0].quantity == 60);
    assert(book.activeOrderCount() == 0);
}

void test_order_cancellation() {
    OrderBook book("AAPL");
    book.addOrder(Order(1, "AAPL", Side::BUY, OrderType::LIMIT, 145.00, 20));
    assert(book.activeOrderCount() == 1);
    assert(book.getBestBid() == 145.00);

    bool cancelled = book.cancelOrder(1);
    assert(cancelled);
    assert(book.activeOrderCount() == 0);
    assert(book.getBestBid() == 0.0);

    // Cancel non-existent
    assert(!book.cancelOrder(999));
}

void test_price_time_priority_fifo() {
    OrderBook book("GOOG");
    // Place two sells at same price 2800.00
    book.addOrder(Order(10, "GOOG", Side::SELL, OrderType::LIMIT, 2800.00, 10)); // placed first
    book.addOrder(Order(11, "GOOG", Side::SELL, OrderType::LIMIT, 2800.00, 20)); // placed second

    // Incoming buy for 15 at 2800.00
    auto trades = book.addOrder(Order(12, "GOOG", Side::BUY, OrderType::LIMIT, 2800.00, 15));
    assert(trades.size() == 2);
    // Order 10 should be fully filled first (FIFO priority)
    assert(trades[0].sellOrderId == 10);
    assert(trades[0].quantity == 10);
    // Order 11 should fill remaining 5
    assert(trades[1].sellOrderId == 11);
    assert(trades[1].quantity == 5);

    auto snapshot = book.getDepthSnapshot();
    assert(snapshot.asks.size() == 1);
    assert(snapshot.asks[0].quantity == 15); // 20 - 5 = 15 remaining
}

void test_market_order_sweep() {
    OrderBook book("MSFT");
    // Place multi-level asks
    book.addOrder(Order(1, "MSFT", Side::SELL, OrderType::LIMIT, 300.00, 10));
    book.addOrder(Order(2, "MSFT", Side::SELL, OrderType::LIMIT, 302.00, 15));
    book.addOrder(Order(3, "MSFT", Side::SELL, OrderType::LIMIT, 305.00, 20));

    // Market Buy for 20 shares sweeps level 1 and part of level 2
    auto trades = book.addOrder(Order(4, "MSFT", Side::BUY, OrderType::MARKET, 0.0, 20));
    assert(trades.size() == 2);
    assert(trades[0].price == 300.00 && trades[0].quantity == 10);
    assert(trades[1].price == 302.00 && trades[1].quantity == 10);

    assert(book.getBestAsk() == 302.00); // 5 shares remaining at 302
}

void test_portfolio_balancer_and_pnl() {
    PortfolioBalancer portfolio(100000.0); // $100k cash
    portfolio.setTargetWeight("NVDA", 0.40);
    portfolio.setTargetWeight("AAPL", 0.30);
    portfolio.updateMarketPrice("NVDA", 200.0);
    portfolio.updateMarketPrice("AAPL", 150.0);

    // Initial weights are 0, balancer should generate buy orders
    auto orders = portfolio.generateRebalanceOrders();
    assert(!orders.empty());

    // Simulate executing a trade: Buy 200 NVDA at $200 = $40,000
    Trade t1(1, "NVDA", 10001, 20001, 200.0, 200);
    portfolio.executeTrade(t1, Side::BUY);

    assert(portfolio.getCash() == 60000.0);
    assert(portfolio.getPosition("NVDA")->quantity == 200);

    // Price appreciates to $250
    portfolio.updateMarketPrice("NVDA", 250.0);
    assert(portfolio.getTotalPortfolioValue() == 60000.0 + (200 * 250.0)); // $110,000
    assert(portfolio.getUnrealizedPnL() == (200 * 50.0)); // +$10,000 unrealized PnL

    // Sell 100 shares at $250
    Trade t2(2, "NVDA", 20002, 10002, 250.0, 100);
    portfolio.executeTrade(t2, Side::SELL);
    assert(portfolio.getCash() == 60000.0 + 25000.0);
    assert(portfolio.getRealizedPnL() == 5000.0); // ($250 - $200) * 100
}

int main() {
    std::cout << "========================================\n";
    std::cout << "PROJECT 1: UNIT TEST SUITE (C++ ENGINE)\n";
    std::cout << "========================================\n";

    run_test("Limit Order Placement & Spread", test_limit_order_placement_and_spread);
    run_test("Exact Match Execution", test_exact_match_execution);
    run_test("Partial Fill & Queue Persistence", test_partial_fill_and_queue_persistence);
    run_test("Order Cancellation", test_order_cancellation);
    run_test("Price-Time Priority (FIFO)", test_price_time_priority_fifo);
    run_test("Market Order Sweep", test_market_order_sweep);
    run_test("Portfolio Balancer & PnL Accounting", test_portfolio_balancer_and_pnl);

    std::cout << "\nALL 7 UNIT TESTS PASSED SUCCESSFULLY!\n";
    return 0;
}
