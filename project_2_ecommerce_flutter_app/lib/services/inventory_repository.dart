import 'dart:async';
import '../models/product.dart';

class InventoryException implements Exception {
  final String message;
  InventoryException(this.message);
  @override
  String toString() => 'InventoryException: $message';
}

class InventoryRepository {
  final Map<String, Product> _inventory = {};
  final Map<String, int> _reservedStock = {}; // productId -> quantity reserved
  final Set<String> _processedIdempotencyKeys = {};

  InventoryRepository() {
    _seedInitialProducts();
  }

  void _seedInitialProducts() {
    final seed = [
      Product(id: 'prod-001', sku: 'LAPTOP-PRO-16', title: 'UltraBook Pro 16"', category: 'Electronics', price: 1899.99, stockQuantity: 15),
      Product(id: 'prod-002', sku: 'HEADPHONES-NC', title: 'Noise Cancelling Headphones', category: 'Audio', price: 299.50, stockQuantity: 30),
      Product(id: 'prod-003', sku: 'SMARTWATCH-ULTRA', title: 'Apex Smartwatch 44mm', category: 'Wearables', price: 349.00, stockQuantity: 8),
      Product(id: 'prod-004', sku: '4K-MONITOR-32', title: '4K IPS Studio Monitor 32"', category: 'Electronics', price: 649.99, stockQuantity: 5),
    ];
    for (var p in seed) {
      _inventory[p.id] = p;
    }
  }

  List<Product> getAllProducts() {
    return _inventory.values.toList();
  }

  Product? getProductById(String id) {
    return _inventory[id];
  }

  int getAvailableStock(String productId) {
    final prod = _inventory[productId];
    if (prod == null) return 0;
    final reserved = _reservedStock[productId] ?? 0;
    return prod.stockQuantity - reserved;
  }

  bool reserveStock(String productId, int quantity) {
    final available = getAvailableStock(productId);
    if (available < quantity) {
      return false;
    }
    _reservedStock[productId] = (_reservedStock[productId] ?? 0) + quantity;
    return true;
  }

  void releaseReservation(String productId, int quantity) {
    final current = _reservedStock[productId] ?? 0;
    if (current <= quantity) {
      _reservedStock.remove(productId);
    } else {
      _reservedStock[productId] = current - quantity;
    }
  }

  Future<bool> commitDeduction(String idempotencyKey, List<CartItem> items) async {
    if (_processedIdempotencyKeys.contains(idempotencyKey)) {
      // Idempotent duplicate: return true immediately without double debiting
      return true;
    }

    // Verify all reservations can be fulfilled
    for (var item in items) {
      final available = getAvailableStock(item.product.id);
      if (available < item.quantity) {
        throw InventoryException('Insufficient stock for ${item.product.title}: requested ${item.quantity}, available $available');
      }
    }

    // Deduct stock permanently and clear reservation
    for (var item in items) {
      final prod = _inventory[item.product.id]!;
      prod.stockQuantity -= item.quantity;
      releaseReservation(item.product.id, item.quantity);
    }

    _processedIdempotencyKeys.add(idempotencyKey);
    return true;
  }

  void replenishStock(String productId, int addedStock) {
    final prod = _inventory[productId];
    if (prod != null) {
      prod.stockQuantity += addedStock;
    }
  }
}
