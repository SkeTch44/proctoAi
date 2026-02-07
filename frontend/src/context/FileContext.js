import React, { createContext, useState, useContext } from 'react';

const FileContext = createContext();

export function useFile() {
    return useContext(FileContext);
}

export function FileProvider({ children }) {
    const [file, setFile] = useState(null);
    const [parsedContent, setParsedContent] = useState('');
    const [docId, setDocId] = useState(null);

    const value = {
        file,
        setFile,
        parsedContent,
        setParsedContent,
        docId,
        setDocId
    };

    return (
        <FileContext.Provider value={value}>
            {children}
        </FileContext.Provider>
    );
}
