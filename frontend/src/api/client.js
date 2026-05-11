export const API_URL = "http://localhost:8000";

export const getAuthToken = () => localStorage.getItem("token");
export const setAuthToken = (token) => localStorage.setItem("token", token);
export const removeAuthToken = () => localStorage.removeItem("token");

export const fetchApi = async (endpoint, options = {}) => {
  const token = getAuthToken();
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Only set Content-Type to application/json if it's not a FormData request
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Handle token refresh or logout here in a real app
    removeAuthToken();
    window.location.href = "/login";
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "API request failed");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
};
