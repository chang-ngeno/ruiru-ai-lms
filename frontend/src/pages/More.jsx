import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FiAward, FiDownload, FiFileText, FiLock, FiPackage, FiPrinter, FiSearch, FiSettings } from "react-icons/fi";
import { Bar, ErrorBox, Logo, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useFetch } from "../lib/hooks";

export function Resources() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useFetch(() => api.get("/resources"));
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  return (
    <div>
      <h1 className="font-display text-3xl font-extrabold text-navy">Resources</h1>
      <p className="mt-1 text-slate-600">Download the materials for the <b>{user.path.level}</b> path. Print the workbook and bring it to class.</p>
      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        {data.resources.map((r) => (
          <div key={r.key} className="card flex flex-col p-6">
            <span className="grid h-12 w-12 place-items-center rounded-xl text-white" style={{ background: user.path.color }}>{r.kind === "ZIP" ? <FiPackage className="h-6 w-6" /> : <FiFileText className="h-6 w-6" />}</span>
            <h2 className="mt-4 font-display text-lg font-bold text-navy">{r.title}</h2>
            <p className="mt-1 flex-1 text-sm text-slate-600">{r.desc}</p>
            <a className="btn-navy btn-sm mt-4 self-start" href={`/api/resources/${r.key}`} download><FiDownload /> Download {r.kind}</a>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Glossary() {
  const { data, error, loading, reload } = useFetch(() => api.get("/glossary"));
  const [q, setQ] = useState("");
  const terms = useMemo(() => {
    const all = data?.terms || [];
    const s = q.trim().toLowerCase();
    return s ? all.filter((t) => t.term.toLowerCase().includes(s) || t.meaning.toLowerCase().includes(s)) : all;
  }, [data, q]);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  return (
    <div>
      <h1 className="font-display text-3xl font-extrabold text-navy">Glossary</h1>
      <p className="mt-1 text-slate-600">{data.terms.length} key words from your lessons.</p>
      <label className="relative mt-5 block max-w-md">
        <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <input className="field !pl-11" placeholder="Search words..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search glossary" />
      </label>
      <dl className="mt-6 grid gap-3 md:grid-cols-2">
        {terms.map((t) => (
          <div key={t.term} className="card p-4">
            <dt className="font-display font-bold text-navy">{t.term}</dt>
            <dd className="mt-1 text-slate-700">{t.meaning}</dd>
            <Link to={`/app/learn/${t.lesson}`} className="mt-2 inline-block text-xs font-bold text-navy-700 underline">Day {t.lesson}: {t.lesson_title}</Link>
          </div>
        ))}
        {!terms.length && <p className="text-slate-500">No words match your search.</p>}
      </dl>
    </div>
  );
}

export function Profile() {
  const { user, logout } = useAuth();
  const { data } = useFetch(() => api.get("/progress"));
  const s = data?.summary;
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="card flex items-center gap-5 p-6">
        {user.picture ? <img src={user.picture} alt="" referrerPolicy="no-referrer" className="h-20 w-20 rounded-full object-cover" /> : <span className="grid h-20 w-20 place-items-center rounded-full bg-navy font-display text-2xl font-bold text-white">{user.name.slice(0, 1).toUpperCase()}</span>}
        <div>
          <h1 className="font-display text-2xl font-extrabold text-navy">{user.name}</h1>
          <p className="text-slate-600">{user.email}</p>
          {user.role === "admin" && <span className="chip mt-2 bg-brand text-navy">Administrator</span>}
        </div>
      </div>
      <div className="card p-6">
        <span className="chip text-white" style={{ background: user.path.color }}>{user.path.level}</span>
        <h2 className="mt-2 font-display text-xl font-bold text-navy">{user.path.title}</h2>
        {s && (<><div className="mt-4"><Bar value={s.completed} total={s.total} color={user.path.color} /></div><p className="mt-2 text-sm font-semibold text-slate-600">{s.completed} of {s.total} lessons complete &middot; {s.streak} day streak</p></>)}
        <p className="mt-4 text-sm text-slate-500">Need to change path? Talk to your trainer, who can update it for you.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link to="/app/certificate" className="btn-outline btn-sm"><FiAward /> Certificate</Link>
          {user.role === "admin" && <Link to="/app/admin" className="btn-outline btn-sm"><FiSettings /> Admin</Link>}
        </div>
      </div>
      <button onClick={logout} className="btn-navy w-full">Sign out</button>
    </div>
  );
}

export function Certificate() {
  const { data, error, loading, reload } = useFetch(() => api.get("/certificate"));
  const summary = useFetch(() => api.get("/progress"));
  if (loading) return <Spinner />;
  if (error) {
    const s = summary.data?.summary;
    return (
      <div className="card mx-auto max-w-lg p-8 text-center">
        <FiLock className="mx-auto h-10 w-10 text-slate-400" aria-hidden="true" />
        <h1 className="mt-3 font-display text-2xl font-extrabold text-navy">Certificate locked</h1>
        <p className="mt-2 text-slate-600">{error}</p>
        {s && <div className="mt-4"><Bar value={s.completed} total={s.total} /><p className="mt-2 text-sm font-semibold text-slate-500">{s.completed} of {s.total} lessons</p></div>}
        <div className="mt-5 flex justify-center gap-3"><Link to="/app/curriculum" className="btn-navy btn-sm">Back to course</Link><button className="btn-outline btn-sm" onClick={reload}>Check again</button></div>
      </div>
    );
  }
  const date = data.completed_at ? new Date(data.completed_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "";
  return (
    <div>
      <div className="no-print mb-4 flex justify-end"><button className="btn-primary btn-sm" onClick={() => window.print()}><FiPrinter /> Print or save as PDF</button></div>
      <div className="mx-auto aspect-[1.414/1] w-full max-w-4xl overflow-hidden bg-white shadow-xl" style={{ border: "14px solid #0B2A6F", outline: "4px solid #F5D90A", outlineOffset: "-22px" }}>
        <div className="flex h-full flex-col items-center justify-center px-6 text-center md:px-16">
          <Logo dark />
          <p className="mt-6 font-script text-3xl text-navy-700">Certificate of Completion</p>
          <p className="mt-3 text-sm text-slate-500">This certifies that</p>
          <h1 className="mt-1 font-display text-3xl font-extrabold text-navy md:text-5xl"><span className="brush">{data.name}</span></h1>
          <p className="mt-5 max-w-xl text-slate-700">has successfully completed the <b>{data.path.level}</b> path, <b>{data.path.title}</b>, a hands-on programme of 20 lessons and about {data.hours} learning hours.</p>
          <div className="mt-8 flex w-full max-w-xl items-end justify-between text-xs text-slate-500">
            <div><p className="border-t border-slate-400 pt-1 font-semibold text-slate-700">{date}</p>Date</div>
            <div className="font-display font-bold text-navy">Learn. Build. Grow.</div>
            <div><p className="border-t border-slate-400 pt-1 font-mono font-semibold text-slate-700">{data.code}</p>Certificate ID</div>
          </div>
        </div>
      </div>
    </div>
  );
}
