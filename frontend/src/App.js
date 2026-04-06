import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";

import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { SubmissionsProvider } from "./context/SubmissionsContext";
import ProtectedRoute from "./components/ProtectedRoute";

/* Student */
import DashboardLayout from "./layout/DashboardLayout";
import StudentHome from "./pages/dashboard/student/StudentHome";
import StudentCourses from "./pages/dashboard/student/StudentCourses";
import StudentSubmissions from "./pages/dashboard/student/StudentSubmissions";
import StudentAssignmentsFull from "./pages/dashboard/student/StudentAssignmentsFull";
import StudentUpload from "./pages/dashboard/student/StudentUpload";

/* Instructor */
import InstructorLayout from "./layout/InstructorLayout";
import InstructorHome from "./pages/dashboard/instructor/InstructorHome";
import InstructorCourses from "./pages/dashboard/instructor/InstructorCourses";
import InstructorCourseDetail from "./pages/dashboard/instructor/InstructorCourseDetail";
import InstructorCourseAssignments from "./pages/dashboard/instructor/InstructorCourseAssignments";
import InstructorAssignmentNew from "./pages/dashboard/instructor/InstructorAssignmentNew";
import InstructorAssignmentDetail from "./pages/dashboard/instructor/InstructorAssignmentDetail";
import InstructorAssignmentQuestions from "./pages/dashboard/instructor/InstructorAssignmentQuestions";
import InstructorAssignmentSubmissions from "./pages/dashboard/instructor/InstructorAssignmentSubmissions";
import InstructorSubmissions from "./pages/dashboard/instructor/InstructorSubmissions";
import InstructorGrading from "./pages/dashboard/instructor/InstructorGrading";
import InstructorAssignmentRubric from "./pages/dashboard/instructor/InstructorAssignmentRubric";

function App() {
  return (
    <Router>
      <ThemeProvider>
        <SubmissionsProvider>
          <AuthProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Login />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/*  STUDENT DASHBOARD  */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<StudentHome />} />
                <Route path="courses" element={<StudentCourses />} />
                <Route
                  path="assignments"
                  element={<StudentAssignmentsFull />}
                />
                <Route path="submissions" element={<StudentSubmissions />} />
                <Route path="upload" element={<StudentUpload />} />
              </Route>

              {/*  INSTRUCTOR DASHBOARD */}
              <Route
                path="/instructor"
                element={
                  <ProtectedRoute>
                    <InstructorLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<InstructorHome />} />
                <Route path="courses" element={<InstructorCourses />} />
                <Route
                  path="courses/:courseId"
                  element={<InstructorCourseDetail />}
                />
                <Route
                  path="courses/:courseId/assignments"
                  element={<InstructorCourseAssignments />}
                />
                <Route
                  path="courses/:courseId/assignments/new"
                  element={<InstructorAssignmentNew />}
                />
                <Route
                  path="courses/:courseId/assignments/:assignmentId"
                  element={<InstructorAssignmentDetail />}
                />
                <Route
                  path="courses/:courseId/assignments/:assignmentId/questions"
                  element={<InstructorAssignmentQuestions />}
                />
                <Route
                  path="courses/:courseId/assignments/:assignmentId/rubric"
                  element={<InstructorAssignmentRubric />}
                />
                <Route
                  path="courses/:courseId/assignments/:assignmentId/submissions"
                  element={<InstructorAssignmentSubmissions />}
                />
                <Route path="submissions" element={<InstructorSubmissions />} />
                <Route path="grading" element={<InstructorGrading />} />
              </Route>
            </Routes>
          </AuthProvider>
        </SubmissionsProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
