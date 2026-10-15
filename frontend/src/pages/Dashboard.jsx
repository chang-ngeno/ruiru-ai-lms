import { Link } from "react-router-dom";
import { FaFire } from "react-icons/fa";
import { FiArrowRight, FiAward, FiClock, FiLock, FiStar, FiTarget } from "react-icons/fi";
import { Bar, ErrorBox, ProgressRing, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useFetch } from "../lib/hooks";

export default function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch(() => api.get("/progress"));
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const s = data.summary;
  const color = user.path.color;
  const first = user.name.split(" ")[0];

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-navy-950 via-navy to-navy-700 p-6 text-white shadow-xl md:p-8">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="font-script text-2xl text-brand">Welcome back,</p>
            <h1 className="font-display text-3xl font-extrabold md:text-4xl">{first}</h1>
            <p className="mt-2 text-white/80">{user.path.level} path &middot; {user.path.title}</p>
            {s.finished ? (
              <Link to="/app/certificate" className="btn-primary mt-5"><FiAward /> Get your certificate</Link>
            ) : (
              <Link to={`/app/learn/${s.next_lesson}`} className="btn-primary mt-5">
                {s.completed ? "Continue" : "Start"} lesson {s.next_lesson} <FiArrowRight />
              </Link>
            )}
          </div>
          <div className="flex items-center gap-6">
            <ProgressRing percent={s.percent} size={130} stroke={13}>
              <div><p className="font-display text-3xl font-extrabold">{s.percent}%</p><p className="text-xs text-white/70">complete</p></div>
            </ProgressRing>
            <div className="space-y-2">
              <p className="flex items-center gap-2 font-display text-lg font-bold"><FaFire className="text-orange-400" aria-hidden="true" /> {s.streak} day streak</p>
              <p className="flex items-center gap-2 text-sm text-white/80"><FiClock aria-hidden="true" /> {s.hours} learning hours</p>
              <p className="flex items-center gap-2 text-sm text-white/80"><FiTarget aria-hidden="true" /> {s.completed} of {s.total} lessons</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="space-y-6 lg:col-span-2">
          {!s.finished && (
            <div className="card border-l-8 p-6" style={{ borderLeftColor: "#F5D90A" }}>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Up next &middot; Lesson {s.next_lesson}</p>
              <h2 className="mt-1 font-display text-xl font-bold text-navy">{s.next_title}</h2>
              <div className="mt-4 rounded-xl bg-brand/20 p-4">
                <p className="text-xs font-bold uppercase text-navy-700">Today&rsquo;s action (homework)</p>
                <p className="mt-1 font-semibold text-navy">{s.next_homework}</p>
              </div>
              <Link to={`/app/learn/${s.next_lesson}`} className="btn-navy btn-sm mt-4">Open lesson <FiArrowRight /></Link>
            </div>
          )}

          <div className="card p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-bold text-navy">Your learning roadmap</h2>
              <Link to="/app/curriculum" className="text-sm font-bold text-navy underline">View all</Link>
            </div>
            <ul className="mt-4 space-y-4">
              {s.weeks.map((w) => (
                <li key={w.week}>
                  <div className="mb-1 flex justify-between text-sm"><span className="font-bold text-slate-700">Week {w.week}: {w.title}</span><span className="font-semibold text-slate-500">{w.done}/{w.total}</span></div>
                  <Bar value={w.done} total={w.total} color={color} />
                </li>
              ))}
            </ul>
          </div>
        </section>

        <aside className="space-y-6">
          <div className="card p-6">
            <h2 className="font-display text-lg font-bold text-navy">Self-check average</h2>
            <p className="mt-2 font-display text-4xl font-extrabold" style={{ color }}>{s.quiz_average === null ? "-" : `${s.quiz_average}%`}</p>
            <p className="text-sm text-slate-500">Take the self-check at the end of each lesson.</p>
          </div>
          <div className="card p-6">
            <h2 className="font-display text-lg font-bold text-navy">Achievements</h2>
            <ul className="mt-4 grid grid-cols-2 gap-3">
              {s.achievements.map((a) => (
                <li key={a.key} title={a.desc} className={`rounded-xl p-3 text-center ${a.earned ? "bg-brand/25" : "bg-slate-100 opacity-70"}`}>
                  <span className={`mx-auto grid h-10 w-10 place-items-center rounded-full ${a.earned ? "bg-brand text-navy" : "bg-slate-300 text-slate-500"}`}>{a.earned ? <FiStar /> : <FiLock />}</span>
                  <p className="mt-2 text-sm font-bold text-navy">{a.title}</p>
                  <p className="text-[11px] leading-tight text-slate-500">{a.desc}</p>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
