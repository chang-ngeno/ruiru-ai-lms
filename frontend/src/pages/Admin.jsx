import { Fragment, useState } from "react";
import { Bar, ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { fmtDate, kes } from "../lib/format";
import { useFetch } from "../lib/hooks";
import { ActivityTab, DeskTab, DiscountsTab, LearnerBillingPanel, PaymentsTab, PricingTab, RefundsTab } from "./AdminBilling";

const TABS = [["learners", "Learners"], ["payments", "Payments"], ["refunds", "Refunds"], ["desk", "Front desk"], ["discounts", "Discounts"], ["pricing", "Pricing"], ["activity", "Activity"]];
const urlCode = () => (typeof window !== "undefined" && window.location ? new URLSearchParams(window.location.search).get("code") || "" : "");

export default function Admin() {
  const [scanCode] = useState(urlCode);
  const [tab, setTab] = useState(scanCode ? "desk" : "learners");
  const [q, setQ] = useState("");
  const [path, setPath] = useState("");
  const [openId, setOpenId] = useState(null);
  const overview = useFetch(() => api.get("/admin/overview"));
  const list = useFetch(() => api.get(`/admin/learners?path=${encodeURIComponent(path)}&q=${encodeURIComponent(q)}`), [path, q]);
  const [msg, setMsg] = useState("");

  const refresh = () => { list.reload(); overview.reload(); };
  const change = async (id, slug) => {
    try {
      await api.patch(`/admin/learners/${id}/path`, { path_slug: slug });
      setMsg("Path updated.");
      refresh();
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (overview.loading && !overview.data) return <Spinner />;
  if (overview.error) return <ErrorBox message={overview.error} onRetry={overview.reload} />;
  const o = overview.data;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-extrabold text-navy">Trainer dashboard</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="card p-5"><p className="text-sm font-bold text-slate-500">Learners</p><p className="font-display text-4xl font-extrabold text-navy">{o.learners}</p>{o.unassigned > 0 && <p className="text-xs font-semibold text-amber-700">{o.unassigned} without a path</p>}</div>
        <div className="card p-5"><p className="text-sm font-bold text-slate-500">Collected (after refunds)</p><p className="font-display text-2xl font-extrabold text-navy">{kes(o.revenue_total)}</p><p className="text-xs text-slate-500">{o.pending_payments} waiting{o.review_payments ? `, ${o.review_payments} to review` : ""}</p>{(o.refunds_waiting > 0 || o.payouts_due > 0) && <p className="text-xs font-semibold text-amber-700">{o.refunds_waiting} refund request(s), {o.payouts_due} payout(s) due</p>}</div>
        {o.paths.map((p) => (
          <div key={p.slug} className="card p-5" style={{ borderTop: `6px solid ${p.color}` }}>
            <p className="text-sm font-bold text-slate-500">{p.level}</p>
            <p className="font-display text-4xl font-extrabold text-navy">{p.learners}</p>
            <p className="text-xs text-slate-500">{kes(p.revenue)} collected</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 overflow-x-auto" role="tablist" aria-label="Trainer sections">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`rounded-full px-5 py-2 font-display text-sm font-bold ${tab === k ? "bg-navy text-white" : "bg-white text-navy ring-1 ring-slate-300 hover:bg-panel"}`}>{label}</button>
        ))}
      </div>

      {tab === "payments" && <PaymentsTab />}
      {tab === "refunds" && <RefundsTab onChanged={refresh} />}
      {tab === "desk" && <DeskTab initialCode={scanCode} />}
      {tab === "discounts" && <DiscountsTab paths={o.paths} />}
      {tab === "activity" && <ActivityTab />}
      {tab === "pricing" && <PricingTab paths={o.paths} reload={overview.reload} />}

      {tab === "learners" && (
        <div className="card p-5">
          <div className="flex flex-wrap items-center gap-3">
            <input className="field max-w-xs !py-2" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search learners" />
            <select className="field max-w-[200px] !py-2" value={path} onChange={(e) => setPath(e.target.value)} aria-label="Filter by path">
              <option value="">All paths</option>
              {o.paths.map((p) => <option key={p.slug} value={p.slug}>{p.level}</option>)}
            </select>
            {msg && <span className="text-sm font-semibold text-navy" aria-live="polite">{msg}</span>}
          </div>
          {list.loading && !list.data ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">Learner</th><th className="pr-3">Path</th><th className="pr-3">Progress</th><th className="pr-3">Paid / due</th><th className="pr-3">Last active</th><th /></tr></thead>
                <tbody>
                  {list.data.learners.map((u) => (
                    <Fragment key={u.id}>
                      <tr className="border-b border-slate-100">
                        <td className="py-3 pr-3"><p className="font-semibold text-navy">{u.name}</p><p className="text-xs text-slate-500">{u.email}</p></td>
                        <td className="pr-3">
                          <select className="rounded-lg border border-slate-300 px-2 py-1" value={u.path || ""} onChange={(e) => e.target.value && change(u.id, e.target.value)} aria-label={`Path for ${u.name}`}>
                            {!u.path && <option value="">Not chosen</option>}
                            {o.paths.map((p) => <option key={p.slug} value={p.slug}>{p.level}</option>)}
                          </select>
                        </td>
                        <td className="pr-3"><div className="w-32"><Bar value={u.completed} total={u.total} /></div><span className="text-xs text-slate-500">{u.completed}/{u.total}</span></td>
                        <td className="pr-3"><p className="font-semibold">{kes(u.paid)} / {kes(u.net)}</p>{u.discount > 0 && <p className="text-xs text-green-700">{kes(u.discount)} discount</p>}</td>
                        <td className="pr-3 text-slate-600">{u.last_active ? fmtDate(u.last_active) : "-"}</td>
                        <td>{u.path && <button className="btn-outline btn-sm" onClick={() => setOpenId(openId === u.id ? null : u.id)} aria-expanded={openId === u.id}>Billing</button>}</td>
                      </tr>
                      {openId === u.id && <tr><td colSpan={6} className="pb-4"><LearnerBillingPanel learner={u} onDone={refresh} /></td></tr>}
                    </Fragment>
                  ))}
                  {!list.data.learners.length && <tr><td colSpan={6} className="py-6 text-center text-slate-500">No learners found.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
