from dataclasses import dataclass
from typing import ClassVar, List, Optional, Tuple


@dataclass
class Product:
    product_id: int
    name: str
    category: str
    quantity: int
    price: float
    supplier: str

    inventory: ClassVar[List["Product"]] = []

    def __post_init__(self):
        # kiểm tra dữ liệu cơ bản
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.price < 0:
            raise ValueError("price cannot be negative")
        Product.inventory.append(self)

    @classmethod
    def add_product(cls, name, category, quantity, price, supplier):
        new_id = cls.inventory[-1].product_id + 1 if cls.inventory else 1
        cls(new_id, name, category, quantity, price, supplier)
        return "Product added successfully"

    @classmethod
    def find_by_id(cls, product_id: int) -> Optional["Product"]:
        for p in cls.inventory:
            if p.product_id == product_id:
                return p
        return None

    @classmethod
    def update_product(cls, product_id, quantity=None, price=None, supplier=None):
        p = cls.find_by_id(product_id)
        if not p:
            return "Product not found"

        if quantity is not None:
            if quantity < 0:
                return "Invalid quantity"
            p.quantity = quantity

        if price is not None:
            if price < 0:
                return "Invalid price"
            p.price = price

        if supplier is not None:
            p.supplier = supplier

        return "Product information updated successfully"

    @classmethod
    def delete_product(cls, product_id):
        p = cls.find_by_id(product_id)
        if not p:
            return "Product not found"
        cls.inventory.remove(p)
        return "Product deleted successfully"

    @classmethod
    def list_products(cls):
        if not cls.inventory:
            print("Kho đang trống.")
            return

        print("\n=== DANH SÁCH SẢN PHẨM TRONG KHO ===")
        for p in cls.inventory:
            print(f"ID:{p.product_id} | {p.name} | Cate:{p.category} | Qty:{p.quantity} | ${p.price} | Supplier:{p.supplier}")

    @classmethod
    def low_stock_alert(cls, threshold=3):
        print(f"\n=== HÀNG SẮP HẾT (<= {threshold}) ===")
        found = False
        for p in cls.inventory:
            if p.quantity <= threshold:
                print(f"ID:{p.product_id} | {p.name} | Qty:{p.quantity}")
                found = True
        if not found:
            print("Không có món nào sắp hết.")



@dataclass
class Order:
    order_id: int
    products: List[Tuple[int, int]]  # (product_id, quantity)
    customer_info: Optional[str] = None
    orders_history = []  # chỗ cất tất cả đơn đã chốt


    def place_order(self, product_id, quantity, customer_info=None):
        if quantity <= 0:
            return "Invalid order quantity"

        p = Product.find_by_id(product_id)
        if not p:
            return "Order could not be placed. Product not found or insufficient quantity."

        if p.quantity < quantity:
            return "Order could not be placed. Product not found or insufficient quantity."

        # trừ kho + ghi đơn
        p.quantity -= quantity
        self.products.append((product_id, quantity))

        if customer_info:
            self.customer_info = customer_info

        return f"Order placed successfully. Order ID: {self.order_id}"
    def total_price(self):
        total = 0
        for product_id, qty in self.products:
            p = Product.find_by_id(product_id)
            if p:
                total += p.price * qty
        return total

    def checkout(self):
        # chốt đơn: lưu vào lịch sử
        Order.orders_history.append({
            "order_id": self.order_id,
            "customer": self.customer_info,
            "items": self.products.copy(),
            "total": self.total_price()
        })
        return "Checkout success"

    @classmethod
    def print_invoice(cls, order_id: int):
        # tìm order trong lịch sử
        target = None
        for o in cls.orders_history:
            if o["order_id"] == order_id:
                target = o
                break

        if not target:
            print("Không tìm thấy order này.")
            return

        print("\n========== INVOICE ==========")
        print(f"Order ID: {target['order_id']}")
        print(f"Customer: {target['customer']}")
        print("----------------------------")
        print("Item | Qty | Price | Subtotal")

        grand = 0
        for pid, qty in target["items"]:
            p = Product.find_by_id(pid)
            # nếu product đã bị xóa khỏi kho sau này thì vẫn in được
            name = p.name if p else f"Product#{pid}"
            price = p.price if p else 0
            sub = price * qty
            grand += sub
            print(f"{name} | {qty} | {price} | {sub}")

        print("----------------------------")
        print(f"TOTAL: ${grand}")
        print("============================\n")


    @classmethod
    def show_history(cls):
        if not cls.orders_history:
            print("Chưa có đơn nào trong lịch sử.")
            return
        print("\n=== LỊCH SỬ ĐƠN ===")
        for o in cls.orders_history:
            print(f"Order #{o['order_id']} | customer: {o['customer']} | items: {o['items']} | total: ${o['total']}")


def seed_data():
    # tạo sẵn 2 món để test
    Product.inventory.clear()
    Product.add_product("Milk", "Dairy", 10, 2.5, "Supplier A")
    Product.add_product("Bread", "Bakery", 5, 1.8, "Supplier B")
    Product.add_product("Coke", "Drink", 3, 1.2, "Supplier C")



def show_menu():
    print("\n===== INVENTORY MENU =====")
    print("1) Xem kho")
    print("2) Thêm sản phẩm")
    print("3) Đặt đơn")
    print("4) Xem tổng tiền đơn")
    print("5) Chốt đơn (lưu lịch sử)")
    print("6) Xem lịch sử đơn")
    print("8) In hóa đơn theo Order ID")



    print("0) Thoát")


if __name__ == "__main__":
    seed_data()
    order = Order(order_id=1, products=[])

    while True:
        show_menu()
        choice = input("Chọn số: ").strip()

        if choice == "1":
            Product.list_products()

        elif choice == "2":
            name = input("Tên: ")
            category = input("Category: ")
            quantity = int(input("Qty: "))
            price = float(input("Price: "))
            supplier = input("Supplier: ")
            print(Product.add_product(name, category, quantity, price, supplier))

        elif choice == "3":
            pid = int(input("Product ID: "))
            qty = int(input("Qty mua: "))
            customer = input("Tên khách (optional): ").strip() or None
            print(order.place_order(pid, qty, customer))
            print("Giỏ đơn:", order.products)

        elif choice == "4":
            print("Tổng tiền đơn: $", order.total_price())

        elif choice == "5":
            print(order.checkout())
            # tạo đơn mới (id + 1), giỏ trống
            order = Order(order_id=order.order_id + 1, products=[])

        elif choice == "6":
            Order.show_history()

        elif choice == "8":
            oid = int(input("Nhập Order ID muốn in: "))
            Order.print_invoice(oid)



        elif choice == "0":
            print("Bye!")
            break

        else:
            print("Sai lựa chọn. Chọn lại.")
