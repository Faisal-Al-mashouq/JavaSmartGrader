import api from "./api";

/** GET /courses/me  (instructor only) */
export const getMyCourses = () => api.get("/courses/me");

/** GET /courses/{id} */
export const getCourse = (id) => api.get(`/courses/${id}`);

/** GET /assignments/course/{courseId} */
export const getCourseAssignments = (courseId) =>
  api.get(`/assignments/course/${courseId}`);

/** GET /assignments/{id} */
export const getAssignment = (id) => api.get(`/assignments/${id}`);

/** GET /assignments/{assignmentId}/questions/ */
export const getAssignmentQuestions = (assignmentId) =>
  api.get(`/assignments/${assignmentId}/questions/`);
