import api from "./api";

/** POST /users/login  — OAuth2 form-encoded */
export const loginUser = (username, password) =>
  api.post("/users/login", new URLSearchParams({ username, password }), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

/** GET /users/me */
export const getMe = () => api.get("/users/me");

/** POST /users/register */
export const registerUser = (data) => api.post("/users/register", data);
