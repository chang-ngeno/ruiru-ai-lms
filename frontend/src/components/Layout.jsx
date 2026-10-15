import { useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { FaWhatsapp } from "react-icons/fa";
import { FiBook, FiBookOpen, FiDownload, FiGrid, FiLogOut, FiMapPin, FiMenu, FiPhone, FiSettings, FiUser, FiX } from "react-icons/fi";
import { useAuth } from "../lib/auth";
import { site } from "../siteConfig";
import { Logo, Spinner } from "./ui";

export function PublicNav() {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const links = [
    ["Course paths", "/#paths"],
    ["What you'll learn", "/#learn"],
    ["How it works", "/#how"],
    ["Workspace", "/#workspace"],
  ];
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-navy-900/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Logo />
        <nav className="hidden items-center gap-7 md:flex" aria-label="Main">
          {links.map(([l, h]) => (
            <a key={l} href={h} className="text-sm font-semibold text-white/80 hover:text-brand">{l}</a>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <Link to="/app" className="btn-primary btn-sm">Go to my course</Link>
          ) : (
            <>
              <Link to="/login" className="text-sm font-bold text-white hover:text-brand">Sign in</Link>
              <Link to="/signup" className="btn-primary btn-sm">Get started</Link>
            </>
          )}
        </div>
        <button className="rounded-lg p-2 text-white md:hidden" onClick={() => setOpen(!open)} aria-label="Menu" aria-expanded={open}>
          {open ? <FiX className="h-6 w-6" /> : <FiMenu className="h-6 w-6" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-white/10 px-4 pb-4 md:hidden">
          {links.map(([l, h]) => (
            <a key={l} href={h} onClick={() => setOpen(false)} className="block py-3 font-semibold text-white/90">{l}</a>
          ))}
          <div className="mt-2 flex gap-3">
            <Link to="/login" className="btn-ghost btn-sm flex-1">Sign in</Link>
            <Link to="/signup" className="btn-primary btn-sm flex-1">Get started</Link>
          </div>
        </div>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="bg-navy-950 text-white/80">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 md:grid-cols-3">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm">Practical AI skills for everyone, from first-timers to builders. Learn. Build. Grow.</p>
        </div>
        <div>
          <h4 className="font-display font-bold text-white">Course paths</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li>Beginner: AI Foundations</li>
            <li>Intermediate: Projects &amp; Automation</li>
            <li>Advanced: Custom AI Solutions</li>
          </ul>
        </div>
        <div>
          <h4 className="font-display font-bold text-white">Book your spot</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li className="flex items-center gap-2"><FiPhone /> {site.phoneDisplay}</li>
            <li className="flex items-center gap-2"><FiMapPin /> {site.location}</li>
          </ul>
          <a className="btn-primary btn-sm mt-4" href={`https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.whatsappMessage)}`} target="_blank" rel="noreferrer">
            <FaWhatsapp /> Chat on WhatsApp
          </a>
        </div>
      </div>
      <div className="border-t border-white/10 py-4 text-center text-xs">&copy; {new Date().getFullYear()} {site.name}, {site.location}</div>
    </footer>
  );
}

/** Gate: signed in and has chosen a path. */
export function RequireAuth({ children, admin = false }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (!user.path) return <Navigate to="/choose-path" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/app" replace />;
  return children;
}

const nav = [
  { to: "/app", label: "Dashboard", icon: FiGrid, end: true },
  { to: "/app/curriculum", label: "Course", icon: FiBookOpen },
  { to: "/app/resources", label: "Resources", icon: FiDownload },
  { to: "/app/glossary", label: "Glossary", icon: FiBook },
  { to: "/app/profile", label: "Profile", icon: FiUser },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const items = user?.role === "admin" ? [...nav, { to: "/app/admin", label: "Admin", icon: FiSettings }] : nav;
  const cls = ({ isActive }) =>
    `flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold transition ${isActive ? "bg-brand text-navy" : "text-white/80 hover:bg-white/10 hover:text-white"}`;
  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="no-print sticky top-0 z-40 bg-navy-900 shadow-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <Logo to="/app" />
          <nav className="hidden items-center gap-1 md:flex" aria-label="App">
            {items.map(({ to, label, icon: I, end }) => (
              <NavLink key={to} to={to} end={end} className={cls}><I aria-hidden="true" /> {label}</NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            {user?.path && (
              <span className="chip hidden text-white sm:inline-flex" style={{ background: user.path.color }}>{user.path.level}</span>
            )}
            <button onClick={logout} className="rounded-full p-2 text-white/80 hover:bg-white/10 hover:text-white" aria-label="Sign out" title="Sign out">
              <FiLogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 md:py-8"><Outlet /></main>
      <nav className="no-print fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-slate-200 bg-white md:hidden" aria-label="App">
        {items.slice(0, 5).map(({ to, label, icon: I, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `flex flex-col items-center gap-0.5 py-2 text-[11px] font-bold ${isActive ? "text-navy" : "text-slate-500"}`}>
            {({ isActive }) => (<><I className={`h-5 w-5 ${isActive ? "text-navy" : ""}`} aria-hidden="true" />{label}</>)}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

