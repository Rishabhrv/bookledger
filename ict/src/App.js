import "./App.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./Pages/HomePage";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}

function App() {
  return (
    <Router basename="/chat">
      <AppRoutes />
    </Router>
  );
}

export default App;
