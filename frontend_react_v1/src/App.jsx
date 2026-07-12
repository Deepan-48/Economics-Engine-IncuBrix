import { BrowserRouter, Routes, Route } from "react-router-dom";
import AdminConsole from "./AdminConsole.jsx";
import SimulationUI from "./SimulationUI.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AdminConsole />} />
        <Route path="/simulation" element={<SimulationUI />} />
      </Routes>
    </BrowserRouter>
  );
}
