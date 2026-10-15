import { FaCode, FaCog, FaLightbulb } from "react-icons/fa";
import * as Fi from "react-icons/fi";
import { Link } from "react-router-dom";

export function Logo({ dark = false, to = "/" }) {
  return (
    <Link to={to} className="flex items-center gap-3" aria-label="AI Training for Everyone home">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-navy shadow-glow">
        <svg viewBox="0 0 64 64" className="h-6 w-6" aria-hidden="true">
          <path d="M12 46 L32 12 L52 46" fill="none" stroke="currentColor" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M22 37h20" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
        </svg>
      </span>
      <span className="leading-none">
        <span className={`block font-display text-sm font-extrabold tracking-wide ${dark ? "text-navy" : "text-white"}`}>AI TRAINING</span>
        <span className={`block font-script text-xl ${dark ? "text-navy-700" : "text-brand"}`}>for Everyone</span>
      </span>
    </Link>
  );
}

export function Icon({ name, className = "" }) {
  const C = Fi[name];
  return C ? <C className={className} aria-hidden="true" /> : null;
}

const PATH_ICONS = { bulb: FaLightbulb, gear: FaCog, code: FaCode };
export function PathIcon({ icon, color, size = "h-12 w-12", iconSize = "h-6 w-6" }) {
  const C = PATH_ICONS[icon] || FaLightbulb;
  return (
    <span className={`grid ${size} shrink-0 place-items-center rounded-full text-white shadow-md`} style={{ background: color }}>
      <C className={iconSize} aria-hidden="true" />
    </span>
  );
}

export function PathCard({ path, selected = false, onSelect, footer }) {
  const clickable = typeof onSelect === "function";
  const Wrapper = clickable ? "button" : "div";
  return (
    <Wrapper
      type={clickable ? "button" : undefined}
      onClick={clickable ? () => onSelect(path.slug) : undefined}
      aria-pressed={clickable ? selected : undefined}
      className={`card relative flex h-full w-full flex-col p-6 text-left transition ${
        clickable ? "cursor-pointer hover:-translate-y-1 hover:shadow-xl" : ""
      } ${selected ? "ring-4" : ""}`}
      style={selected ? { "--tw-ring-color": path.color } : undefined}
    >
      {selected && (
        <span className="absolute right-4 top-4 grid h-7 w-7 place-items-center rounded-full text-white" style={{ background: path.color }}>
          <Fi.FiCheck aria-hidden="true" />
          <span className="sr-only">Selected</span>
        </span>
      )}
      <div className="flex items-center gap-4">
        <PathIcon icon={path.icon} color={path.color} />
        <div>
          <span className="chip text-white" style={{ background: path.color }}>{path.level}</span>
        </div>
      </div>
      <h3 className="mt-4 font-display text-xl font-bold text-navy">{path.title}</h3>
      <p className="mt-1 text-slate-600">{path.blurb}</p>
      {path.outcomes && (
        <ul className="mt-4 space-y-2 text-sm text-slate-700">
          {path.outcomes.slice(0, 3).map((o) => (
            <li key={o} className="flex gap-2">
              <Fi.FiCheckCircle className="mt-0.5 h-4 w-4 shrink-0" style={{ color: path.color }} aria-hidden="true" />
              <span>{o}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-auto pt-5 text-sm font-semibold text-slate-500">
        {path.lessons || 20} lessons &middot; 4 weeks &middot; 3 hours a day
      </div>
      {footer}
    </Wrapper>
  );
}

export function ProgressRing({ percent = 0, size = 120, stroke = 12, color = "#F5D90A", track = "rgba(255,255,255,.2)", children }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c - (Math.min(100, Math.max(0, percent)) / 100) * c;
  return (
    <div className="relative" style={{ width: size, height: size }} role="img" aria-label={`${percent} percent complete`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}

export function Bar({ value, total, color = "#1B8A3A" }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function Spinner({ label = "Loading..." }) {
  return (
    <div className="grid min-h-[40vh] place-items-center" role="status">
      <div className="flex items-center gap-3 text-navy">
        <span className="h-6 w-6 animate-spin rounded-full border-4 border-navy/20 border-t-navy" />
        <span className="font-semibold">{label}</span>
      </div>
    </div>
  );
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="card mx-auto my-10 max-w-lg p-6 text-center" role="alert">
      <p className="font-semibold text-red-700">{message || "Something went wrong."}</p>
      {onRetry && (
        <button className="btn-navy btn-sm mt-4" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
