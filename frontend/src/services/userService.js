import api from "./api";

/** GET /users/students — instructor only */
export const getStudents = () => api.get("/users/students");
