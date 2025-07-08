import React, { useState, useEffect, useCallback } from 'react';
import { postChatMessage, fetchDocumentCount } from '../api';
import './ChatView.css';

function ChatView() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [docCountInfo, setDocCountInfo] = useState('');
  const [error, setError] = useState('');

  const getDocCount = useCallback(async () => {
    try {
      const data = await fetchDocumentCount();
      setDocCountInfo(data.message || `${data.count} document chunks in the knowledge base.`);
      if (data.count === 0) {
        setDocCountInfo("⚠️ No documents found. Please upload documents in the 'Upload Documents' tab.");
      }
    } catch (err) {
      setDocCountInfo('⚠️ Could not fetch document count.');
      console.error(err);
    }
  }, []);

  useEffect(() => {
    getDocCount();
  }, [getDocCount]);

  const handleSend = async () => {
    if (!input.trim()) return;
    setError('');
    const newUserMessage = { role: 'user', content: input };
    setMessages(prevMessages => [...prevMessages, newUserMessage]);
    setInput('');
    setIsLoading(true);

    // Prepare chat history for the API
    const apiChatHistory = messages.map(msg => ({ role: msg.role, content: msg.content }));

    try {
      // Fetch doc count again before sending, in case it changed and user hasn't seen the update
      const currentDocCountData = await fetchDocumentCount();
      if (currentDocCountData.count === 0) {
        const noDocsError = "I don't have any documents to search through. Please upload documents first.";
        setMessages(prevMessages => [...prevMessages, { role: 'assistant', content: noDocsError }]);
        setIsLoading(false);
        return;
      }

      const data = await postChatMessage(input, apiChatHistory);
      setMessages(prevMessages => [...prevMessages, { role: 'assistant', content: data.ai_message }]);
    } catch (err) {
      console.error("Chat API error:", err);
      setError(`Error: ${err.message || 'Failed to get response from assistant.'}`);
      setMessages(prevMessages => [...prevMessages, { role: 'assistant', content: `Sorry, I encountered an error: ${err.message}` }]);
    }
    setIsLoading(false);
  };

  return (
    <div className="chat-view">
      <div className="doc-count-info">{docCountInfo}</div>
      {error && <div className="error-message">{error}</div>}
      <div className="message-list">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-bubble">
              <strong>{msg.role === 'user' ? 'You' : 'Assistant'}:</strong> {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-bubble">
              <strong>Assistant:</strong> Thinking...
            </div>
          </div>
        )}
      </div>
      <div className="input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents..."
          rows="3"
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default ChatView;
