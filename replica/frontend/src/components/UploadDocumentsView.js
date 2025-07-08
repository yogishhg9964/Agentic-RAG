import React, { useState, useCallback } from 'react';
import { uploadFiles, clearAllDocuments, fetchDocumentCount } from '../api';
import './UploadDocumentsView.css';

function UploadDocumentsView() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [docCountInfo, setDocCountInfo] = useState('');
  const [error, setError] = useState('');

  const getDocCount = useCallback(async () => {
    try {
      const data = await fetchDocumentCount();
      setDocCountInfo(data.message || `${data.count} document chunks in the knowledge base.`);
    } catch (err) {
      setDocCountInfo('⚠️ Could not fetch document count.');
      console.error(err);
    }
  }, []);

  useState(() => {
    getDocCount();
  }, [getDocCount]);

  const handleFileChange = (event) => {
    setSelectedFiles([...event.target.files]);
    setUploadMessage('');
    setError('');
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select files to upload.');
      return;
    }
    setIsUploading(true);
    setError('');
    setUploadMessage('Processing files...');

    try {
      const data = await uploadFiles(selectedFiles);
      setUploadMessage(data.message || 'Upload successful!');
      setSelectedFiles([]); // Clear selection
      document.getElementById('file-input').value = null; // Reset file input
      getDocCount(); // Refresh document count
    } catch (err) {
      console.error("Upload error:", err);
      setError(`Upload failed: ${err.message || 'Unknown error'}`);
      setUploadMessage('');
    }
    setIsUploading(false);
  };

  const handleClearDocuments = async () => {
    if (!window.confirm("Are you sure you want to delete all documents from the knowledge base?")) {
      return;
    }
    setIsUploading(true); // Use same loading state for simplicity
    setError('');
    setUploadMessage('Clearing documents...');
    try {
      const data = await clearAllDocuments();
      setUploadMessage(data.message || 'Documents cleared successfully!');
      getDocCount(); // Refresh document count
    } catch (err) {
      console.error("Clear documents error:", err);
      setError(`Failed to clear documents: ${err.message || 'Unknown error'}`);
      setUploadMessage('');
    }
    setIsUploading(false);
  };

  return (
    <div className="upload-view">
      <h2>Upload Documents</h2>
      <p className="doc-count-info">{docCountInfo}</p>
      {error && <p className="error-message">{error}</p>}
      {uploadMessage && <p className="upload-message">{uploadMessage}</p>}
      
      <div className="upload-controls">
        <input type="file" id="file-input" multiple onChange={handleFileChange} disabled={isUploading} />
        <button onClick={handleUpload} disabled={isUploading || selectedFiles.length === 0}>
          {isUploading ? 'Uploading...' : 'Upload Selected Files'}
        </button>
      </div>

      <div className="selected-files">
        {selectedFiles.length > 0 && (
          <p>Selected files ({selectedFiles.length}):</p>
        )}
        <ul>
          {selectedFiles.map((file, index) => (
            <li key={index}>{file.name}</li>
          ))}
        </ul>
      </div>

      <div className="clear-documents-section">
        <h3>Manage Documents</h3>
        <button onClick={handleClearDocuments} disabled={isUploading} className="clear-button">
          {isUploading ? 'Processing...' : 'Clear All Documents from Knowledge Base'}
        </button>
      </div>
    </div>
  );
}

export default UploadDocumentsView;
