import csv
import sqlite3

from dataclasses import dataclass
from typing import ClassVar, List, Optional, Tuple


DB_FILE = "inventory.db"

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # bảng products
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        supplier TEXT NOT NULL
    )
    """)

    # bảng orders
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY,
        customer TEXT
    )
    """)

    # bảng order_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(order_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    conn.commit()
    conn.close()


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
    def load_from_db(cls):
        cls.inventory.clear()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT product_id, name, category, quantity, price, supplier FROM products ORDER BY product_id")
        rows = cur.fetchall()
        conn.close()

        for r in rows:
            # tạo object và auto append vào inventory nhờ __post_init__
            cls(r[0], r[1], r[2], r[3], r[4], r[5])

    @classmethod
    def add_product_db(cls, name, category, quantity, price, supplier):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, category, quantity, price, supplier) VALUES (?, ?, ?, ?, ?)",
            (name, category, quantity, price, supplier),
        )
        conn.commit()
        conn.close()
        cls.load_from_db()
        return "Product added successfully (DB)"

    @classmethod
    def update_product_db(cls, product_id, quantity=None, price=None, supplier=None):
        sets = []
        params = []

        if quantity is not None:
            sets.append("quantity = ?")
            params.append(quantity)
        if price is not None:
            sets.append("price = ?")
            params.append(price)
        if supplier is not None:
            sets.append("supplier = ?")
            params.append(supplier)

        if not sets:
            return "Nothing to update"

        params.append(product_id)

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"UPDATE products SET {', '.join(sets)} WHERE product_id = ?", params)
        conn.commit()
        changed = cur.rowcount
        conn.close()

        cls.load_from_db()
        return "Product information updated successfully (DB)" if changed else "Product not found"

    @classmethod
    def delete_product_db(cls, product_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
        changed = cur.rowcount
        conn.close()

        cls.load_from_db()
        return "Product deleted successfully (DB)" if changed else "Product not found"


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
    
    @classmethod
    def decrease_stock_db(cls, product_id: int, qty: int):
        conn = get_conn()
        cur = conn.cursor()

        # chỉ trừ nếu còn đủ hàng (an toàn)
        cur.execute(
            "UPDATE products SET quantity = quantity - ? WHERE product_id = ? AND quantity >= ?",
            (qty, product_id, qty)
        )
        conn.commit()
        changed = cur.rowcount
        conn.close()

        cls.load_from_db()
        return changed == 1




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
        ok = Product.decrease_stock_db(product_id, quantity)
        if not ok:
            return "Order could not be placed. Product not found or insufficient quantity."

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
    def total_revenue(cls):
        total = 0
        for o in cls.orders_history:
            total += o["total"]
        return total

    @classmethod
    def top_selling_products(cls):
        counter = {}

        for o in cls.orders_history:
            for pid, qty in o["items"]:
                counter[pid] = counter.get(pid, 0) + qty

        if not counter:
            print("Chưa có dữ liệu bán hàng.")
            return

        print("\n=== TOP BÁN CHẠY ===")
        for pid, qty in sorted(counter.items(), key=lambda x: x[1], reverse=True):
            p = Product.find_by_id(pid)
            name = p.name if p else f"Product#{pid}"
            print(f"{name}: {qty} units")


    @classmethod
    def low_stock_report(cls, threshold=2):
        print(f"\n=== HÀNG SẮP HẾT (<= {threshold}) ===")
        for p in Product.inventory:
            if p.quantity <= threshold:
                print(f"{p.name}: còn {p.quantity}")


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

    @classmethod
    def export_sales_report_csv(cls, filename="sales_report.csv"):
        # top selling
        counter = {}
        for o in cls.orders_history:
            for pid, qty in o["items"]:
                counter[pid] = counter.get(pid, 0) + qty

        top_list = sorted(counter.items(), key=lambda x: x[1], reverse=True)

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            writer.writerow(["total_revenue", cls.total_revenue()])
            writer.writerow([])

            writer.writerow(["top_selling_product", "units_sold"])
            for pid, qty in top_list:
                p = Product.find_by_id(pid)
                name = p.name if p else f"Product#{pid}"
                writer.writerow([name, qty])

            writer.writerow([])
            writer.writerow(["low_stock_product", "qty_left"])
            for p in Product.inventory:
                if p.quantity <= 2:
                    writer.writerow([p.name, p.quantity])

        return f"Exported to {filename}"

    @classmethod
    def export_orders_csv(cls, filename="orders_history.csv"):
        import csv

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["order_id", "customer", "product_id", "product_name", "qty", "unit_price", "subtotal"])

            for o in cls.orders_history:
                for pid, qty in o["items"]:
                    p = Product.find_by_id(pid)
                    name = p.name if p else f"Product#{pid}"
                    price = p.price if p else 0
                    subtotal = price * qty
                    writer.writerow([o["order_id"], o["customer"], pid, name, qty, price, subtotal])

        return f"Exported to {filename}"

    @classmethod
    def load_history_from_db(cls):
        cls.orders_history.clear()
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT order_id, customer FROM orders ORDER BY order_id")
        orders = cur.fetchall()

        for order_id, customer in orders:
            cur.execute("SELECT product_id, qty, unit_price FROM order_items WHERE order_id = ?", (order_id,))
            items_rows = cur.fetchall()

            items = [(pid, qty) for pid, qty, _ in items_rows]
            total = sum(qty * unit_price for _, qty, unit_price in items_rows)

            cls.orders_history.append({
                "order_id": order_id,
                "customer": customer,
                "items": items,
                "total": total
            })

        conn.close()

    def checkout_db(self):
        # lưu order + items vào DB
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("INSERT INTO orders (order_id, customer) VALUES (?, ?)", (self.order_id, self.customer_info))

        for pid, qty in self.products:
            p = Product.find_by_id(pid)
            unit_price = p.price if p else 0
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, qty, unit_price) VALUES (?, ?, ?, ?)",
                (self.order_id, pid, qty, unit_price)
            )

        conn.commit()
        conn.close()

        # update cache history trong app
        Order.load_history_from_db()
        return "Checkout success (DB)"




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
    print("9) Sales report")
    print("10) Export report CSV")
    print("11) Export orders CSV")





    print("0) Thoát")


if __name__ == "__main__":
    init_db()

    Product.load_from_db()
    Order.load_history_from_db()



    # seed_data()
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
            print(Product.add_product_db(name, category, quantity, price, supplier))

        elif choice == "3":
            pid = int(input("Product ID: "))
            qty = int(input("Qty mua: "))
            customer = input("Tên khách (optional): ").strip() or None
            print(order.place_order(pid, qty, customer))
            print("Giỏ đơn:", order.products)

        elif choice == "4":
            print("Tổng tiền đơn: $", order.total_price())

        elif choice == "5":
            print(order.checkout_db())
            # tạo đơn mới (id + 1), giỏ trống
            order = Order(order_id=order.order_id + 1, products=[])

        elif choice == "6":
            Order.show_history()

        elif choice == "8":
            oid = int(input("Nhập Order ID muốn in: "))
            Order.print_invoice(oid)


        elif choice == "9":
            print("\n=== SALES REPORT ===")
            print("Tổng doanh thu: $", Order.total_revenue())
            Order.top_selling_products()
            Order.low_stock_report()

        elif choice == "10":
            print(Order.export_sales_report_csv())

        elif choice == "11":
            print(Order.export_orders_csv())



        elif choice == "0":
            print("Bye!")
            break

        else:
            print("Sai lựa chọn. Chọn lại.")
