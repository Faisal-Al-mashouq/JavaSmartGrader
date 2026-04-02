import api from "./api";

/** GET /submissions/me */
export const getMySubmissions = () => api.get("/submissions/me");

/** GET /submissions/{id} */
export const getSubmission = (id) => api.get(`/submissions/${id}`);

/** GET /submissions/assignment/{assignmentId}  (instructor) */
export const getAssignmentSubmissions = (assignmentId) =>
  api.get(`/submissions/assignment/${assignmentId}`);

/** POST /submissions/  (student) */
export const submitAnswer = (questionId, assignmentId, file) => {
  const form = new FormData();
  form.append("question_id", String(questionId));
  form.append("assignment_id", String(assignmentId));
  form.append("file", file);
  return api.post("/submissions/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
