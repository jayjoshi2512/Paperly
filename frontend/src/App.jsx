import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";
import EvalDashboard from "./pages/EvalDashboard";
import Layout from "./components/Layout";
import { getAuthToken } from "./api/client";

const ProtectedRoute = ({ children }) => {
  if (!getAuthToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<Chat />} />
          <Route path="documents" element={<Documents />} />
          <Route path="eval" element={<EvalDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}