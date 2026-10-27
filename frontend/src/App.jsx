import { useState } from "react";
import "./App.css";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";

function App() {
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [conversationRefresh, setConversationRefresh] = useState(0);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [selectedDocumentName, setSelectedDocumentName] = useState(null);

  return (
    <div className="app">
      <Sidebar
        selectedConversationId={selectedConversationId}
        onSelectConversation={setSelectedConversationId}
        refreshTrigger={conversationRefresh}
        selectedDocumentId={selectedDocumentId}
        onSelectDocument={(documentId, documentName) => {
          setSelectedDocumentId(documentId);
          setSelectedDocumentName(documentName);
        }}
      />

      <main className="main-content">
        <ChatWindow
          conversationId={selectedConversationId}
          selectedDocumentId={selectedDocumentId}
          selectedDocumentName={selectedDocumentName}
          onConversationTitleUpdate={() => {
            setConversationRefresh((current) => current + 1);
          }}
        />
      </main>
    </div>
  );
}

export default App;