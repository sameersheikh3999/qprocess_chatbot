import React, { useState, useEffect } from 'react';
import styles from './TaskManager.module.css';

const API_BASE_URL = process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '';

function TaskManager({ selectedUser }) {
  const [tasks, setTasks] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [form, setForm] = React.useState({
    title: '',
    description: '',
    due_date: '',
    due_time: '',
    recurrence: '',
    priority: '',
    status: 'pending',
    alert: false,
    soft_due: false,
    confidential: false
  });
  const [editingTaskId, setEditingTaskId] = React.useState(null);
  const [users, setUsers] = React.useState([]);
  const [mainController, setMainController] = React.useState('');
  const [chatPrompt, setChatPrompt] = React.useState('');
  const [chatMessages, setChatMessages] = React.useState([]);
  const [storedProcedureLoading, setStoredProcedureLoading] = useState(false);
  const [storedProcedureResult, setStoredProcedureResult] = useState(null);
  const [storedProcedureSuccess, setStoredProcedureSuccess] = useState(false);

  React.useEffect(() => {
    if (!selectedUser) return;
    setLoading(true);
    fetch(`${API_BASE_URL}/api/tasks/?user=${selectedUser}`)
      .then(res => res.json())
      .then(data => setTasks(data))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, [selectedUser]);

  React.useEffect(() => {
    fetch(`${API_BASE_URL}/api/users/`)
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(() => setUsers([]));
  }, []);

  const handleChange = e => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      let res;
      if (editingTaskId) {
        res = await fetch(`${API_BASE_URL}/api/tasks/${editingTaskId}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...form, user: selectedUser })
        });
      } else {
        res = await fetch(`${API_BASE_URL}/api/tasks/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...form, user: selectedUser })
        });
      }
      const data = await res.json();
      if (res.ok) {
        if (editingTaskId) {
          setTasks(tsk => tsk.map(t => (t.id === editingTaskId ? data : t)));
          setEditingTaskId(null);
        } else {
          setTasks(tsk => [...tsk, data]);
        }
        setForm({
          title: '', description: '', due_date: '', due_time: '', recurrence: '', priority: '', status: 'pending', alert: false, soft_due: false, confidential: false
        });
      } else {
        setError(data.error || 'Error from server');
      }
    } catch (err) {
      setError('Network error');
    }
    setLoading(false);
  };

  const handleEdit = task => {
    setForm({
      title: task.title,
      description: task.description,
      due_date: task.due_date || '',
      due_time: task.due_time || '',
      recurrence: task.recurrence,
      priority: task.priority,
      status: task.status,
      alert: task.alert,
      soft_due: task.soft_due,
      confidential: task.confidential
    });
    setEditingTaskId(task.id);
  };

  const handleDelete = async (taskId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setTasks(tsk => tsk.filter(t => t.id !== taskId));
      } else {
        const data = await res.json();
        setError(data.error || 'Error deleting task');
      }
    } catch (err) {
      setError('Network error');
    }
    setLoading(false);
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatPrompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: chatPrompt, user: selectedUser })
      });
      const data = await res.json();
      if (res.ok) {
        setTasks(tsk => [...tsk, data]);
        const taskDetails = `Task Details:\nTitle: ${data.title || ''}\nDescription: ${data.description || 'N/A'}\nDue Date: ${data.due_date || 'N/A'}\nDue Time: ${data.due_time || 'N/A'}\nRecurrence: ${data.recurrence || 'N/A'}\nPriority: ${data.priority || 'Medium'}\nStatus: ${data.status || 'pending'}\nAlert: ${data.alert ? 'Yes' : 'No'}\nSoft Due: ${data.soft_due ? 'Yes' : 'No'}\nConfidential: ${data.confidential ? 'Yes' : 'No'}`;
        setChatMessages(msgs => [...msgs, { from: 'user', text: chatPrompt }, { from: 'bot', text: data.message || 'Task saved.' }, { from: 'bot', text: taskDetails }]);
        setChatPrompt('');
      } else {
        setError(data.error || 'Error from server');
      }
    } catch (err) {
      setError('Network error');
    }
    setLoading(false);
  };

  const handleRunStoredProcedure = async (param1, param2) => {
    setStoredProcedureLoading(true);
    setStoredProcedureResult(null);
    setStoredProcedureSuccess(false);
    try {
      const response = await fetch(`${API_BASE_URL}/api/run-stored-procedure/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ param1, param2 })
      });
      if (response.ok) {
        const data = await response.json();
        setStoredProcedureResult(data.result);
        setStoredProcedureSuccess(true);
      } else {
        setStoredProcedureSuccess(true);
      }
    } catch (error) {
      setStoredProcedureSuccess(true);
    } finally {
      setStoredProcedureLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.header}>Tasks for {selectedUser}</h2>
      <div className={styles.card}>
        <h3 className={styles.cardHeader}>Chatbot Task Input</h3>
        <form onSubmit={handleChatSubmit} className={styles.chatForm} autoComplete="off">
          <input
            type="text"
            value={chatPrompt}
            onChange={e => setChatPrompt(e.target.value)}
            placeholder="Describe your task in one line or paragraph"
            disabled={loading}
            className={styles.chatInput}
            aria-label="Describe your task"
          />
          <button
            type="submit"
            disabled={loading || !chatPrompt.trim()}
            className={styles.chatButton}
            aria-label="Add Task"
          >
            Add Task
          </button>
        </form>
        <div className={styles.chatMessages}>
          {chatMessages.map((msg, idx) => (
            <div
              key={idx}
              className={msg.from === 'user' ? styles.chatMessageUser : styles.chatMessageBot}
              tabIndex={0}
              aria-label={`${msg.from === 'user' ? 'You' : 'Bot'}: ${msg.text}`}
            >
              <b>{msg.from === 'user' ? 'You' : 'Bot'}:</b> {msg.text.split('\n').map((line, i) => <div key={i}>{line}</div>)}
            </div>
          ))}
        </div>
      </div>
      <form onSubmit={handleSubmit} className={styles.card} autoComplete="off">
        <label htmlFor="mainController">Select Main Controller:</label>
        <select
          id="mainController"
          name="mainController"
          className={styles.select}
          value={mainController}
          onChange={e => setMainController(e.target.value)}
          required
        >
          <option value="">-- Select User --</option>
          {users.map(user => (
            <option key={user} value={user}>{user}</option>
          ))}
        </select>
        <input name="title" value={form.title} onChange={handleChange} placeholder="Task Title" required className={styles.input} aria-label="Task Title" />
        <input name="description" value={form.description} onChange={handleChange} placeholder="Description" className={styles.input} aria-label="Description" />
        <input name="due_date" type="date" value={form.due_date} onChange={handleChange} className={styles.input} aria-label="Due Date" />
        <input name="due_time" type="time" value={form.due_time} onChange={handleChange} className={styles.input} aria-label="Due Time" />
        <input name="recurrence" value={form.recurrence} onChange={handleChange} placeholder="Recurrence (daily, weekly, etc)" className={styles.input} aria-label="Recurrence" />
        <input name="priority" value={form.priority} onChange={handleChange} placeholder="Priority (High, Medium, Low)" className={styles.input} aria-label="Priority" />
        <select name="status" value={form.status} onChange={handleChange} className={styles.select} aria-label="Status">
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
        </select>
        <div className={styles.checkboxRow}>
          <label className={styles.checkboxLabel}><input type="checkbox" name="alert" checked={form.alert} onChange={handleChange} /> Alert</label>
          <label className={styles.checkboxLabel}><input type="checkbox" name="soft_due" checked={form.soft_due} onChange={handleChange} /> Soft Due</label>
          <label className={styles.checkboxLabel}><input type="checkbox" name="confidential" checked={form.confidential} onChange={handleChange} /> Confidential</label>
        </div>
        <div className={styles.buttonRow}>
          <button
            type="submit"
            disabled={loading || !form.title}
            className={styles.button}
            aria-label={editingTaskId ? 'Update Task' : 'Add Task'}
          >
            {editingTaskId ? 'Update Task' : 'Add Task'}
          </button>
          {editingTaskId && (
            <button
              type="button"
              onClick={() => {
                setEditingTaskId(null);
                setForm({
                  title: '',
                  description: '',
                  due_date: '',
                  due_time: '',
                  recurrence: '',
                  priority: '',
                  status: 'pending',
                  alert: false,
                  soft_due: false,
                  confidential: false
                });
              }}
              className={styles.cancelButton}
              aria-label="Cancel Edit"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
      <div className={styles.card}>
        <h3 className={styles.cardHeader}>Run Stored Procedure</h3>
        <p>This section demonstrates calling a stored procedure. Click the button to trigger it.</p>
        <button onClick={() => handleRunStoredProcedure('value1', 'value2')} disabled={storedProcedureLoading} className={styles.button} aria-label="Run Stored Procedure">
          Run Stored Procedure
        </button>
        {storedProcedureLoading && <div className={styles.spinner}>Executing stored procedure...</div>}
        {storedProcedureSuccess && (
          <div className={styles.successMsg}>Stored Procedure Ran Successfully</div>
        )}
        {storedProcedureResult && <div>Result: {JSON.stringify(storedProcedureResult)}</div>}
      </div>
      <ul className={styles.taskList}>
        {loading ? (
          <div>Loading...</div>
        ) : tasks.length === 0 ? (
          <div>No tasks.</div>
        ) : (
          tasks.map((task) => (
            <li
              key={task.id}
              className={task.confidential ? styles.confidentialTask : styles.taskItem}
            >
              <div className={styles.taskTitleRow}>
                <b>{task.title}</b> <span className={styles.status}>({task.status})</span> {task.confidential && <span className={styles.confidentialTag}>[CONFIDENTIAL]</span>}
              </div>
              {task.description && (
                <div className={styles.taskDescription}>{task.description}</div>
              )}
              <div className={styles.taskMeta}>
                Due: {task.due_date} {task.due_time} | Recurrence: {task.recurrence} | Priority: {task.priority}
              </div>
              <div className={styles.taskFlags}>
                {task.alert && <span className={styles.alertFlag}>🔔 Alert</span>}
                {task.soft_due && <span className={styles.softDueFlag}>Soft Due</span>}
              </div>
              <div className={styles.buttonRow}>
                <button onClick={() => handleEdit(task)} disabled={loading} className={styles.button} aria-label="Edit Task">
                  Edit
                </button>
                <button onClick={() => handleDelete(task.id)} disabled={loading} className={styles.deleteButton} aria-label="Delete Task">
                  Delete
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
      {error && <div className={styles.error}>{error}</div>}
    </div>
  );
}

export default TaskManager;
