import { createContext, useContext, useState, useEffect } from "react";
import { loginUser, getMe } from "../services/authService";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true); // true while we check the stored token

  // On mount: if a token is stored, restore the session via GET /users/me
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      getMe()
        .then((res) => setUser(res.data))
        .catch(() => localStorage.removeItem("token")) // token expired / invalid
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  /**
   * Calls POST /users/login, stores the JWT, then fetches /users/me.
   * Returns the user object so the caller can navigate by role.
   */
  const login = async (username, password) => {
    const res = await loginUser(username, password);
    localStorage.setItem("token", res.data.access_token);
    const meRes = await getMe();
    setUser(meRes.data);
    return meRes.data; // { id, username, email, role: "instructor"|"student" }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
