import '../lib/services/inventory_repository.dart';
import '../lib/state/cart_manager.dart';

void main() async {
  print('================================================================');
  print('PROJECT 2: SIMULATION / DRY RUN (HYPERCOMMERCE E-COMMERCE SUITE)');
  print('================================================================\n');

  final inventory = InventoryRepository();
  final cart = CartManager(inventory);

  print('[Phase 1] Initializing Warehouse Inventory Catalog...');
  for (var p in inventory.getAllProducts()) {
    print('  - [${p.sku}] ${p.title} | Price: \$${p.price.toStringAsFixed(2)} | Stock: ${p.stockQuantity}');
  }

  print('\n[Phase 2] Simulating User Shopping Session & Cart Building...');
  final laptop = inventory.getProductById('prod-001')!;
  final headphones = inventory.getProductById('prod-002')!;
  final monitor = inventory.getProductById('prod-004')!;

  print('  -> Adding 1x ${laptop.title} to Cart...');
  cart.addItem(laptop, 1);

  print('  -> Adding 2x ${headphones.title} to Cart...');
  cart.addItem(headphones, 2);

  print('  -> Attempting to add 10x ${monitor.title} (Stock is only 5)...');
  final oversizeAttempt = cart.addItem(monitor, 10);
  print('     Oversize addition rejected: ${!oversizeAttempt} (Stock-guard active)');

  print('  -> Adding 2x ${monitor.title} to Cart (Valid)...');
  cart.addItem(monitor, 2);

  print('\n[Phase 3] Applying Discount Promo Codes...');
  print('  -> Subtotal before promo: \$${cart.subtotal.toStringAsFixed(2)}');
  final promoSuccess = cart.applyPromoCode('SAVE20');
  print('  -> Promo Code [SAVE20] applied: $promoSuccess');
  print('     Discount Amount (20%): -\$${cart.discountAmount.toStringAsFixed(2)}');
  print('     Estimated Tax (8.25%): +\$${cart.taxAmount.toStringAsFixed(2)}');
  print('     Final Payable Total:   \$${cart.finalTotal.toStringAsFixed(2)}');

  print('\n[Phase 4] Executing Checkout Transaction with Idempotency Key...');
  final idempotencyKey = 'tx-sess-${DateTime.now().millisecondsSinceEpoch}';
  final receipt = await cart.checkout(idempotencyKey);

  print('  RECEIPT GENERATED:');
  print('    Order ID:        ${receipt.orderId}');
  print('    Idempotency Key: ${receipt.idempotencyKey}');
  print('    Items Purchased: ${receipt.items.length} distinct lines');
  for (var item in receipt.items) {
    print('      * ${item.product.title} (Qty: ${item.quantity}) @ \$${item.product.price} = \$${item.lineTotal.toStringAsFixed(2)}');
  }
  print('    Subtotal:        \$${receipt.subtotal.toStringAsFixed(2)}');
  print('    Discount:       -\$${receipt.discountAmount.toStringAsFixed(2)}');
  print('    Tax:            +\$${receipt.taxAmount.toStringAsFixed(2)}');
  print('    Total Charged:   \$${receipt.finalTotal.toStringAsFixed(2)}');

  print('\n[Phase 5] Post-Transaction Warehouse Audit:');
  for (var p in inventory.getAllProducts()) {
    print('  - [${p.sku}] ${p.title} -> Remaining Stock: ${p.stockQuantity}');
  }

  print('\nDRY RUN / PIPELINE SIMULATION COMPLETED WITH 0 ERRORS.');
}
