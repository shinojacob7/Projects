import 'package:test/test.dart';
import '../lib/models/product.dart';
import '../lib/services/inventory_repository.dart';
import '../lib/state/cart_manager.dart';

void main() {
  group('HyperCommerce Core Unit Tests', () {
    late InventoryRepository inventoryRepo;
    late CartManager cartManager;

    setUp(() {
      inventoryRepo = InventoryRepository();
      cartManager = CartManager(inventoryRepo);
    });

    test('Initial inventory seed verification', () {
      final products = inventoryRepo.getAllProducts();
      expect(products.length, equals(4));

      final laptop = inventoryRepo.getProductById('prod-001');
      expect(laptop, isNotNull);
      expect(laptop!.stockQuantity, equals(15));
      expect(inventoryRepo.getAvailableStock('prod-001'), equals(15));
    });

    test('Add item to cart within available stock', () {
      final laptop = inventoryRepo.getProductById('prod-001')!;
      final success = cartManager.addItem(laptop, 2);

      expect(success, isTrue);
      expect(cartManager.totalItemCount, equals(2));
      expect(cartManager.subtotal, closeTo(3799.98, 0.01));
    });

    test('Reject adding item when quantity exceeds inventory stock', () {
      final monitor = inventoryRepo.getProductById('prod-004')!; // stock is 5
      final success = cartManager.addItem(monitor, 10);

      expect(success, isFalse);
      expect(cartManager.totalItemCount, equals(0));
    });

    test('Apply promo discount and tax calculation', () {
      final headphones = inventoryRepo.getProductById('prod-002')!; // $299.50
      cartManager.addItem(headphones, 2); // Subtotal: $599.00

      expect(cartManager.subtotal, closeTo(599.00, 0.01));

      // Apply SAVE20 promo (20% off)
      final promoApplied = cartManager.applyPromoCode('SAVE20');
      expect(promoApplied, isTrue);

      final expectedDiscount = 599.00 * 0.20; // $119.80
      final expectedTaxable = 599.00 - expectedDiscount; // $479.20
      final expectedTax = expectedTaxable * 0.0825; // $39.534
      final expectedTotal = expectedTaxable + expectedTax; // $518.734

      expect(cartManager.discountAmount, closeTo(expectedDiscount, 0.01));
      expect(cartManager.taxAmount, closeTo(expectedTax, 0.01));
      expect(cartManager.finalTotal, closeTo(expectedTotal, 0.01));
    });

    test('Update item quantity and remove item', () {
      final watch = inventoryRepo.getProductById('prod-003')!;
      cartManager.addItem(watch, 2);
      expect(cartManager.totalItemCount, equals(2));

      // Update to 4
      final updated = cartManager.updateQuantity(watch.id, 4);
      expect(updated, isTrue);
      expect(cartManager.totalItemCount, equals(4));

      // Remove item
      cartManager.removeItem(watch.id);
      expect(cartManager.totalItemCount, equals(0));
      expect(cartManager.subtotal, equals(0.0));
    });

    test('Successful checkout commits stock deduction and produces receipt', () async {
      final laptop = inventoryRepo.getProductById('prod-001')!; // initial stock 15
      cartManager.addItem(laptop, 3);

      final receipt = await cartManager.checkout('idem-key-9988');

      expect(receipt, isNotNull);
      expect(receipt.idempotencyKey, equals('idem-key-9988'));
      expect(receipt.items.length, equals(1));
      expect(receipt.items.first.quantity, equals(3));

      // Cart should be reset
      expect(cartManager.totalItemCount, equals(0));

      // Stock should be deducted from 15 to 12
      expect(inventoryRepo.getProductById('prod-001')!.stockQuantity, equals(12));
    });

    test('Idempotent double-checkout does not double-decrement inventory', () async {
      final laptop = inventoryRepo.getProductById('prod-001')!;
      cartManager.addItem(laptop, 2);

      await cartManager.checkout('idem-key-first-pass');
      expect(inventoryRepo.getProductById('prod-001')!.stockQuantity, equals(13)); // 15 - 2

      // Second checkout with same key directly to repo
      final reCommit = await inventoryRepo.commitDeduction('idem-key-first-pass', [
        CartItem(product: laptop, quantity: 2)
      ]);
      expect(reCommit, isTrue);
      // Stock remains 13 (no double debit)
      expect(inventoryRepo.getProductById('prod-001')!.stockQuantity, equals(13));
    });
  });
}
