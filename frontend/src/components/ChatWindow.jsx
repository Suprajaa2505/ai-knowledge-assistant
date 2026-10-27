import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

function getUniqueSources(sources) {
  const uniqueSources = [];
  const seen = new Set();

  for (const source of sources) {
    const key = `${source.document_id}-${source.page ?? "document"}`;

    if (!seen.has(key)) {
      seen.add(key);
      uniqueSources.push(source);
    }
  }

  return uniqueSources;
}

function ChatWindow({
  conversationId,
  selectedDocumentId,
  selectedDocumentName,
  onConversationTitleUpdate,
}) {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");

  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] =
    useState(false);

  const [messageLoadError, setMessageLoadError] =
    useState("");

  const [chatError, setChatError] = useState("");

  async function loadMessages() {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    setLoadingMessages(true);
    setMessageLoadError("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/conversations/${conversationId}/messages`
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to load messages."
        );
      }

      setMessages(data.messages || []);
    } catch (error) {
      console.error(
        "Failed to load messages:",
        error
      );

      setMessageLoadError(
        error.message ||
          "Unable to load conversation messages."
      );
    } finally {
      setLoadingMessages(false);
    }
  }

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setMessageLoadError("");
      setChatError("");
      return;
    }

    loadMessages();
  }, [conversationId]);

  async function sendMessage() {
    if (!query.trim() || !conversationId || loading) {
      return;
    }

    const userQuery = query.trim();

    setQuery("");
    setLoading(true);
    setChatError("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/conversations/${conversationId}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: userQuery,
            top_k: 3,
            document_id: selectedDocumentId,
          }),
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to send message."
        );
      }

      if (!data?.answer) {
        throw new Error(
          "The assistant returned an empty response."
        );
      }

      if (data.conversation_title) {
        onConversationTitleUpdate();
      }

      const messageId = Date.now();

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `user-${messageId}`,
          role: "user",
          content: userQuery,
          sources: [],
        },
        {
          id: `assistant-${messageId}`,
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (error) {
      console.error(
        "Failed to send message:",
        error
      );

      setQuery(userQuery);

      setChatError(
        error.message ||
          "Unable to get a response from the assistant."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <section className="chat-window">
      <header className="chat-header">
        <h1>AI Knowledge Assistant</h1>
      </header>

      {!conversationId ? (
        <div className="empty-chat">
          <div>
            <div className="empty-chat-icon">
              🤖
            </div>

            <h2>AI Knowledge Assistant</h2>

            <p>
              Select a conversation to start chatting.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="active-document-filter">
            Searching:{" "}
            <strong>
              {selectedDocumentName ||
                "All Documents"}
            </strong>
          </div>

          {chatError && (
            <div className="chat-error">
              <span>{chatError}</span>

              <button
                type="button"
                onClick={() => setChatError("")}
              >
                Dismiss
              </button>
            </div>
          )}

          <div className="messages-container">
            {loadingMessages ? (
              <div className="message-status">
                <span className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>

                <span>
                  Loading conversation...
                </span>
              </div>
            ) : messageLoadError ? (
              <div className="message-error">
                <div className="empty-chat-icon">
                  ⚠️
                </div>

                <h2>
                  Couldn't load this conversation
                </h2>

                <p>{messageLoadError}</p>

                <button
                  className="retry-button"
                  type="button"
                  onClick={loadMessages}
                >
                  Retry
                </button>
              </div>
            ) : messages.length === 0 ? (
              <div className="empty-chat">
                <div>
                  <div className="empty-chat-icon">
                    🤖
                  </div>

                  <h2>Ask your documents</h2>

                  <p>
                    Ask a question about the
                    documents you've uploaded.
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-row ${message.role}`}
                >
                  {message.role === "assistant" && (
                    <div className="assistant-avatar">
                      🤖
                    </div>
                  )}

                  <div className="message">
                    {message.role === "user" ? (
                      <div className="user-message">
                        {message.content}
                      </div>
                    ) : (
                      <>
                        <div className="assistant-message">
                          <ReactMarkdown>
                            {message.content}
                          </ReactMarkdown>
                        </div>

                        {message.sources &&
                          message.sources.length > 0 && (
                            <div className="sources">
                              <button
                                className="sources-button"
                                type="button"
                              >
                                Sources ·{" "}
                                {
                                  getUniqueSources(
                                    message.sources
                                  ).length
                                }
                              </button>

                              <div className="sources-popover">
                                {getUniqueSources(
                                  message.sources
                                ).map(
                                  (
                                    source,
                                    index
                                  ) => (
                                    <div
                                      className="source-detail"
                                      key={`${source.document_id}-${source.page}-${index}`}
                                    >
                                      <div className="source-document">
                                        📄{" "}
                                        {
                                          source.source
                                        }
                                      </div>

                                      {source.page !==
                                        null &&
                                        source.page !==
                                          undefined && (
                                          <div className="source-page">
                                            Page{" "}
                                            {
                                              source.page
                                            }
                                          </div>
                                        )}
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                      </>
                    )}
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="message-row assistant">
                <div className="assistant-avatar">
                  🤖
                </div>

                <div className="message">
                  <div className="assistant-loading">
                    <span className="loading-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </span>

                    <span>
                      Thinking...
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="chat-input-area">
            <div className="chat-input-wrapper">
              <textarea
                className="chat-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                onKeyDown={handleKeyDown}
                placeholder="Ask something about your documents..."
                disabled={loading}
                rows={1}
              />

              <button
                className="send-button"
                onClick={sendMessage}
                disabled={
                  loading || !query.trim()
                }
              >
                {loading ? "..." : "Send"}
              </button>
            </div>

            <p className="input-hint">
              Press Enter to send
            </p>
          </div>
        </>
      )}
    </section>
  );
}

export default ChatWindow;