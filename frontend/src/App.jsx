import { Link, Route, Routes } from "react-router-dom";
import { AppShell, RequireAuth } from "./components/Layout";
import Admin from "./pages/Admin";
import { ChoosePath, Login, Signup } from "./pages/Auth";
import Curriculum from "./pages/Curriculum";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Lesson from "./pages/Lesson";
import { Certificate, Glossary, Profile, Resources } from "./pages/More";

function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-panel p-6 text-center">
      <div>
        <p className="font-script text-4xl text-navy-700">Oops!</p>
        <h1 className="font-display text-3xl font-extrabold text-navy">Page not found</h1>
        <Link to="/" className="btn-primary mt-6">Back to home</Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/login" element={<Login />} />
      <Route path="/choose-path" element={<ChoosePath />} />
      <Route path="/app" element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="curriculum" element={<Curriculum />} />
        <Route path="learn/:number" element={<Lesson />} />
        <Route path="resources" element={<Resources />} />
        <Route path="glossary" element={<Glossary />} />
        <Route path="profile" element={<Profile />} />
        <Route path="certificate" element={<Certificate />} />
        <Route path="admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
