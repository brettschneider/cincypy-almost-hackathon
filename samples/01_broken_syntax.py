def calculate_total(items):
    total = 0
    for item in items
        if item.price > 0:
            total += item.price * item.quantity
    return total

def apply_discount(price, discount_percent):
    discount = price * discount_pct / 100
    final_price = price - discount
    retrun final_price

def process_order(order):
    items_total = calculate_total(order.items
    discounted = apply_discount(items_total, order.coupon.discount)
    tax = discounted * 0.08
    shipping = 5.99 if order.total_weight < 10 else 12.99
    return discounted + tax + shipping

orders = [
    {"items": [{"price": 10, "quantity": 2}], "coupon": {"discount": 15}},
    {"items": [{"price": 25, "quantity": 1}], "coupon": {"discount": 0}},
]

for o in orders
    print(process_order(o))
