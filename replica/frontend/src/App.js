import React, { useState } from 'react';
import './App.css';
import ChatView from './components/ChatView';
import UploadDocumentsView from './components/UploadDocumentsView';
import DebugInfoView from './components/DebugInfoView';
// import VoiceAssistantView from './components/VoiceAssistantView'; // Placeholder for now

function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat', 'upload', 'debug'

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatView />;
      case 'upload':
        return <UploadDocumentsView />;
      case 'debug':
        return <DebugInfoView />;
      // case 'voice':
      //   return <VoiceAssistantView />;
      default:
        return <ChatView />;
    }
  };

  return (
    <div className="App">
      <nav className="App-nav">
        <button onClick={() => setActiveTab('chat')} className={activeTab === 'chat' ? 'active' : ''}>
          Chat
        </button>
        <button onClick={() => setActiveTab('upload')} className={activeTab === 'upload' ? 'active' : ''}>
          Upload Documents
        </button>
        {/* <button onClick={() => setActiveTab('voice')} className={activeTab === 'voice' ? 'active' : ''}>
          Voice Assistant (Coming Soon)
        </button> */}
        <button onClick={() => setActiveTab('debug')} className={activeTab === 'debug' ? 'active' : ''}>
          Debug Info
        </button>
      </nav>
      <main className="App-main">
        {renderActiveTab()}
      </main>
      <footer className="App-footer">
        <p>Agentic RAG Chatbot - React Version</p>
      </footer>
    </div>
  );
}

export default App;
