class Product {
  final String id;
  final String sku;
  final String title;
  final String category;
  final double price;
  int stockQuantity;
  final double rating;

  Product({
    required this.id,
    required this.sku,
    required this.title,
    required this.category,
    required this.price,
    required this.stockQuantity,
    this.rating = 4.5,
  });

  bool get inStock => stockQuantity > 0;

  Map<String, dynamic> toJson() => {
    'id': id,
    'sku': sku,
    'title': title,
    'category': category,
    'price': price,
    'stockQuantity': stockQuantity,
    'rating': rating,
  };
}

class CartItem {
  final Product product;
  int quantity;

  CartItem({required this.product, required this.quantity});

  double get lineTotal => product.price * quantity;
}

class OrderReceipt {
  final String orderId;
  final String idempotencyKey;
  final List<CartItem> items;
  final double subtotal;
  final double discountAmount;
  final double taxAmount;
  final double finalTotal;
  final DateTime createdAt;

  OrderReceipt({
    required this.orderId,
    required this.idempotencyKey,
    required this.items,
    required this.subtotal,
    required this.discountAmount,
    required this.taxAmount,
    required this.finalTotal,
    required this.createdAt,
  });
}
