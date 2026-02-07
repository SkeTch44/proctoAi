
import { getToken, logout } from "./authStorage";

const BASE_URL = "http://localhost:5000"; // Can be moved to env var

/**
 * Enhanced fetch wrapper that automatically adds Authorization header
 */
export async function authFetch(endpoint, options = {}) {
    const token = getToken();

    const headers = {
        ...options.headers,
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    // Ensure config does not override our auth if not intended
    const config = {
        ...options,
        headers,
    };

    // Adjust URL if relative
    const url = endpoint.startsWith("http") ? endpoint : `${BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, config);

        // Handle 401 Unauthorized globally
        if (response.status === 401) {
            console.warn("Session expired or unauthorized. Redirecting to login...");
            logout();
            window.location.href = "/login";
            return response; // Caller handles the rest, but user is redirected
        }

        return response;
    } catch (error) {
        console.error("API Request Failed:", error);
        throw error;
    }
}
