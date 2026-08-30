import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { Lab } from "../routes/Lab";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Lab />} />
        {/* Collapse legacy routes into the single demo surface. */}
        <Route path="lab" element={<Navigate to="/" replace />} />
        <Route path="sessions" element={<Navigate to="/" replace />} />
        <Route path="settings" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
