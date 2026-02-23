import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";

import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

/* Student */
import DashboardLayout from "./layout/DashboardLayout";
import StudentHome from "./pages/dashboard/student/StudentHome";
import StudentSubmissions from "./pages/dashboard/student/StudentSubmissions";
import StudentUpload from "./pages/dashboard/student/StudentUpload";

/* Instructor */
import InstructorLayout from "./layout/InstructorLayout";
import InstructorHome from "./pages/dashboard/instructor/InstructorHome";
import InstructorSubmissions from "./pages/dashboard/instructor/InstructorSubmissions";
import InstructorGrading from "./pages/dashboard/instructor/InstructorGrading";

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />

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
            <Route path="submissions" element={<InstructorSubmissions />} />
            <Route path="grading" element={<InstructorGrading />} />
          </Route>
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
