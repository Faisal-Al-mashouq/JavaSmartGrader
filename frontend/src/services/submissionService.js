import api from "./api";

/** GET /submissions/me */
export const getMySubmissions = () => api.get("/submissions/me");

/** GET /submissions/{id} */
export const getSubmission = (id) => api.get(`/submissions/${id}`);

/** GET /submissions/assignment/{assignmentId}  (instructor) */
export const getAssignmentSubmissions = (assignmentId) =>
  api.get(`/submissions/assignment/${assignmentId}`);

/** GET /submissions/{submissionId}/pending-review  (student) */
export const getPendingReview = (submissionId) =>
  api.get(`/submissions/${submissionId}/pending-review`);

/** POST /submissions/{submissionId}/approve-transcription  (student) */
export const approveTranscription = (submissionId, approvedText) =>
  api.post(`/submissions/${submissionId}/approve-transcription`, {
    approved_text: approvedText,
  });

/** POST /submissions/  (student) */
export const submitAnswer = (questionId, assignmentId, file) => {
  const form = new FormData();
  form.append("question_id", String(questionId));
  form.append("assignment_id", String(assignmentId));
  form.append("file", file);
  // Let the browser set multipart boundary; a bare "multipart/form-data" header breaks uploads.
  return api.post("/submissions/", form);
};
