import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Wallet, TrendingUp, TrendingDown, Plus, Trash2, RefreshCw, MessageCircle, X } from 'lucide-react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [transactions, setTransactions] = useState([]);
  const [recurringTransactions, setRecurringTransactions] = useState([]);
  const [summary, setSummary] = useState({ income: 0, expenses: 0, balance: 0 });
  const [showForm, setShowForm] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [recommendations, setRecommendations] = useState('');
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [showLogin, setShowLogin] = useState(true);
  const [isRegistering, setIsRegistering] = useState(false);
  const [authForm, setAuthForm] = useState({
    username: '',
    email: '',
    password: ''
  });
  const [formData, setFormData] = useState({
    type: 'Expense',
    amount: '',
    category: 'Dine out',
    date: new Date().toISOString().split('T')[0],
    description: '',
    isRecurring: false,
    interval: 'monthly'
  });

  const expenseCategories = ['Dine out', 'Gas/Fares', 'Shopping', 'Entertainment', 'Bills', 'Savings', 'Other'];
  const incomeCategories = ['Job', 'Freelance', 'Gift', 'Other'];

  useEffect(() => {
    if (token) {
      setIsAuthenticated(true);
      setShowLogin(false);
      fetchData();
    }
  }, [token]);

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setToken(savedToken);
      setIsAuthenticated(true);
      setShowLogin(false);
    }
  }, []);

  const fetchData = async () => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const [transRes, recRes, sumRes] = await Promise.all([
        axios.get(`${API_URL}/transactions`, { headers }),
        axios.get(`${API_URL}/recurring`, { headers }),
        axios.get(`${API_URL}/summary`, { headers })
      ]);
      setTransactions(transRes.data);
      setRecurringTransactions(recRes.data);
      setSummary(sumRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      if (error.response?.status === 401) {
        handleLogout();
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const transactionData = {
        type: formData.type,
        amount: parseFloat(formData.amount),
        category: formData.category,
        date: formData.date,
        description: formData.description,
        interval: formData.interval
      };

      if (formData.isRecurring) {
        await axios.post(`${API_URL}/recurring`, transactionData, { headers });
      } else {
        await axios.post(`${API_URL}/transactions`, transactionData, { headers });
      }

      setFormData({
        type: 'Expense',
        amount: '',
        category: 'Dine out',
        date: new Date().toISOString().split('T')[0],
        description: '',
        isRecurring: false,
        interval: 'monthly'
      });
      setShowForm(false);
      fetchData();
    } catch (error) {
      console.error('Error adding transaction:', error);
    }
  };

  const deleteTransaction = async (id) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API_URL}/transactions/${id}`, { headers });
      fetchData();
    } catch (error) {
      console.error('Error deleting transaction:', error);
    }
  };

  const deleteRecurring = async (id) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API_URL}/recurring/${id}`, { headers });
      fetchData();
    } catch (error) {
      console.error('Error deleting recurring transaction:', error);
    }
  };

  const applyRecurring = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.post(`${API_URL}/apply-recurring`, {}, { headers });
      fetchData();
    } catch (error) {
      console.error('Error applying recurring transactions:', error);
    }
  };

  const clearAll = async () => {
    if (window.confirm('Are you sure you want to clear all transactions?')) {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        await axios.delete(`${API_URL}/clear-all`, { headers });
        fetchData();
      } catch (error) {
        console.error('Error clearing transactions:', error);
      }
    }
  };

  const getRecommendations = async () => {
    setLoadingRecommendations(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API_URL}/recommendations`, { headers });
      setRecommendations(response.data.recommendations);
      setShowRecommendations(true);
    } catch (error) {
      console.error('Error getting recommendations:', error);
      alert('Failed to get recommendations. Make sure GROQ_API_KEY is configured.');
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', authForm.username);
      formData.append('password', authForm.password);

      const response = await axios.post(`${API_URL}/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      const accessToken = response.data.access_token;
      localStorage.setItem('token', accessToken);
      setToken(accessToken);
      setIsAuthenticated(true);
      setShowLogin(false);
      fetchData();
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please check your credentials.');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_URL}/register`, authForm);
      alert('Registration successful! Please login.');
      setIsRegistering(false);
    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed. Username or email may already exist.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setIsAuthenticated(false);
    setShowLogin(true);
    setTransactions([]);
    setRecurringTransactions([]);
    setSummary({ income: 0, expenses: 0, balance: 0 });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 p-8">
      <div className="max-w-6xl mx-auto">
        {showLogin ? (
          <div className="flex items-center justify-center min-h-[80vh]">
            <div className="bg-white rounded-xl p-8 shadow-2xl w-full max-w-md">
              <h2 className="text-3xl font-bold text-center mb-6 flex items-center justify-center gap-2">
                <Wallet className="w-8 h-8 text-purple-600" />
                {isRegistering ? 'Create Account' : 'Login'}
              </h2>
              <form onSubmit={isRegistering ? handleRegister : handleLogin} className="space-y-4">
                {isRegistering && (
                  <div>
                    <label className="block text-gray-700 mb-2">Email</label>
                    <input
                      type="email"
                      value={authForm.email}
                      onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                      className="w-full p-3 border rounded-lg"
                      required
                    />
                  </div>
                )}
                <div>
                  <label className="block text-gray-700 mb-2">Username</label>
                  <input
                    type="text"
                    value={authForm.username}
                    onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-gray-700 mb-2">Password</label>
                  <input
                    type="password"
                    value={authForm.password}
                    onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition"
                >
                  {isRegistering ? 'Register' : 'Login'}
                </button>
              </form>
              <p className="text-center mt-4 text-gray-600">
                {isRegistering ? 'Already have an account?' : "Don't have an account?"}
                <button
                  onClick={() => setIsRegistering(!isRegistering)}
                  className="text-purple-600 font-semibold ml-2 hover:underline"
                >
                  {isRegistering ? 'Login' : 'Register'}
                </button>
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="text-center mb-8 flex items-center justify-between">
              <div className="text-left">
                <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                  <Wallet className="w-10 h-10" />
                  Personal Finance Tracker
                </h1>
                <p className="text-white/80">Track your income and expenses</p>
              </div>
              <button
                onClick={handleLogout}
                className="bg-white/20 text-white px-4 py-2 rounded-lg hover:bg-white/30 transition"
              >
                Logout
              </button>
            </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-6 h-6 text-green-500" />
              <span className="text-gray-600">Total Income</span>
            </div>
            <p className="text-3xl font-bold text-green-600">${summary.income.toFixed(2)}</p>
          </div>
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-2">
              <TrendingDown className="w-6 h-6 text-red-500" />
              <span className="text-gray-600">Total Expenses</span>
            </div>
            <p className="text-3xl font-bold text-red-600">${summary.expenses.toFixed(2)}</p>
          </div>
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-2">
              <Wallet className="w-6 h-6 text-blue-500" />
              <span className="text-gray-600">Balance</span>
            </div>
            <p className={`text-3xl font-bold ${summary.balance >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
              ${summary.balance.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-white text-purple-600 px-6 py-3 rounded-lg font-semibold hover:bg-purple-50 transition flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Transaction
          </button>
          <button
            onClick={applyRecurring}
            className="bg-white text-purple-600 px-6 py-3 rounded-lg font-semibold hover:bg-purple-50 transition flex items-center gap-2"
          >
            <RefreshCw className="w-5 h-5" />
            Apply Recurring
          </button>
          <button
            onClick={getRecommendations}
            disabled={loadingRecommendations}
            className="bg-gradient-to-r from-green-500 to-teal-500 text-white px-6 py-3 rounded-lg font-semibold hover:from-green-600 hover:to-teal-600 transition flex items-center gap-2 disabled:opacity-50"
          >
            <MessageCircle className="w-5 h-5" />
            {loadingRecommendations ? 'Loading...' : 'AI Recommendations'}
          </button>
          <button
            onClick={clearAll}
            className="bg-red-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-red-600 transition"
          >
            Clear All
          </button>
        </div>

        {/* Add Transaction Form */}
        {showForm && (
          <div className="bg-white rounded-xl p-6 shadow-lg mb-8">
            <h2 className="text-2xl font-bold mb-4">Add Transaction</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-700 mb-2">Type</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value, category: e.target.value === 'Expense' ? 'Dine out' : 'Job' })}
                    className="w-full p-3 border rounded-lg"
                  >
                    <option value="Expense">Expense</option>
                    <option value="Income">Income</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 mb-2">Amount ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-gray-700 mb-2">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                  >
                    {(formData.type === 'Expense' ? expenseCategories : incomeCategories).map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 mb-2">Date</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                    required
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-gray-700 mb-2">Description (optional)</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full p-3 border rounded-lg"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.isRecurring}
                      onChange={(e) => setFormData({ ...formData, isRecurring: e.target.checked })}
                      className="w-5 h-5"
                    />
                    <span className="text-gray-700">Will this be a recurring transaction?</span>
                  </label>
                </div>
                {formData.isRecurring && (
                  <div className="md:col-span-2">
                    <label className="block text-gray-700 mb-2">Interval</label>
                    <select
                      value={formData.interval}
                      onChange={(e) => setFormData({ ...formData, interval: e.target.value })}
                      className="w-full p-3 border rounded-lg"
                    >
                      <option value="weekly">Weekly</option>
                      <option value="biweekly">Biweekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="yearly">Yearly</option>
                    </select>
                  </div>
                )}
              </div>
              <button
                type="submit"
                className="w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition"
              >
                Add Transaction
              </button>
            </form>
          </div>
        )}

        {/* Transaction History */}
        <div className="bg-white rounded-xl p-6 shadow-lg mb-8">
          <h2 className="text-2xl font-bold mb-4">Transaction History</h2>
          {transactions.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No transactions yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3">Date</th>
                    <th className="text-left p-3">Type</th>
                    <th className="text-left p-3">Category</th>
                    <th className="text-left p-3">Amount</th>
                    <th className="text-left p-3">Description</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((trans) => (
                    <tr key={trans.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">{trans.date}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-sm ${trans.type === 'Income' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {trans.type}
                        </span>
                      </td>
                      <td className="p-3">{trans.category}</td>
                      <td className={`p-3 font-semibold ${trans.type === 'Income' ? 'text-green-600' : 'text-red-600'}`}>
                        ${trans.amount.toFixed(2)}
                      </td>
                      <td className="p-3 text-gray-600">{trans.description || '-'}</td>
                      <td className="p-3">
                        <button
                          onClick={() => deleteTransaction(trans.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recurring Transactions */}
        {recurringTransactions.length > 0 && (
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <h2 className="text-2xl font-bold mb-4">Recurring Transactions</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3">Type</th>
                    <th className="text-left p-3">Category</th>
                    <th className="text-left p-3">Amount</th>
                    <th className="text-left p-3">Interval</th>
                    <th className="text-left p-3">Last Applied</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recurringTransactions.map((trans) => (
                    <tr key={trans.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-sm ${trans.type === 'Income' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {trans.type}
                        </span>
                      </td>
                      <td className="p-3">{trans.category}</td>
                      <td className={`p-3 font-semibold ${trans.type === 'Income' ? 'text-green-600' : 'text-red-600'}`}>
                        ${trans.amount.toFixed(2)}
                      </td>
                      <td className="p-3 capitalize">{trans.interval || 'monthly'}</td>
                      <td className="p-3">{trans.last_applied}</td>
                      <td className="p-3">
                        <button
                          onClick={() => deleteRecurring(trans.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* AI Recommendations Modal */}
        {showRecommendations && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl p-6 shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  <MessageCircle className="w-6 h-6 text-green-500" />
                  AI Financial Recommendations
                </h2>
                <button
                  onClick={() => setShowRecommendations(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="prose prose-sm max-w-none">
                <p className="whitespace-pre-wrap text-gray-700">{recommendations}</p>
              </div>
            </div>
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
