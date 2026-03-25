import { createContext, useContext, useState, useEffect } from "react";
import { loginUser, getMe } from "../services/api";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On mount, restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((res) => {
        // Normalise role to uppercase to match existing UI checks
        setUser({ ...res.data, role: res.data.role.toUpperCase() });
      })
      .catch(() => {
        // Token is invalid or expired — clear it
        localStorage.removeItem("token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    const tokenRes = await loginUser(username, password);
    localStorage.setItem("token", tokenRes.data.access_token);
    const meRes = await getMe();
    const userData = { ...meRes.data, role: meRes.data.role.toUpperCase() };
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
