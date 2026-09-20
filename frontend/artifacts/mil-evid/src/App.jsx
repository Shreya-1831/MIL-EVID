import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import NewAnalysis from "./pages/NewAnalysis";
import AnalysisDetail from "./pages/AnalysisDetail";
import History from "./pages/History";
import EvidenceExplorer from "./pages/EvidenceExplorer";
import EvidenceDetail from "./pages/EvidenceDetail";
import SystemStatus from "./pages/SystemStatus";
import NotFound from "./pages/NotFound";
import Protected from "./components/Protected";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/analysis/new" element={<Protected><NewAnalysis /></Protected>} />
          <Route path="/analysis/:id" element={<Protected><AnalysisDetail /></Protected>} />
          <Route path="/history" element={<Protected><History /></Protected>} />
          <Route path="/evidence" element={<Protected><EvidenceExplorer /></Protected>} />
          <Route path="/evidence/:id" element={<Protected><EvidenceDetail /></Protected>} />
          <Route path="/system" element={<Protected><SystemStatus /></Protected>} />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;