import { Link } from "react-router-dom";
import { FiCheckCircle, FiChevronRight, FiCircle } from "react-icons/fi";
import { Bar, ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useFetch } from "../lib/hooks";

export default function Curriculum() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch(() => api.get("/lessons"));
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const weeks = {};
  data.lessons.forEach((l) => (weeks[l.week] ||= { week: l.week, title: l.week_title, goal: l.week_goal, lessons: [] }).lessons.push(l));
  const color = user.path.color;
  const next = data.lessons.find((l) => !l.completed)?.number;

  return (
    <div className="space-y-6">
      <header>
        <span className="chip text-white" style={{ background: color }}>{user.path.level}</span>
        <h1 className="mt-2 font-display text-3xl font-extrabold text-navy">{user.path.title}</h1>
        <p className="mt-1 max-w-2xl text-slate-600">{user.path.tagline}</p>
      </header>
      {Object.values(weeks).map((w) => {
        const done = w.lessons.filter((l) => l.completed).length;
        return (
          <section key={w.week} className="card overflow-hidden">
            <div className="p-5 md:p-6" style={{ borderLeft: `8px solid ${color}` }}>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Week {w.week}</p>
              <h2 className="font-display text-xl font-bold text-navy">{w.title}</h2>
              <p className="mt-1 text-sm text-slate-600">{w.goal}</p>
              <div className="mt-3 flex items-center gap-3"><div className="flex-1"><Bar value={done} total={w.lessons.length} color={color} /></div><span className="text-sm font-bold text-slate-500">{done}/{w.lessons.length}</span></div>
            </div>
            <ul className="divide-y divide-slate-100">
              {w.lessons.map((l) => (
                <li key={l.number}>
                  <Link to={`/app/learn/${l.number}`} className="flex items-center gap-4 px-5 py-4 hover:bg-panel md:px-6">
                    {l.completed ? <FiCheckCircle className="h-6 w-6 shrink-0 text-path-beginner" aria-label="Completed" /> : <FiCircle className="h-6 w-6 shrink-0 text-slate-300" aria-label="Not completed" />}
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold text-slate-400">Day {l.number}</p>
                      <p className="truncate font-semibold text-navy">{l.title}</p>
                    </div>
                    {l.quiz_total ? <span className="chip bg-brand/30 text-navy">{l.quiz_score}/{l.quiz_total}</span> : null}
                    {l.number === next && <span className="chip bg-navy text-white">Up next</span>}
                    <FiChevronRight className="shrink-0 text-slate-400" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
