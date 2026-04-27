# modules
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import os

# page name
st.set_page_config(page_title="Finance Tracker")

# maintains data for user over multiple sessions
# private financial information saved locally
CSV_FILE = "transactions.csv"

if "transactions" not in st.session_state:
    if os.path.exists(CSV_FILE):
        st.session_state.transactions = pd.read_csv(CSV_FILE).to_dict("records")
    else:
        st.session_state.transactions = []
RECURRING_FILE = "recurring.csv"

if "recurring_applied" not in st.session_state:
    st.session_state.recurring_applied = False

if os.path.exists(RECURRING_FILE) and not st.session_state.recurring_applied:
    recurring_df = pd.read_csv(RECURRING_FILE)
    now = pd.Timestamp.now()
    applied = False
    
    for i, row in recurring_df.iterrows():
        last_applied = pd.Timestamp(row["Date"])
        if now - last_applied >= pd.Timedelta(minutes=1):
            new_entry = {
                "Type": row["Type"],
                "Amount": row["Amount"],
                "Category": row["Category"],
                "Date": str(now.date()),
            }
            st.session_state.transactions.append(new_entry)
            recurring_df.loc[i, "Date"] = str(now.date())
            applied = True
    
    if applied:
        pd.DataFrame(st.session_state.transactions).to_csv(CSV_FILE, index=False)
        recurring_df.to_csv(RECURRING_FILE, index=False)
    
    st.session_state.recurring_applied = True
# title
st.title("Personal Finance Tracker")

# transaction information
st.subheader("Add Transaction")
col1, col2 = st.columns(2)
with col1:
    trans_type = st.selectbox("Type", ["Expense", "Income"])
    amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)
with col2:
    category = st.selectbox("Category", ["Dine out", "Gas/Fares", "Shopping", "Entertainment", "Bills", "Savings",  "Other"] if trans_type == "Expense" else ["Job", "Freelance", "Gift", "Other"])
    trans_date = st.date_input("Date", value=date.today())
is_recurring = st.checkbox("Will this be a monthly transaction?")

if st.button("Add"):
    new_transaction = {
        "Type": trans_type,
        "Amount": amount,
        "Category": category,
        "Date": str(trans_date),
    }
    if is_recurring:
        RECURRING_FILE = "recurring.csv"
        if os.path.exists(RECURRING_FILE):
            recurring_df = pd.read_csv(RECURRING_FILE)
            new_recurring = pd.DataFrame([new_transaction])
            recurring_df = pd.concat([recurring_df, new_recurring], ignore_index=True)
        else:
            recurring_df = pd.DataFrame([new_transaction])
        recurring_df.to_csv(RECURRING_FILE, index=False)
        st.success(f"Recurring transaction saved: ${amount:.2f} every month")
    else:
        st.session_state.transactions.append(new_transaction)
        pd.DataFrame(st.session_state.transactions).to_csv(CSV_FILE, index=False)
        st.success(f"Added {trans_type}: ${amount:.2f}")

# Summary
if st.session_state.transactions:
    df = pd.DataFrame(st.session_state.transactions)

    income = df[df["Type"] == "Income"]["Amount"].sum()
    expenses = df[df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expenses
 
    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:.2f}")
    col2.metric("Total Expenses", f"${expenses:.2f}")
    col3.metric("Balance", f"${balance:.2f}")

# Transaction history
st.subheader("Transaction History")
st.dataframe(df[::-1], use_container_width=True)
st.subheader("WARNING")

# reset history of transactions
if st.button("CLEAR ALL TRANSACTIONS"):
    st.session_state.transactions = []
    st.session_state.recurring_applied = False
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
    if os.path.exists(RECURRING_FILE):
        os.remove(RECURRING_FILE)
    st.success("All transactions cleared.")
    st.rerun()