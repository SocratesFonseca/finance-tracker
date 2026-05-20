from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from groq import Groq
from passlib.context import CryptContext
from jose import JWTError, jwt
from functools import wraps

app = FastAPI(title="Finance Tracker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "finance_tracker"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor
    )

# Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Authentication helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user is None:
        raise credentials_exception
    return user

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

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool = True

# Initialize database tables
@app.on_event("startup")
def startup():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create transactions table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(10) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            category VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            description TEXT
        )
    """)
    
    # Create recurring_transactions table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
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

@app.post("/register")
def register(user: UserCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if username or email already exists
    cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (user.username, user.email))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    cur.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s) RETURNING id, username, email",
        (user.username, user.email, hashed_password)
    )
    new_user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return {"message": "User registered successfully", "user": new_user}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/transactions", response_model=List[Transaction])
def get_transactions(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC", (current_user['id'],))
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return transactions

@app.post("/transactions", response_model=Transaction)
def create_transaction(transaction: TransactionBase, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
        (current_user['id'], transaction.type, transaction.amount, transaction.category, transaction.date, transaction.description)
    )
    new_transaction = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s RETURNING *", (transaction_id, current_user['id']))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}

@app.get("/recurring", response_model=List[RecurringTransaction])
def get_recurring_transactions(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recurring_transactions WHERE user_id = %s", (current_user['id'],))
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return transactions

@app.post("/recurring", response_model=RecurringTransaction)
def create_recurring_transaction(transaction: TransactionBase, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO recurring_transactions (user_id, type, amount, category, date, description, last_applied, interval) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (current_user['id'], transaction.type, transaction.amount, transaction.category, transaction.date, transaction.description, transaction.date, transaction.interval)
    )
    new_transaction = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_transaction

@app.delete("/recurring/{transaction_id}")
def delete_recurring_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM recurring_transactions WHERE id = %s AND user_id = %s RETURNING *", (transaction_id, current_user['id']))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    return {"message": "Recurring transaction deleted"}

@app.post("/apply-recurring")
def apply_recurring_transactions(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user's recurring transactions
    cur.execute("SELECT * FROM recurring_transactions WHERE user_id = %s", (current_user['id'],))
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
                "INSERT INTO transactions (user_id, type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s, %s)",
                (current_user['id'], trans['type'], trans['amount'], trans['category'], str(now.date()), trans['description'])
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
def get_summary(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Income' AND user_id = %s", (current_user['id'],))
    income = cur.fetchone()['sum'] or 0
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Expense' AND user_id = %s", (current_user['id'],))
    expenses = cur.fetchone()['sum'] or 0
    
    cur.close()
    conn.close()
    
    return {
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(income - expenses)
    }

@app.delete("/clear-all")
def clear_all_transactions(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM transactions WHERE user_id = %s", (current_user['id'],))
    cur.execute("DELETE FROM recurring_transactions WHERE user_id = %s", (current_user['id'],))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"message": "All transactions cleared"}

@app.get("/recommendations")
def get_financial_recommendations(current_user: dict = Depends(get_current_user)):
    if not groq_client:
        raise HTTPException(status_code=503, detail="Groq API key not configured")
    
    # Get user's transaction data
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT type, amount, category, date, description FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 50", (current_user['id'],))
    transactions = cur.fetchall()
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Income' AND user_id = %s", (current_user['id'],))
    income = cur.fetchone()['sum'] or 0
    
    cur.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Expense' AND user_id = %s", (current_user['id'],))
    expenses = cur.fetchone()['sum'] or 0
    
    cur.close()
    conn.close()
    
    # Prepare transaction summary for the AI
    transaction_summary = f"""
    Total Income: ${income}
    Total Expenses: ${expenses}
    Balance: ${income - expenses}
    
    Recent Transactions:
    """
    
    for t in transactions:
        transaction_summary += f"- {t['type']}: ${t['amount']} ({t['category']}) on {t['date']}"
        if t['description']:
            transaction_summary += f" - {t['description']}"
        transaction_summary += "\n"
    
    # Get recommendations from Groq
    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial advisor. Provide specific, actionable advice based on the user's transaction data. Be concise and practical. Focus on helping them save money and make better financial decisions."
                },
                {
                    "role": "user",
                    "content": f"Based on my financial data, please provide 3-5 specific recommendations for being more financially responsible:\n{transaction_summary}"
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        recommendations = response.choices[0].message.content
        return {"recommendations": recommendations}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
