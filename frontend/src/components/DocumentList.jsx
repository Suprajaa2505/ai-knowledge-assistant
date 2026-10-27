import { useEffect, useState } from "react";

function DocumentList({
  refreshTrigger,
  selectedDocumentId,
  onSelectDocument,
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [documentError, setDocumentError] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [deletingDocumentId, setDeletingDocumentId] =
    useState(null);

  async function loadDocuments() {
    setLoading(true);
    setDocumentError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/documents"
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to load documents."
        );
      }

      setDocuments(data.documents || []);
    } catch (error) {
      console.error(
        "Failed to load documents:",
        error
      );

      setDocumentError(
        error.message ||
          "Unable to load documents."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, [refreshTrigger]);

  function handleDocumentClick(document) {
    if (deletingDocumentId === document.id) {
      return;
    }

    setSelectedDocument((current) => {
      if (current?.id === document.id) {
        return null;
      }

      return document;
    });
  }

  function handleDocumentSelection(document) {
    if (deletingDocumentId === document.id) {
      return;
    }

    if (selectedDocumentId === document.id) {
      onSelectDocument(null, null);
    } else {
      onSelectDocument(
        document.id,
        document.filename
      );
    }
  }

  async function handleDeleteDocument(document) {
    if (deletingDocumentId) {
      return;
    }

    const confirmed = window.confirm(
      `Do you want to delete this document?\n\n"${document.filename}"\n\nThis will permanently remove the document and its indexed data.`
    );

    if (!confirmed) {
      return;
    }

    setDeletingDocumentId(document.id);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${document.id}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Failed to delete document."
        );
      }

      setDocuments((currentDocuments) =>
        currentDocuments.filter(
          (item) => item.id !== document.id
        )
      );

      setSelectedDocument((current) => {
        if (current?.id === document.id) {
          return null;
        }

        return current;
      });

      if (selectedDocumentId === document.id) {
        onSelectDocument(null, null);
      }
    } catch (error) {
      console.error(
        "Failed to delete document:",
        error
      );

      window.alert(
        error.message ||
          "Failed to delete document."
      );
    } finally {
      setDeletingDocumentId(null);
    }
  }

  function formatCreatedDate(createdAt) {
    if (!createdAt) {
      return "Unknown";
    }

    const date = new Date(createdAt);

    if (Number.isNaN(date.getTime())) {
      return "Unknown";
    }

    return date.toLocaleDateString(undefined, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  return (
    <div className="document-section">
      <button
        className="documents-toggle"
        type="button"
        onClick={() =>
          setIsOpen((current) => !current)
        }
      >
        <span>Documents</span>

        <span className="documents-toggle-right">
          <span className="document-count">
            {documents.length}
          </span>

          <span
            className={`documents-chevron ${
              isOpen ? "open" : ""
            }`}
          >
            ›
          </span>
        </span>
      </button>

      {isOpen && (
        <div className="document-dropdown">
          {/* All Documents */}
          <div
            className={`document-item ${
              selectedDocumentId === null
                ? "selected"
                : ""
            }`}
          >
            <input
              className="document-checkbox"
              type="checkbox"
              checked={selectedDocumentId === null}
              onChange={() => {
                setSelectedDocument(null);
                onSelectDocument(null, null);
              }}
              aria-label="Search all documents"
              disabled={Boolean(deletingDocumentId)}
            />

            <span className="document-icon">
              📚
            </span>

            <span className="document-name">
              All Documents
            </span>
          </div>

          {loading ? (
            <p className="document-status">
              Loading documents...
            </p>
          ) : documentError ? (
            <div className="document-error">
              <p>{documentError}</p>

              <button
                className="retry-button"
                type="button"
                onClick={loadDocuments}
              >
                Retry
              </button>
            </div>
          ) : documents.length === 0 ? (
            <p className="document-status">
              No documents uploaded.
            </p>
          ) : (
            <div className="document-list-scroll">
              <div className="document-list">
                {documents.map((document) => {
                  const isSelected =
                    selectedDocumentId === document.id;

                  const isDetailsOpen =
                    selectedDocument?.id === document.id;

                  const isDeleting =
                    deletingDocumentId === document.id;

                  return (
                    <div
                      key={document.id}
                      className="document-wrapper"
                    >
                      <div
                        className={`document-item ${
                          isSelected ? "selected" : ""
                        }`}
                      >
                        {/* Search filter checkbox */}
                        <input
                          className="document-checkbox"
                          type="checkbox"
                          checked={isSelected}
                          disabled={isDeleting}
                          onChange={() =>
                            handleDocumentSelection(
                              document
                            )
                          }
                          aria-label={`Search ${document.filename}`}
                        />

                        {/* Filename opens details */}
                        <button
                          className="document-file-button"
                          type="button"
                          onClick={() =>
                            handleDocumentClick(
                              document
                            )
                          }
                          disabled={isDeleting}
                          title="Click to view document details"
                        >
                          <span className="document-icon">
                            📄
                          </span>

                          <span
                            className="document-name"
                            title={document.filename}
                          >
                            {document.filename}
                          </span>
                        </button>

                        {/* Delete button */}
                        <button
                          className="document-delete-button"
                          type="button"
                          onClick={() =>
                            handleDeleteDocument(
                              document
                            )
                          }
                          disabled={isDeleting}
                          title="Delete document"
                          aria-label={`Delete ${document.filename}`}
                        >
                          {isDeleting ? "..." : "🗑️"}
                        </button>
                      </div>

                      {/* Document details */}
                      {isDetailsOpen && (
                        <div className="document-details">
                          <div>
                            <span>File</span>

                            <strong
                              title={document.filename}
                            >
                              {document.filename}
                            </strong>
                          </div>

                          <div>
                            <span>Type</span>

                            <strong>
                              {document.file_type}
                            </strong>
                          </div>

                          <div>
                            <span>Size</span>

                            <strong>
                              {Math.ceil(
                                document.file_size / 1024
                              )}{" "}
                              KB
                            </strong>
                          </div>

                          <div>
                            <span>Added</span>

                            <strong>
                              {formatCreatedDate(
                                document.created_at
                              )}
                            </strong>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentList;