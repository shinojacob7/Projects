import '../models/product.dart';
import '../services/inventory_repository.dart';

class CartManager {
  final InventoryRepository _inventoryRepo;
  final Map<String, CartItem> _items = {};
  String? _appliedPromoCode;
  double _promoDiscountPercent = 0.0;
  static const double taxRate = 0.0825; // 8.25% State & Local Sales Tax

  CartManager(this._inventoryRepo);

  List<CartItem> get items => _items.values.toList();
  int get totalItemCount => _items.values.fold(0, (sum, i) => sum + i.quantity);
  String? get activePromoCode => _appliedPromoCode;

  double get subtotal => _items.values.fold(0.0, (sum, i) => sum + i.lineTotal);

  double get discountAmount => subtotal * _promoDiscountPercent;

  double get taxAmount => (subtotal - discountAmount) * taxRate;

  double get finalTotal => (subtotal - discountAmount) + taxAmount;

  bool addItem(Product product, int quantity) {
    if (quantity <= 0) return false;
    final currentInCart = _items[product.id]?.quantity ?? 0;
    final available = _inventoryRepo.getAvailableStock(product.id);

    if (currentInCart + quantity > available) {
      return false; // exceeds available stock
    }

    if (_items.containsKey(product.id)) {
      _items[product.id]!.quantity += quantity;
    } else {
      _items[product.id] = CartItem(product: product, quantity: quantity);
    }
    return true;
  }

  bool updateQuantity(String productId, int newQuantity) {
    if (!_items.containsKey(productId)) return false;
    if (newQuantity <= 0) {
      _items.remove(productId);
      return true;
    }

    final available = _inventoryRepo.getAvailableStock(productId);
    if (newQuantity > available) {
      return false;
    }

    _items[productId]!.quantity = newQuantity;
    return true;
  }

  void removeItem(String productId) {
    _items.remove(productId);
  }

  void clearCart() {
    _items.clear();
    _appliedPromoCode = null;
    _promoDiscountPercent = 0.0;
  }

  bool applyPromoCode(String code) {
    final cleanCode = code.trim().toUpperCase();
    if (cleanCode == 'SAVE20') {
      _appliedPromoCode = cleanCode;
      _promoDiscountPercent = 0.20;
      return true;
    } else if (cleanCode == 'FLAT10') {
      _appliedPromoCode = cleanCode;
      _promoDiscountPercent = 0.10;
      return true;
    }
    return false;
  }

  Future<OrderReceipt> checkout(String idempotencyKey) async {
    if (_items.isEmpty) {
      throw StateError('Cannot checkout an empty cart');
    }

    final cartSnapshot = items;
    final calculatedSubtotal = subtotal;
    final calculatedDiscount = discountAmount;
    final calculatedTax = taxAmount;
    final calculatedTotal = finalTotal;

    // Commit deduction against inventory
    await _inventoryRepo.commitDeduction(idempotencyKey, cartSnapshot);

    final receipt = OrderReceipt(
      orderId: 'ORD-${DateTime.now().millisecondsSinceEpoch}',
      idempotencyKey: idempotencyKey,
      items: cartSnapshot,
      subtotal: calculatedSubtotal,
      discountAmount: calculatedDiscount,
      taxAmount: calculatedTax,
      finalTotal: calculatedTotal,
      createdAt: DateTime.now(),
    );

    clearCart();
    return receipt;
  }
}
