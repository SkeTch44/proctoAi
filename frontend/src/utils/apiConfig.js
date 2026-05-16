// src/utils/apiConfig.js
/**
 * Centralized API configuration for ProctoAI.
 * Prefers REACT_APP_API_URL environment variable, 
 * defaults to localhost:5000 for standard development.
 */

export const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

export const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};
