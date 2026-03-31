import api from "./api";

/** GET /submissions/me */
export const getMySubmissions = () => api.get("/submissions/me");

/** GET /submissions/{id} */
export const getSubmission = (id) => api.get(`/submissions/${id}`);

/** GET /submissions/assignment/{assignmentId}  (instructor) */
export const getAssignmentSubmissions = (assignmentId) =>
  api.get(`/submissions/assignment/${assignmentId}`);

/** POST /submissions/  (student) */
export const submitAnswer = (questionId, assignmentId) =>
  api.post("/submissions/", null, {
    params: { question_id: questionId, assignment_id: assignmentId },
  });
