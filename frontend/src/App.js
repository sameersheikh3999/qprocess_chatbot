import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  // Add a new state for stored procedure success
  const [storedProcedureSuccess, setStoredProcedureSuccess] = useState(false);
  // Add timezone state
  const [userTimezone, setUserTimezone] = useState('');

  useEffect(() => {
    // Detect user's timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    setUserTimezone(timezone);
    
    // Fetch users from backend
    fetch(`${API_BASE_URL}/api/users/`)
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(() => setUsers([]));
  }, []);

  const parseTaskList = (text) => {
    // Simple parser to detect task list lines and format them
    const lines = text.split('\n');
    const taskLines = lines.filter(line => line.trim().length > 0);
    if (taskLines.length === 0) return text;
    return (
      <ul>
        {taskLines.map((line, idx) => (
          <li key={idx}>{line}</li>
        ))}
      </ul>
    );
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !selectedUser) return;
    const userMsg = { sender: 'user', text: input, timestamp: new Date().toISOString() };
    setMessages((msgs) => [...msgs, userMsg]);
    setLoading(true);
    setError(null);
    setStoredProcedureSuccess(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: input, 
          user: selectedUser,
          timezone: userTimezone 
        })
      });
      const data = await res.json();
      if (res.ok) {
        // Check if reply indicates stored procedure success
        if (data.reply && data.reply.toLowerCase().includes('task created')) {
          setStoredProcedureSuccess(true);
          // Also show the success message in chat
          const botMsg = { sender: 'bot', text: data.reply, timestamp: new Date().toISOString() };
          setMessages((msgs) => [...msgs, botMsg]);
        } else {
          // Regular bot response
          let botMsgContent = data.reply;
          const isTaskList = botMsgContent.includes('\n');
          const botMsg = { sender: 'bot', text: botMsgContent, timestamp: new Date().toISOString(), isTaskList };
          setMessages((msgs) => [...msgs, botMsg]);
        }
      } else {
        // HTTP error case
          setError(data.error || 'Error from server');
      }
    } catch (err) {
      // Actual network error
      setError('Network error: Unable to connect to server');
    }
    setInput('');
    setLoading(false);
  };

  return (
    <div className="app-container">
      <div className="chat-container">
        <h1>Acme Chatbot</h1>
        {/* Display detected timezone */}
        {userTimezone && (
          <div style={{ 
            fontSize: '12px', 
            color: '#666', 
            marginBottom: '10px',
            padding: '5px 10px',
            backgroundColor: '#f5f5f5',
            borderRadius: '4px',
            display: 'inline-block'
          }}>
            📍 Timezone: {userTimezone}
          </div>
        )}
        <div className="chat-box">
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.sender === 'user' ? 'user-msg' : 'bot-msg'}>
              <b>{msg.sender === 'user' ? 'You' : 'Bot'}:</b> 
              {msg.isTaskList ? parseTaskList(msg.text) : msg.text}
              <div className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</div>
            </div>
          ))}
          {loading && <div className="bot-msg">Bot is typing...</div>}
        </div>
        {/* Show success message if stored procedure ran */}
        {storedProcedureSuccess && (
          <div style={{ color: 'green', marginTop: 8 }}>Task Created Successfully!</div>
        )}
        {/* Only show error if not a stored procedure success */}
        {!storedProcedureSuccess && error && <div className="error">{error}</div>}
        <form onSubmit={sendMessage} className="chat-form">
          <select value={selectedUser} onChange={e => setSelectedUser(e.target.value)} required>
            <option value="">Select User</option>
            {users.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(e);
              }
            }}
            placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
            disabled={loading}
            rows="3"
          />
          <button type="submit" disabled={loading || !input.trim() || !selectedUser}>Send</button>
        </form>
      </div>
    </div>
  );
}

export default App;
