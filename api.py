from fastapi import FastAPI
from pydantic import BaseModel

from main import Product, Order, get_conn, init_db


app = FastAPI(title="Inventory API")


# ----- MODELS (forms) -----
class ProductCreate(BaseModel):
    name: str
    category: str
    quantity: int
    price: float
    supplier: str


class OrderItem(BaseModel):
    product_id: int
    qty: int


class OrderCreate(BaseModel):
    customer: str | None = None
    items: list[OrderItem]


# ----- STARTUP -----
@app.on_event("startup")
def startup():
    # tạo DB/bảng nếu chưa có
    init_db()
    # load cache từ DB vào RAM (để Product.find_by_id hoạt động)
    Product.load_from_db()
    Order.load_history_from_db()


# ----- HELPERS -----
def next_order_id() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(order_id), 0) + 1 FROM orders")
    oid = cur.fetchone()[0]
    conn.close()
    return oid


# ----- ROUTES -----
@app.get("/")
def root():
    return {"message": "hello from inventory api"}


@app.get("/products")
def get_products():
    Product.load_from_db()
    return [
        {
            "id": p.product_id,
            "name": p.name,
            "category": p.category,
            "quantity": p.quantity,
            "price": p.price,
            "supplier": p.supplier,
        }
        for p in Product.inventory
    ]


@app.post("/products")
def create_product(data: ProductCreate):
    msg = Product.add_product_db(
        data.name, data.category, data.quantity, data.price, data.supplier
    )
    return {"ok": True, "message": msg}


@app.post("/orders")
def create_order(data: OrderCreate):
    # refresh cache để đảm bảo đúng stock mới nhất
    Product.load_from_db()

    oid = next_order_id()
    order = Order(order_id=oid, products=[], customer_info=data.customer)

    for it in data.items:
        msg = order.place_order(it.product_id, it.qty, data.customer)
        if "could not be placed" in msg:
            return {"ok": False, "message": msg}

    msg2 = order.checkout_db()
    return {"ok": True, "order_id": oid, "message": msg2, "total": order.total_price()}

@app.get("/ai/low-stock-forecast")
def low_stock_forecast(lookback_orders: int = 10, threshold: int = 2):
    # load dữ liệu mới nhất
    Product.load_from_db()
    Order.load_history_from_db()

    # lấy N đơn gần nhất
    recent = Order.orders_history[-lookback_orders:] if lookback_orders > 0 else Order.orders_history

    # đếm bán trung bình mỗi đơn
    sold_counts = {}   # pid -> total qty sold in recent orders
    order_hits = {}    # pid -> number of orders that contain this pid

    for o in recent:
        seen_in_this_order = set()
        for pid, qty in o["items"]:
            sold_counts[pid] = sold_counts.get(pid, 0) + qty
            if pid not in seen_in_this_order:
                order_hits[pid] = order_hits.get(pid, 0) + 1
                seen_in_this_order.add(pid)

    results = []
    for p in Product.inventory:
        if p.quantity <= threshold:
            pid = p.product_id
            total_sold = sold_counts.get(pid, 0)
            hits = order_hits.get(pid, 0)

            # avg qty per order (chỉ tính những đơn có món đó)
            avg_per_order = (total_sold / hits) if hits > 0 else 0

            # dự đoán còn bao nhiêu đơn nữa hết
            est_orders_left = (p.quantity / avg_per_order) if avg_per_order > 0 else None

            results.append({
                "product_id": pid,
                "product_name": p.name,
                "qty_left": p.quantity,
                "lookback_orders": lookback_orders,
                "avg_sold_per_order": round(avg_per_order, 2),
                "estimated_orders_left": (round(est_orders_left, 2) if est_orders_left is not None else None),
                "note": ("not enough data" if avg_per_order == 0 else "ok")
            })

    return {
        "threshold": threshold,
        "results": results
    }

@app.get("/ai/reorder-suggest")
def reorder_suggest(lookback_orders: int = 20, target_days: int = 7):
    Product.load_from_db()
    Order.load_history_from_db()

    recent = Order.orders_history[-lookback_orders:] if lookback_orders > 0 else Order.orders_history

    # đếm bán tổng
    sold_counts = {}  # pid -> total qty sold
    for o in recent:
        for pid, qty in o["items"]:
            sold_counts[pid] = sold_counts.get(pid, 0) + qty

    # ước lượng "đơn per day": giả lập đơn nào cũng như nhau => coi lookback_orders ~ target window
    # để đơn giản: lấy avg per order rồi nhân "orders_per_day" giả lập = 1
    # (m muốn xịn hơn thì bước sau tao thêm timestamp thật)
    orders_per_day = 1

    results = []
    for p in Product.inventory:
        pid = p.product_id
        total_sold = sold_counts.get(pid, 0)

        # avg sold per order
        avg_per_order = (total_sold / lookback_orders) if lookback_orders > 0 else 0
        daily_demand = avg_per_order * orders_per_day

        need_for_days = daily_demand * target_days
        reorder_qty = max(0, int(round(need_for_days - p.quantity)))

        results.append({
            "product_id": pid,
            "product_name": p.name,
            "qty_left": p.quantity,
            "lookback_orders": lookback_orders,
            "target_days": target_days,
            "estimated_daily_demand": round(daily_demand, 2),
            "recommended_reorder_qty": reorder_qty
        })

    # ưu tiên món cần nhập nhiều nhất lên đầu
    results.sort(key=lambda x: x["recommended_reorder_qty"], reverse=True)

    return {"results": results}

