import api from "./api";

export const STANDARD_CRITERIA_KEYS = [
  "correctness",
  "edge_cases",
  "code_quality",
  "efficiency",
];

/** Default rubric — 4 standard criteria summing to 100% */
export const DEFAULT_ASSIGNMENT_RUBRIC = {
  criteria: {
    correctness: {
      label: "Correctness",
      weight: 40,
      description:
        "Does the solution produce correct output for all given test cases?",
      is_standard: true,
    },
    edge_cases: {
      label: "Edge Cases",
      weight: 20,
      description:
        "Does the solution handle boundary and edge cases properly?",
      is_standard: true,
    },
    code_quality: {
      label: "Code Quality",
      weight: 20,
      description:
        "Is the code clean, readable, and following good programming practices?",
      is_standard: true,
    },
    efficiency: {
      label: "Efficiency",
      weight: 20,
      description:
        "Does the solution use appropriate algorithms and data structures to minimize time and space complexity?",
      is_standard: true,
    },
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

/** PUT /assignments/{id}/rubric — body: rubric JSON */
export const updateAssignmentRubric = (assignmentId, rubricJson) =>
  api.put(`/assignments/${assignmentId}/rubric`, rubricJson);

/** GET /assignments/{id} */
export const getAssignment = (id) => api.get(`/assignments/${id}`);
