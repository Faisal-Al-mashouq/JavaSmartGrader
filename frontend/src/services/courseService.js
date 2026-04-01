import api from "./api";

/** Default rubric body for POST /assignments/ (JSON body) */
export const DEFAULT_ASSIGNMENT_RUBRIC = {
  criteria: {
    Correctness: { weight: 100, description: "Solution correctness" },
  },
};

/** POST /courses/ — query: name, description */
export const createCourse = (name, description) =>
  api.post("/courses/", null, {
    params: { name, description: description ?? "" },
  });

/** GET /courses/me — instructors: courses taught; students: enrolled courses */
export const getMyCourses = () => api.get("/courses/me");

/** GET /courses/{id} */
export const getCourse = (id) => api.get(`/courses/${id}`);

/** GET /courses/{courseId}/students — enrolled students (instructor) */
export const getCourseStudents = (courseId) =>
  api.get(`/courses/${courseId}/students`);

/** POST /courses/{courseId}/enroll/{studentId} */
export const enrollStudentInCourse = (courseId, studentId) =>
  api.post(`/courses/${courseId}/enroll/${studentId}`);

/** DELETE /courses/{courseId}/enroll/{studentId} */
export const unenrollStudentFromCourse = (courseId, studentId) =>
  api.delete(`/courses/${courseId}/enroll/${studentId}`);

/** GET /assignments/course/{courseId} */
export const getCourseAssignments = (courseId) =>
  api.get(`/assignments/course/${courseId}`);

/** POST /assignments/ — body: rubric JSON; query: course_id, title, description?, due_date? */
export const createAssignment = (
  courseId,
  title,
  description,
  dueDateIso,
  rubricJson,
) =>
  api.post("/assignments/", rubricJson ?? DEFAULT_ASSIGNMENT_RUBRIC, {
    params: {
      course_id: courseId,
      title,
      ...(description ? { description } : {}),
      ...(dueDateIso ? { due_date: dueDateIso } : {}),
    },
  });

/** DELETE /assignments/{id} */
export const deleteAssignment = (assignmentId) =>
  api.delete(`/assignments/${assignmentId}`);

/** GET /assignments/{id} */
export const getAssignment = (id) => api.get(`/assignments/${id}`);

/** GET /assignments/{assignmentId}/questions/ */
export const getAssignmentQuestions = (assignmentId) =>
  api.get(`/assignments/${assignmentId}/questions/`);

/** POST /assignments/{assignmentId}/questions/ — query: question_text */
export const createQuestion = (assignmentId, questionText) =>
  api.post(`/assignments/${assignmentId}/questions/`, null, {
    params: { question_text: questionText },
  });

/** DELETE /assignments/{assignmentId}/questions/{questionId} */
export const deleteQuestion = (assignmentId, questionId) =>
  api.delete(`/assignments/${assignmentId}/questions/${questionId}`);

/** POST .../questions/{questionId}/testcases — query: input_data, expected_output */
export const addTestcase = (
  assignmentId,
  questionId,
  inputData,
  expectedOutput,
) =>
  api.post(
    `/assignments/${assignmentId}/questions/${questionId}/testcases`,
    null,
    { params: { input_data: inputData, expected_output: expectedOutput } },
  );

/** GET .../questions/{questionId}/testcases */
export const getQuestionTestcases = (assignmentId, questionId) =>
  api.get(`/assignments/${assignmentId}/questions/${questionId}/testcases`);

/** DELETE .../testcases/{testcaseId} */
export const deleteTestcase = (assignmentId, questionId, testcaseId) =>
  api.delete(
    `/assignments/${assignmentId}/questions/${questionId}/testcases/${testcaseId}`,
  );
