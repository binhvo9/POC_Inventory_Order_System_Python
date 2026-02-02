
# POC Inventory & Order System (Python + FastAPI + SQLite)

A small but real-world backend portfolio project.

This project demonstrates:
- Inventory management
- Order placement with stock deduction
- Persistent storage with SQLite
- REST API using FastAPI
- Basic AI-style analytics (low-stock forecast & reorder suggestion)

---

## Features

### Inventory
- Add products
- List products
- Persistent storage (SQLite)
- Low-stock detection

### Orders
- Place orders via API
- Auto-decrease stock in database
- Save orders + order items
- Order history persistence

### Reports & Analytics
- Sales report (total revenue, top-selling products)
- Export sales report to CSV
- Export order history to CSV

### AI (Conceptual, Free, Runnable)
- Low stock forecast based on recent orders
- Reorder suggestion based on estimated demand  
(No heavy ML libraries, logic-based forecasting)

---

## Tech Stack
- Python 3
- FastAPI
- SQLite
- Standard Library only (csv, sqlite3, datetime, etc.)

---

## How to Run

### 1. Setup virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
````

### 2. Run API server

```bash
python -m uvicorn api:app --reload
```

### 3. Open API Docs

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## API Endpoints

### Products

* `GET /products` – list inventory
* `POST /products` – add product

### Orders

* `POST /orders` – place order (auto stock deduction)

### AI / Analytics

* `GET /ai/low-stock-forecast`
* `GET /ai/reorder-suggest`

---

## Data Persistence

* SQLite database file: `inventory.db`
* Data remains after restart

