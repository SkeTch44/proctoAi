// src/pages/AdminPages/DragNdrop.jsx
import React, { useRef, useState } from "react";

export default function DragNdrop() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
     
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Upload your exam file
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">   Drag & drop a file here, or click to browse from your device.
       
        </p>
      </div>

      {/* Drag area - centered with proper width */}
      <div
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`
          cursor-pointer rounded-xl p-12 text-center border-2 border-dashed transition-all w-full
          border-[#D1D5DB] hover:border-[#6D28D9] hover:bg-[#F3F4F6]
          dark:border-[#374151] dark:hover:border-[#10B981] dark:bg-[#171A1D] dark:hover:bg-[#111827]
          ${isDragging 
            ? 'border-[#6D28D9] bg-[#6D28D9]/10 dark:border-[#10B981] dark:bg-[#10B981]/10' 
            : ''
          }
        `}
      >
        <div
          className="
            mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full
            bg-[#EEF2FF] text-[#6D28D9]
            dark:bg-[#10B981]/15 dark:text-[#10B981]
          "
        >
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M16 8l-4-4m0 0L8 8m4-4v12"
            />
          </svg>
        </div>

        <p className="text-lg font-medium text-gray-700 dark:text-gray-100 mb-1">
          Drop your file here
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Supports PDF, TXT, DOCX, CSV (max 10MB)
        </p>

        <button
          type="button"
          className="
            mt-6 inline-flex items-center justify-center px-6 py-2.5 text-sm font-medium rounded-xl
            border border-[#6D28D9] text-[#6D28D9] bg-[#EEF2FF]
            hover:bg-[#6D28D9]/10 hover:shadow-md
            dark:border-[#10B981] dark:text-[#10B981] dark:bg-[#10B981]/10
            dark:hover:bg-[#10B981]/20 dark:hover:shadow-md
          "
        >
          Browse files
        </button>
      </div>

      <input
        ref={inputRef}
        type="file"
        hidden
        accept=".pdf,.txt,.docx,.doc,.csv"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {file && (
        <div
          className="
            flex items-center justify-between rounded-xl px-6 py-4 shadow-sm
            bg-[#F9FAFB] border border-[#E5E7EB]
            dark:bg-[#111827] dark:border-[#374151]
          "
        >
          <div className="truncate">
            <p className="text-base font-medium text-gray-900 dark:text-white max-w-md">
              {file.name}
            </p>
            <p className="text-sm text-gray-500">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          </div>
          <span
            className="
              text-sm px-4 py-2 rounded-full font-semibold
              bg-[#10B981]/10 text-[#10B981]
              dark:bg-[#10B981]/20 dark:text-[#10B981]
            "
          >
            Ready
          </span>
        </div>
      )}
    </div>
  );
}
