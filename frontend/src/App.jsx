import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import SelectMediaType from "./pages/SelectMediaType";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import ComingSoon from "./pages/ComingSoon";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/select" element={<SelectMediaType />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<ComingSoon title="Page not found" />} />
      </Routes>
    </ErrorBoundary>
  );
}
