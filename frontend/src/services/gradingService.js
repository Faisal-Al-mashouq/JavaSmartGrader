import api from "./api";

/** GET /grading/{submissionId}/ai_feedback */
export const getAIFeedback = (submissionId) =>
  api.get(`/grading/${submissionId}/ai_feedback`);

/** GET /grading/{submissionId}/transcription */
export const getTranscription = (submissionId) =>
  api.get(`/grading/${submissionId}/transcription`);

/** GET /grading/{submissionId}/compile_result */
export const getCompileResult = (submissionId) =>
  api.get(`/grading/${submissionId}/compile_result`);

/**
 * POST /grading/{submissionId}/grade
 * Creates a new grade entry for the submission.
 */
export const addGrade = (submissionId, finalGrade) =>
  api.post(`/grading/${submissionId}/grade`, null, {
    params: { final_grade: finalGrade },
  });

/**
 * PUT /grading/{submissionId}/grade
 * Updates an existing grade entry.
 */
export const updateGrade = (submissionId, grade) =>
  api.put(`/grading/${submissionId}/grade`, null, {
    params: { grade },
  });
