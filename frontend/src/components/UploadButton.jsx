import { useEffect, useRef, useState } from "react";

function UploadButton({ onUploadSuccess }) {
  const fileInputRef = useRef(null);
  const messageTimeoutRef = useRef(null);

  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function openFilePicker() {
    if (uploading) {
      return;
    }

    fileInputRef.current?.click();
  }

  function showTemporaryMessage(
    type,
    message,
    duration
  ) {
    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
    }

    if (type === "success") {
      setStatus(message);
      setError("");
    } else {
      setError(message);
      setStatus("");
    }

    messageTimeoutRef.current = setTimeout(() => {
      setStatus("");
      setError("");
      messageTimeoutRef.current = null;
    }, duration);
  }

  useEffect(() => {
    return () => {
      if (messageTimeoutRef.current) {
        clearTimeout(messageTimeoutRef.current);
      }
    };
  }, []);

  async function handleFileChange(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
      messageTimeoutRef.current = null;
    }

    setStatus("");
    setError("");
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Failed to upload document."
        );
      }

      showTemporaryMessage(
        "success",
        `${file.name} uploaded successfully.`,
        3000
      );

      onUploadSuccess(data);
    } catch (error) {
      console.error(
        "Failed to upload document:",
        error
      );

      showTemporaryMessage(
        "error",
        error.message ||
          "Unable to upload the document. Please try again.",
        4000
      );
    } finally {
      setUploading(false);

      event.target.value = "";
    }
  }

  return (
    <div className="upload-section">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt"
        onChange={handleFileChange}
        hidden
      />

      <button
        className="upload-button"
        type="button"
        onClick={openFilePicker}
        disabled={uploading}
      >
        {uploading
          ? "Uploading..."
          : "+ Upload"}
      </button>

      {status && (
        <p className="upload-success">
          ✓ {status}
        </p>
      )}

      {error && (
        <p className="upload-error">
          {error}
        </p>
      )}
    </div>
  );
}

export default UploadButton;