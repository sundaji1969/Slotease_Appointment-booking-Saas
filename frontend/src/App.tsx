import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import DashboardLayout from "./pages/dashboard/Layout";
import Hours from "./pages/dashboard/Hours";
import Services from "./pages/dashboard/Services";
import Stats from "./pages/dashboard/Stats";
import Today from "./pages/dashboard/Today";
import Week from "./pages/dashboard/Week";
import Home from "./pages/Home";
import BookingPage from "./pages/public/BookingPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Today />} />
        <Route path="week" element={<Week />} />
        <Route path="services" element={<Services />} />
        <Route path="hours" element={<Hours />} />
        <Route path="stats" element={<Stats />} />
      </Route>
      <Route path="/:slug" element={<BookingPage />} />
    </Routes>
  );
}
