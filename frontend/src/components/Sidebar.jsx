import { useEffect, useRef, useState } from "react";
import UploadButton from "./UploadButton";
import DocumentList from "./DocumentList";

function Sidebar({
  selectedConversationId,
  onSelectConversation,
  refreshTrigger,
  selectedDocumentId,
  onSelectDocument,
}) {
  const [conversations, setConversations] = useState([]);
  const [documentRefresh, setDocumentRefresh] = useState(0);

  const [loadingConversations, setLoadingConversations] =
    useState(true);

  const [conversationError, setConversationError] =
    useState("");

  const [creatingConversation, setCreatingConversation] =
    useState(false);

  const [deletingConversationId, setDeletingConversationId] =
    useState(null);

  const [actionError, setActionError] = useState("");

  const actionErrorTimeoutRef = useRef(null);

  function showActionError(message) {
    if (actionErrorTimeoutRef.current) {
      clearTimeout(actionErrorTimeoutRef.current);
    }

    setActionError(message);

    actionErrorTimeoutRef.current = setTimeout(() => {
      setActionError("");
      actionErrorTimeoutRef.current = null;
    }, 4000);
  }

  useEffect(() => {
    return () => {
      if (actionErrorTimeoutRef.current) {
        clearTimeout(actionErrorTimeoutRef.current);
      }
    };
  }, []);

  async function loadConversations() {
    setLoadingConversations(true);
    setConversationError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/conversations"
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to load conversations."
        );
      }

      setConversations(data.conversations || []);
    } catch (error) {
      console.error(
        "Failed to load conversations:",
        error
      );

      setConversationError(
        error.message ||
          "Unable to load conversations."
      );
    } finally {
      setLoadingConversations(false);
    }
  }

  useEffect(() => {
    loadConversations();
  }, [refreshTrigger]);

  async function createConversation() {
    if (creatingConversation) {
      return;
    }

    setCreatingConversation(true);
    setActionError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/conversations",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: "New Conversation",
          }),
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Failed to create conversation."
        );
      }

      setConversations((currentConversations) => [
        data,
        ...currentConversations,
      ]);

      onSelectConversation(data.conversation_id);
    } catch (error) {
      console.error(
        "Failed to create conversation:",
        error
      );

      showActionError(
        error.message ||
          "Unable to create a new conversation."
      );
    } finally {
      setCreatingConversation(false);
    }
  }

  async function handleDeleteConversation(conversation) {
    if (deletingConversationId) {
      return;
    }

    const confirmed = window.confirm(
      `Do you want to delete this conversation?\n\n"${conversation.title}"\n\nThis will permanently remove the conversation and its messages.`
    );

    if (!confirmed) {
      return;
    }

    const conversationId =
      conversation.conversation_id ||
      conversation.id;

    setDeletingConversationId(conversationId);
    setActionError("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/conversations/${conversationId}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Failed to delete conversation."
        );
      }

      setConversations((currentConversations) =>
        currentConversations.filter(
          (item) =>
            (item.conversation_id || item.id) !==
            conversationId
        )
      );

      if (selectedConversationId === conversationId) {
        onSelectConversation(null);
      }
    } catch (error) {
      console.error(
        "Failed to delete conversation:",
        error
      );

      showActionError(
        error.message ||
          "Unable to delete the conversation."
      );
    } finally {
      setDeletingConversationId(null);
    }
  }

  return (
    <aside className="sidebar">
      <h2>AI Knowledge Assistant</h2>

      <div className="sidebar-actions">
        <button
          className="new-conversation-button"
          type="button"
          onClick={createConversation}
          disabled={creatingConversation}
        >
          {creatingConversation
            ? "Creating..."
            : "+ New Chat"}
        </button>

        <div className="upload-wrapper">
          <UploadButton
            onUploadSuccess={() => {
              setDocumentRefresh(
                (current) => current + 1
              );
            }}
          />
        </div>
      </div>

      {actionError && (
        <div className="sidebar-action-error">
          {actionError}
        </div>
      )}

      <div className="sidebar-content">
        <DocumentList
          refreshTrigger={documentRefresh}
          selectedDocumentId={selectedDocumentId}
          onSelectDocument={onSelectDocument}
        />

        <h3>Conversations</h3>

        <div className="conversation-list">
          {loadingConversations ? (
            <p className="conversation-status">
              Loading conversations...
            </p>
          ) : conversationError ? (
            <div className="conversation-error">
              <p>{conversationError}</p>

              <button
                className="retry-button"
                type="button"
                onClick={loadConversations}
              >
                Retry
              </button>
            </div>
          ) : conversations.length === 0 ? (
            <p className="conversation-status">
              No conversations yet.
            </p>
          ) : (
            conversations.map((conversation) => {
              const conversationId =
                conversation.conversation_id ||
                conversation.id;

              const isDeleting =
                deletingConversationId ===
                conversationId;

              return (
                <div
                  className="conversation-item"
                  key={conversationId}
                >
                  <button
                    className={`conversation-button ${
                      selectedConversationId ===
                      conversationId
                        ? "selected"
                        : ""
                    }`}
                    type="button"
                    onClick={() =>
                      onSelectConversation(
                        conversationId
                      )
                    }
                    disabled={isDeleting}
                    title={conversation.title}
                  >
                    {conversation.title}
                  </button>

                  <button
                    className="conversation-delete-button"
                    type="button"
                    title="Delete conversation"
                    aria-label={`Delete ${conversation.title}`}
                    onClick={() =>
                      handleDeleteConversation(
                        conversation
                      )
                    }
                    disabled={isDeleting}
                  >
                    {isDeleting ? "..." : "🗑️"}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;