import api from "./api";

/** GET /assignments/{assignmentId}/rubric */
export const getRubric = (assignmentId) =>
  api.get(`/assignments/${assignmentId}/rubric`);

/** PUT /assignments/{assignmentId}/rubric */
export const saveRubric = (assignmentId, criteria) =>
  api.put(`/assignments/${assignmentId}/rubric`, { criteria });
