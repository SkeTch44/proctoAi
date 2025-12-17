import React from 'react'
  import { useRef, useState } from "react";

export default function DragNdrop() {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    setFile(selectedFile);
    // 👉 send this file to backend / read it in app
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };
  // return (
  //   <div>
  //     This is a drag and drop page.
      
  //   </div>
  // )


  return (
    <div className=" flex items-center justify-center bg-gray-100 dark:bg-[#111827] transition-colors">
      <div className="  p-6 rounded-2xl shadow-xl bg-white dark:bg-[#111827]">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Upload your file
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Drag & drop a file here, or click to browse
        </p>

        <div
          onClick={() => inputRef.current.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`cursor-pointer border-2 border-dashed rounded-xl p-8 text-center transition
            ${
              isDragging
                ? "border-[#10B981] bg-[#10B981]/10"
                : "border-gray-300 dark:border-[#10B981]"
            }
          `}
        >
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
            Drop your file here
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Supports PDF, TXT, DOCX, CSV
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {file && (
          <div className="mt-4 flex items-center justify-between rounded-lg px-4 py-3
            bg-gray-50 dark:bg-[#1F2933]">
            <div>
              <p className="text-sm font-medium text-gray-800 dark:text-white">
                {file.name}
              </p>
              <p className="text-xs text-gray-500">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <span className="text-xs px-2 py-1 rounded-full bg-[#10B981]/20 text-[#10B981]">
              Ready
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
export const pages = [
    "Dashboard",
    "Uploads",
    "Documents",
    "Analytics",
    "Settings",
    "Help",
];

