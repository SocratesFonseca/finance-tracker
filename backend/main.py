from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Finance Tracker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "finance_tracker"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor
    )

# Pydantic models
class TransactionBase(BaseModel):
    type: str  # "Income" or "Expense"
    amount: float
    category: str
    date: str
    description: Optional[str] = None
    interval: Optional[str] = "monthly"  # weekly, biweekly, monthly, yearly

class Transaction(TransactionBase):
    id: int

class RecurringTransaction(TransactionBase):
    id: int
    last_applied: str
    interval: str

# Initialize database tables
@app.on_event("startup")
def startup():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create transactions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            type VARCHAR(10) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            category VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            description TEXT
        )
    """)
    
    # Create recurring_transactions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring_transactions (
            id SERIAL PRIMARY KEY,
            type VARCHAR(10) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            category VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            description TEXT,
            last_applied DATE NOT NULL,
            interval VARCHAR(20) NOT NULL DEFAULT 'monthly'
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Finance Tracker API"}

@app.get("/transactions", response_model=List[Transaction])
def get_transactions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY date DESC")
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return transactions

@app.post("/transactions", response_model=Transaction)
def create_transaction(transaction: TransactionBase):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (transaction.type, transaction.amount, transaction.category, transaction.date, transaction.description)
    )
    new_transaction = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = %s RETURNING *", (transaction_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}

@app.get("/recurring", response_model=List[RecurringTransaction])
def get_recurring_transactions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recurring_transactions")
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return transactions

@app.post("/recurring", response_model=RecurringTransaction)
def create_recurring_transaction(transaction: TransactionBase):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recurring_transactions (type, amount, category, date, description, last_applied, interval) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (transaction.type, transaction.amount, transaction.category, transaction.date, transaction.description, transaction.date, transaction.interval)
    )
    new_transaction = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_transaction

@app.delete("/recurring/{transaction_id}")
def delete_recurring_transaction(transaction_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM recurring_transactions WHERE id = %s RETURNING *", (transaction_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    return {"message": "Recurring transaction deleted"}

@app.post("/apply-recurring")
def apply_recurring_transactions():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all recurring transactions
    cur.execute("SELECT * FROM recurring_transactions")
    recurring = cur.fetchall()
    
    now = datetime.now()
    applied_count = 0
    
    # Interval days mapping
    interval_days = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'yearly': 365
    }
    
    for trans in recurring:
        last_applied = datetime.strptime(str(trans['last_applied']), '%Y-%m-%d')
        interval = trans.get('interval', 'monthly')
        days_threshold = interval_days.get(interval, 30)
        
        if (now - last_applied).days >= days_threshold:
            # Create new transaction
            cur.execute(
                "INSERT INTO transactions (type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s)",
                (trans['type'], trans['amount'], trans['category'], str(now.date()), trans['description'])
            )
            # Update last_applied
            cur.execute(
                "UPDATE recurring_transactions SET last_applied = %s WHERE id = %s",
                (str(now.date()), trans['id'])
            )
            applied_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"message": f"Applied {applied_count} recurring transactions"}

@app.get("/summary")
def get_summary():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Income'")
    income = cur.fetchone()['sum'] or 0
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Expense'")
    expenses = cur.fetchone()['sum'] or 0
    
    cur.close()
    conn.close()
    
    return {
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(income - expenses)
    }

@app.delete("/clear-all")
def clear_all_transactions():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM recurring_transactions")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"message": "All transactions cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
