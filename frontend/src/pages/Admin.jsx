import { useState } from "react";
import { Bar, ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useFetch } from "../lib/hooks";

export default function Admin() {
  const [q, setQ] = useState("");
  const [path, setPath] = useState("");
  const overview = useFetch(() => api.get("/admin/overview"));
  const list = useFetch(() => api.get(`/admin/learners?path=${encodeURIComponent(path)}&q=${encodeURIComponent(q)}`), [path, q]);
  const [msg, setMsg] = useState("");

  const change = async (id, slug) => {
    try {
      await api.patch(`/admin/learners/${id}/path`, { path_slug: slug });
      setMsg("Path updated.");
      list.reload();
      overview.reload();
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (overview.loading) return <Spinner />;
  if (overview.error) return <ErrorBox message={overview.error} onRetry={overview.reload} />;
  const o = overview.data;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-extrabold text-navy">Trainer dashboard</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5"><p className="text-sm font-bold text-slate-500">Learners</p><p className="font-display text-4xl font-extrabold text-navy">{o.learners}</p>{o.unassigned > 0 && <p className="text-xs font-semibold text-amber-700">{o.unassigned} without a path</p>}</div>
        {o.paths.map((p) => (
          <div key={p.slug} className="card p-5" style={{ borderTop: `6px solid ${p.color}` }}>
            <p className="text-sm font-bold text-slate-500">{p.level}</p>
            <p className="font-display text-4xl font-extrabold text-navy">{p.learners}</p>
            <p className="text-xs text-slate-500">{p.completions} lessons completed</p>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <div className="flex flex-wrap items-center gap-3">
          <input className="field max-w-xs !py-2" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search learners" />
          <select className="field max-w-[200px] !py-2" value={path} onChange={(e) => setPath(e.target.value)} aria-label="Filter by path">
            <option value="">All paths</option>
            {o.paths.map((p) => <option key={p.slug} value={p.slug}>{p.level}</option>)}
          </select>
          {msg && <span className="text-sm font-semibold text-navy" aria-live="polite">{msg}</span>}
        </div>
        {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">Learner</th><th className="pr-3">Path</th><th className="pr-3">Progress</th><th>Last active</th></tr></thead>
              <tbody>
                {list.data.learners.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100">
                    <td className="py-3 pr-3"><p className="font-semibold text-navy">{u.name}</p><p className="text-xs text-slate-500">{u.email}</p></td>
                    <td className="pr-3">
                      <select className="rounded-lg border border-slate-300 px-2 py-1" value={u.path || ""} onChange={(e) => e.target.value && change(u.id, e.target.value)} aria-label={`Path for ${u.name}`}>
                        {!u.path && <option value="">Not chosen</option>}
                        {o.paths.map((p) => <option key={p.slug} value={p.slug}>{p.level}</option>)}
                      </select>
                    </td>
                    <td className="pr-3"><div className="w-36"><Bar value={u.completed} total={u.total} /></div><span className="text-xs text-slate-500">{u.completed}/{u.total}</span></td>
                    <td className="text-slate-600">{u.last_active ? new Date(u.last_active).toLocaleDateString("en-GB") : "-"}</td>
                  </tr>
                ))}
                {!list.data.learners.length && <tr><td colSpan={4} className="py-6 text-center text-slate-500">No learners found.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
