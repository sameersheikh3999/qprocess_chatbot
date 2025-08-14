import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [storedProcedureSuccess, setStoredProcedureSuccess] = useState(false);
  const [userTimezone, setUserTimezone] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isUserFromStorage, setIsUserFromStorage] = useState(false);
  const [showStorageNotification, setShowStorageNotification] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState('thinking'); // 'thinking' or 'typing'
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Detect user's timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    setUserTimezone(timezone);
    
    // Load selected user from localStorage
    const savedUser = localStorage.getItem('acmeChatbotSelectedUser');
    if (savedUser) {
      setSelectedUser(savedUser);
      setIsUserFromStorage(true);
      setShowStorageNotification(true); // Show notification for restored user
    }
    
    // Fetch users from backend
    fetch(`${API_BASE_URL}/api/users/`)
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(() => setUsers([]));
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Auto-resize textarea function
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      
      // Calculate new height based on content
      const newHeight = Math.min(textarea.scrollHeight, 200); // Max height of 200px
      textarea.style.height = `${newHeight}px`;
    }
  };

  // Handle input change with auto-resize
  const handleInputChange = (e) => {
    setInput(e.target.value);
    // Use setTimeout to ensure the value is updated before adjusting height
    setTimeout(adjustTextareaHeight, 0);
  };

  // Handle user selection with localStorage persistence
  const handleUserSelect = (user) => {
    setSelectedUser(user);
    setIsDropdownOpen(false);
    setIsUserFromStorage(false); // Reset the flag when user manually selects
    
    // Save selected user to localStorage
    localStorage.setItem('acmeChatbotSelectedUser', user);
  };

  // Clear stored user (useful for logout or reset)
  const clearStoredUser = () => {
    setSelectedUser('');
    setIsUserFromStorage(false);
    localStorage.removeItem('acmeChatbotSelectedUser');
  };

  // Validate stored user against available users
  useEffect(() => {
    if (selectedUser && users.length > 0) {
      const userExists = users.includes(selectedUser);
      if (!userExists) {
        // If stored user is no longer available, clear it
        clearStoredUser();
      }
    }
  }, [users, selectedUser]);

  // Auto-hide storage notification after 3 seconds
  useEffect(() => {
    if (showStorageNotification) {
      const timer = setTimeout(() => {
        setShowStorageNotification(false);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [showStorageNotification]);

  const parseTaskList = (text) => {
    const lines = text.split('\n');
    const taskLines = lines.filter(line => line.trim().length > 0);
    if (taskLines.length === 0) return text;
    return (
      <ul className="task-list-parsed">
        {taskLines.map((line, idx) => (
          <li key={idx} className="task-item">
            <span className="task-bullet">•</span>
            <span className="task-text">{line}</span>
          </li>
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
    setIsTyping(true);
    setLoadingPhase('thinking'); // Start with thinking phase
    
    // Switch to typing phase after 3 seconds
    const typingTimer = setTimeout(() => {
      setLoadingPhase('typing');
    }, 3000);
    
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
        if (data.reply && data.reply.toLowerCase().includes('task created')) {
          setStoredProcedureSuccess(true);
          const botMsg = { sender: 'bot', text: data.reply, timestamp: new Date().toISOString() };
          setMessages((msgs) => [...msgs, botMsg]);
        } else {
          let botMsgContent = data.reply;
          const isTaskList = botMsgContent.includes('\n');
          const botMsg = { sender: 'bot', text: botMsgContent, timestamp: new Date().toISOString(), isTaskList };
          setMessages((msgs) => [...msgs, botMsg]);
        }
      } else {
        setError(data.error || 'Error from server');
      }
    } catch (err) {
      setError('Network error: Unable to connect to server');
    }
    
    // Clear the typing timer
    clearTimeout(typingTimer);
    
    setInput('');
    setLoading(false);
    setIsTyping(false);
    setLoadingPhase('thinking'); // Reset to thinking phase
    
    // Reset textarea height after sending
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="app-container">
      <div className="chat-container">
        {/* Enhanced Header */}
        <div className="chat-header">
          <div className="header-content">
            <div className="logo-section">
              <div className="logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              </div>
              <h1>Acme Chatbot</h1>
            </div>
            {userTimezone && (
              <div className="timezone-badge">
                <span className="timezone-icon">🌍</span>
                <span className="timezone-text">{userTimezone}</span>
              </div>
            )}
          </div>
        </div>

        

        {/* Enhanced Chat Box */}
        <div className="chat-box">
          {messages.length === 0 && (
            <div className="welcome-message">
              <div className="welcome-icon">👋</div>
              <h3>Welcome to Acme Chatbot!</h3>
              <p>Select a user and start chatting to get started.</p>
            </div>
          )}
          
          {/* Storage Notification */}
          {showStorageNotification && (
            <div className="storage-notification">
              <span className="storage-icon">💾</span>
              <span>Welcome back! Your previous user selection has been restored.</span>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.sender === 'user' ? 'user-msg' : 'bot-msg'}`}>
              <div className="message-avatar">
                {msg.sender === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-header">
                  <span className="message-sender">
                    {msg.sender === 'user' ? 'You' : 'Acme Bot'}
                  </span>
                  <span className="message-time">{formatTime(msg.timestamp)}</span>
                </div>
                <div className="message-text">
                  {msg.isTaskList ? parseTaskList(msg.text) : msg.text}
                </div>
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className={`message bot-msg typing-indicator ${loadingPhase}`}>
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-text">
                  {loadingPhase === 'thinking' ? 'Bot is thinking...' : 'Bot is typing...'}
                </div>
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Success/Error Messages */}
        {storedProcedureSuccess && (
          <div className="success-message">
            <span className="success-icon">✅</span>
            <span>Task Created Successfully!</span>
          </div>
        )}
        
        {!storedProcedureSuccess && error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Enhanced Chat Form */}
        <form onSubmit={sendMessage} className="chat-form">
          {/* User Selection - Custom Dropdown */}
        <div className="user-selection-section">
          <div className="custom-dropdown" ref={dropdownRef}>
            <button
              type="button"
              className="dropdown-trigger"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            >
              <span className="dropdown-text">
                {selectedUser ? `👤 ${selectedUser}` : '👤 Select User'}
              </span>
              {isUserFromStorage && (
                <span className="dropdown-indicator">
                  💾
                </span>
              )}
              <svg 
                className={`dropdown-arrow ${isDropdownOpen ? 'open' : ''}`}
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2"
              >
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </button>
            
            {isDropdownOpen && (
              <div className="dropdown-menu">
                {users.map(user => (
                  <button
                    key={user}
                    type="button"
                    className={`dropdown-option ${selectedUser === user ? 'selected' : ''}`}
                    onClick={() => handleUserSelect(user)}
                  >
                    👤 {user}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
          <div className="input-row">
            <div className="textarea-wrapper">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(e);
                  }
                  // Add Ctrl+Enter support
                  if (e.key === 'Enter' && e.ctrlKey) {
                    e.preventDefault();
                    sendMessage(e);
                  }
                }}
                placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                disabled={loading}
                rows="1"
                className="message-input auto-resize"
              />
            </div>
            <div className="button-group">
              <button 
                type="submit" 
                disabled={loading || !input.trim() || !selectedUser}
                className="send-button"
              >
                {loading ? (
                  <span className="loading-spinner"></span>
                ) : (
                  <>
                    <span className="send-icon">📤</span>
                    <span className="send-text">Send</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;
