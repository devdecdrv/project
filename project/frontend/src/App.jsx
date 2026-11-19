import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Batch from "./pages/Batch";
import Watch from "./pages/Watch";

export default function App() {
  return (
    <Routes>
      <Route path="/"                     element={<Home />} />
      <Route path="/batch/:batchId"       element={<Batch />} />
      <Route path="/watch/:videoId"       element={<Watch />} />
    </Routes>
  );
}
