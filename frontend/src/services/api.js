import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

// Attach JWT token to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auth ──────────────────────────────────────────────────────────────────────
export const loginUser = (username, password) => {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);
  return api.post("/users/login", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
};

export const getMe = () => api.get("/users/me");

export const registerUser = (data) => api.post("/users/register", data);

// ── Courses ───────────────────────────────────────────────────────────────────
export const getMyCourses = () => api.get("/courses/me");
export const getCourse = (courseId) => api.get(`/courses/${courseId}`);

// ── Assignments ───────────────────────────────────────────────────────────────
export const getCourseAssignments = (courseId) =>
  api.get(`/assignments/course/${courseId}`);
export const getAssignment = (assignmentId) =>
  api.get(`/assignments/${assignmentId}`);

// ── Questions ─────────────────────────────────────────────────────────────────
export const getQuestions = (assignmentId) =>
  api.get(`/assignments/${assignmentId}/questions/`);

// ── Submissions ───────────────────────────────────────────────────────────────
export const getMySubmissions = () => api.get("/submissions/me");
export const getAssignmentSubmissions = (assignmentId) =>
  api.get(`/submissions/assignment/${assignmentId}`);
export const createSubmission = (questionId, assignmentId, imageUrl) =>
  api.post("/submissions/", null, {
    params: {
      question_id: questionId,
      assignment_id: assignmentId,
      ...(imageUrl ? { image_url: imageUrl } : {}),
    },
  });

// ── Grading ───────────────────────────────────────────────────────────────────
export const getAIFeedback = (submissionId) =>
  api.get(`/grading/${submissionId}/ai_feedback`);
export const getCompileResult = (submissionId) =>
  api.get(`/grading/${submissionId}/compile_result`);
export const getTranscription = (submissionId) =>
  api.get(`/grading/${submissionId}/transcription`);
export const addGrade = (submissionId, finalGrade) =>
  api.post(`/grading/${submissionId}/grade`, null, {
    params: { final_grade: finalGrade },
  });
export const updateGrade = (submissionId, grade) =>
  api.put(`/grading/${submissionId}/grade`, null, { params: { grade } });

export default api;
