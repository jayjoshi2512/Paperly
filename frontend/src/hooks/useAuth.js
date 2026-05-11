import { useState } from "react";
import { fetchApi, setAuthToken, removeAuthToken, getAuthToken } from "../api/client";

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(!!getAuthToken());

  const login = async (email, password) => {
    const res = await fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAuthToken(res.access_token);
    setIsAuthenticated(true);
  };

  const register = async (email, password, workspace_name) => {
    const res = await fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, workspace_name }),
    });
    setAuthToken(res.access_token);
    setIsAuthenticated(true);
  };

  const logout = () => {
    removeAuthToken();
    setIsAuthenticated(false);
  };

  return { isAuthenticated, login, register, logout };
};
