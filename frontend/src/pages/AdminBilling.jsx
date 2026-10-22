import { Fragment, useEffect, useRef, useState } from "react";
import { ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { fmtDate, fmtDateTime, kes } from "../lib/format";
import { useFetch } from "../lib/hooks";

const STATUS_CLS = {
  success: "bg-green-100 text-green-800",
  pending: "bg-amber-100 text-amber-800",
  initiated: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
  expired: "bg-slate-200 text-slate-700",
  review: "bg-purple-100 text-purple-800",
};

/** Inline panel under a learner row: record a cash/bank payment or give a discount. */
export function LearnerBillingPanel({ learner, onDone }) {
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("Cash payment");
  const [percent, setPercent] = useState("");
  const [fixed, setFixed] = useState("");
  const [reason, setReason] = useState("");
  const [until, setUntil] = useState("");
  const [refundAmt, setRefundAmt] = useState("");
  const [refundWhy, setRefundWhy] = useState("");
  const [msg, setMsg] = useState({ ok: true, text: "" });

  const run = async (fn, okText) => {
    try {
      await fn();
      setMsg({ ok: true, text: okText });
      onDone();
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    }
  };

  return (
    <div className="grid gap-4 rounded-xl bg-panel p-4 md:grid-cols-2">
      <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); run(() => api.post("/admin/payments/manual", { user_id: learner.id, amount: Number(amount), note }), "Payment recorded."); }}>
        <p className="font-display font-bold text-navy">Record a cash or bank payment</p>
        <div className="flex gap-2">
          <input className="field !py-2" type="number" min="1" placeholder="Amount KES" value={amount} onChange={(e) => setAmount(e.target.value)} required aria-label="Amount" />
          <input className="field !py-2" placeholder="Note" value={note} onChange={(e) => setNote(e.target.value)} aria-label="Note" />
        </div>
        <button className="btn-navy btn-sm">Record payment</button>
      </form>
      <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); run(() => api.post(`/admin/learners/${learner.id}/discount`, percent ? { percent: Number(percent), reason } : { amount: Number(fixed || 0), reason }), "Discount saved."); }}>
        <p className="font-display font-bold text-navy">Give a discount or scholarship</p>
        <div className="flex gap-2">
          <input className="field !py-2" type="number" min="0" max="100" placeholder="% off" value={percent} onChange={(e) => { setPercent(e.target.value); setFixed(""); }} aria-label="Percent off" />
          <input className="field !py-2" type="number" min="0" placeholder="or KES off" value={fixed} onChange={(e) => { setFixed(e.target.value); setPercent(""); }} aria-label="KES off" />
        </div>
        <input className="field !py-2" placeholder="Reason (kept on record)" value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Reason" />
        <button className="btn-outline btn-sm">Save discount</button>
        <p className="text-xs text-slate-500">100% = fully open. Enter 0 to remove a discount.</p>
      </form>
      <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); run(() => api.post(`/admin/learners/${learner.id}/workspace`, { until: until || null }), until ? "Workspace pass end date saved." : "Workspace pass back to the normal period."); }}>
        <p className="font-display font-bold text-navy">Workspace pass end date</p>
        <div className="flex gap-2">
          <input className="field !py-2" type="date" value={until} onChange={(e) => setUntil(e.target.value)} aria-label="Workspace pass valid until" />
          <button className="btn-outline btn-sm">{until ? "Set date" : "Reset"}</button>
        </div>
        <p className="text-xs text-slate-500">Leave empty and press Reset to use the normal period from the first payment.</p>
      </form>
      <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); run(() => api.post("/admin/refunds", { user_id: learner.id, amount: Number(refundAmt), reason: refundWhy }), "Refund approved. Send the money, then mark it paid out in the Refunds tab."); }}>
        <p className="font-display font-bold text-navy">Start a refund for this learner</p>
        <div className="flex gap-2">
          <input className="field !py-2" type="number" min="1" placeholder="Amount KES" value={refundAmt} onChange={(e) => setRefundAmt(e.target.value)} required aria-label="Refund amount" />
          <input className="field !py-2" placeholder="Reason" value={refundWhy} onChange={(e) => setRefundWhy(e.target.value)} aria-label="Refund reason" />
        </div>
        <button className="btn-outline btn-sm">Approve refund</button>
        <p className="text-xs text-slate-500">Reduces what they have paid, so weeks and the workspace pass close if it falls below what they cover.</p>
      </form>
      {msg.text && <p className={`text-sm font-semibold md:col-span-2 ${msg.ok ? "text-green-700" : "text-red-700"}`} role="status">{msg.text}</p>}
      <p className="text-xs text-slate-500 md:col-span-2">Price {kes(learner.price)} &middot; discount {kes(learner.discount)} &middot; net {kes(learner.net)} &middot; paid {kes(learner.paid)}</p>
    </div>
  );
}

export function PaymentsTab() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [note, setNote] = useState("");
  const { data, error, loading, reload } = useFetch(() => api.get(`/admin/payments?status=${status}&q=${encodeURIComponent(q)}`), [status, q]);
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center gap-3">
        <input className="field max-w-xs !py-2" placeholder="Search name, email or receipt" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search payments" />
        <select className="field max-w-[180px] !py-2" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {["success", "pending", "failed", "expired", "review"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn-outline btn-sm" onClick={reload}>Refresh</button>
        <button className="btn-outline btn-sm" onClick={async () => { try { const r = await api.post("/admin/payments/reconcile"); setNote(`Checked ${r.checked} waiting payment(s); ${r.updated} updated.`); reload(); } catch (e) { setNote(e.message); } }}>Check waiting payments with Safaricom</button>
        <a className="btn-outline btn-sm" href="/api/admin/payments.csv" download>Download CSV</a>
        {note && <span className="text-sm font-semibold text-navy" aria-live="polite">{note}</span>}
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={reload} /> : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">Date</th><th className="pr-3">Learner</th><th className="pr-3">Path</th><th className="pr-3">Amount</th><th className="pr-3">Method</th><th className="pr-3">Status</th><th>Receipt / note</th></tr></thead>
            <tbody>
              {data.payments.map((p) => (
                <tr key={p.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3">{fmtDateTime(p.created_at)}</td>
                  <td className="pr-3"><p className="font-semibold text-navy">{p.learner}</p><p className="text-xs text-slate-500">{p.email}</p></td>
                  <td className="pr-3">{p.path}</td>
                  <td className="pr-3 font-semibold">{kes(p.amount)}</td>
                  <td className="pr-3">{p.method === "manual" ? "Manual" : `M-Pesa ${p.phone || ""}`}</td>
                  <td className="pr-3"><span className={`chip ${STATUS_CLS[p.status] || "bg-slate-100"}`}>{p.status}</span></td>
                  <td className="font-mono text-xs">{p.receipt || p.note || p.result_desc || "-"}</td>
                </tr>
              ))}
              {!data.payments.length && <tr><td colSpan={7} className="py-6 text-center text-slate-500">No payments found.</td></tr>}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-500">"review" means the amount Safaricom reported did not match the request. Check the M-Pesa statement, then record a manual payment if the money arrived.</p>
        </div>
      )}
    </div>
  );
}

export function DiscountsTab({ paths }) {
  const { data, error, loading, reload } = useFetch(() => api.get("/admin/discounts"));
  const blank = { code: "", kind: "percent", value: "", path: "", max_redemptions: "", valid_until: "", user_email: "", description: "" };
  const [f, setF] = useState(blank);
  const [msg, setMsg] = useState({ ok: true, text: "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/discounts", { ...f, value: Number(f.value), max_redemptions: f.max_redemptions || null, valid_until: f.valid_until || null, path: f.path || null, user_email: f.user_email || null });
      setF(blank);
      setMsg({ ok: true, text: "Code created." });
      reload();
    } catch (ex) {
      setMsg({ ok: false, text: ex.message });
    }
  };
  const toggle = async (c) => {
    await api.patch(`/admin/discounts/${c.id}`, { active: !c.active });
    reload();
  };

  return (
    <div className="space-y-6">
      <form onSubmit={create} className="card grid gap-3 p-5 md:grid-cols-4">
        <h2 className="font-display text-lg font-bold text-navy md:col-span-4">New discount code</h2>
        <input className="field uppercase" placeholder="CODE (e.g. EARLY10)" value={f.code} onChange={set("code")} required aria-label="Code" />
        <select className="field" value={f.kind} onChange={set("kind")} aria-label="Type"><option value="percent">Percent off</option><option value="fixed">KES off</option></select>
        <input className="field" type="number" min="1" placeholder={f.kind === "percent" ? "Percent (1-100)" : "Amount in KES"} value={f.value} onChange={set("value")} required aria-label="Value" />
        <select className="field" value={f.path} onChange={set("path")} aria-label="Path"><option value="">Any path</option>{paths.map((p) => <option key={p.slug} value={p.slug}>{p.level} only</option>)}</select>
        <input className="field" type="number" min="1" placeholder="Max uses (optional)" value={f.max_redemptions} onChange={set("max_redemptions")} aria-label="Maximum uses" />
        <input className="field" type="date" value={f.valid_until} onChange={set("valid_until")} aria-label="Valid until" title="Valid until (optional)" />
        <input className="field md:col-span-2" type="email" placeholder="Only for this learner's email (optional)" value={f.user_email} onChange={set("user_email")} aria-label="Learner email" />
        <input className="field md:col-span-3" placeholder="Description, e.g. Early bird October cohort" value={f.description} onChange={set("description")} aria-label="Description" />
        <button className="btn-primary">Create code</button>
        {msg.text && <p className={`text-sm font-semibold md:col-span-4 ${msg.ok ? "text-green-700" : "text-red-700"}`} role="status">{msg.text}</p>}
      </form>
      <div className="card p-5">
        {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={reload} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">Code</th><th className="pr-3">Discount</th><th className="pr-3">Applies to</th><th className="pr-3">Used</th><th className="pr-3">Expires</th><th>Status</th></tr></thead>
              <tbody>
                {data.discounts.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2 pr-3"><p className="font-mono font-bold text-navy">{c.code}</p><p className="text-xs text-slate-500">{c.description}</p></td>
                    <td className="pr-3 font-semibold">{c.kind === "percent" ? `${c.value}%` : kes(c.value)}</td>
                    <td className="pr-3">{c.path || "Any path"}{c.user_email ? ` / ${c.user_email}` : ""}</td>
                    <td className="pr-3">{c.used}{c.max_redemptions ? ` / ${c.max_redemptions}` : ""}</td>
                    <td className="pr-3">{c.valid_until ? fmtDate(c.valid_until) : "Never"}</td>
                    <td><button className={`chip ${c.active ? "bg-green-100 text-green-800" : "bg-slate-200 text-slate-600"}`} onClick={() => toggle(c)} title="Click to switch on/off">{c.active ? "Active" : "Off"}</button></td>
                  </tr>
                ))}
                {!data.discounts.length && <tr><td colSpan={6} className="py-6 text-center text-slate-500">No codes yet.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function PricingTab({ paths, reload }) {
  const [vals, setVals] = useState(Object.fromEntries(paths.map((p) => [p.slug, String(p.price_kes)])));
  const [msg, setMsg] = useState({ ok: true, text: "" });
  const save = async (slug) => {
    try {
      await api.patch(`/admin/paths/${slug}`, { price_kes: Number(vals[slug]) });
      setMsg({ ok: true, text: "Price saved. Learners who have not paid yet will see the new price." });
      reload();
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    }
  };
  return (
    <div className="card p-5">
      <h2 className="font-display text-lg font-bold text-navy">Path prices (KES)</h2>
      <div className="mt-4 space-y-3">
        {paths.map((p) => (
          <div key={p.slug} className="flex flex-wrap items-center gap-3">
            <span className="chip w-32 justify-center text-white" style={{ background: p.color }}>{p.level}</span>
            <input className="field max-w-[180px] !py-2" type="number" min="0" value={vals[p.slug]} onChange={(e) => setVals({ ...vals, [p.slug]: e.target.value })} aria-label={`${p.level} price`} />
            <button className="btn-navy btn-sm" onClick={() => save(p.slug)}>Save</button>
            <span className="text-sm text-slate-500">Collected so far: {kes(p.revenue)}</span>
          </div>
        ))}
      </div>
      {msg.text && <p className={`mt-3 text-sm font-semibold ${msg.ok ? "text-green-700" : "text-red-700"}`} role="status">{msg.text}</p>}
      <p className="mt-4 text-xs text-slate-500">A learner who has already paid keeps the price they were quoted. Setting a price to 0 makes that path free and fully open.</p>
    </div>
  );
}



const REFUND_CLS = {
  requested: "bg-amber-100 text-amber-800",
  approved: "bg-blue-100 text-blue-800",
  paid_out: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-slate-200 text-slate-700",
};
const TIER = { full: "Full refund", partial: "Partial", none: "Outside guide" };

function RefundRow({ r, onChanged }) {
  const [amount, setAmount] = useState(String(r.eligible_amount || r.requested_amount));
  const [note, setNote] = useState("");
  const [ref, setRef] = useState("");
  const [err, setErr] = useState("");

  const act = async (path, body) => {
    setErr("");
    try {
      await api.post(`/admin/refunds/${r.id}/${path}`, body);
      onChanged();
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <tr className="border-b border-slate-100 align-top">
      <td className="py-3 pr-3">{fmtDateTime(r.created_at)}</td>
      <td className="pr-3"><p className="font-semibold text-navy">{r.learner}</p><p className="text-xs text-slate-500">{r.email} &middot; {r.path}</p></td>
      <td className="pr-3"><p className="font-semibold">{kes(r.requested_amount)}</p><p className="text-xs text-slate-500">Guide: {TIER[r.policy_tier]} {r.eligible_amount ? `(${kes(r.eligible_amount)})` : ""}</p></td>
      <td className="max-w-[220px] pr-3 text-slate-700">{r.reason}</td>
      <td className="pr-3"><span className={`chip ${REFUND_CLS[r.status] || "bg-slate-100"}`}>{r.status.replace("_", " ")}</span>{r.approved_amount != null && <p className="mt-1 text-xs font-semibold">{kes(r.approved_amount)}</p>}</td>
      <td className="min-w-[230px]">
        {r.status === "requested" && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input className="field !py-1.5 text-sm" type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Amount to approve" />
              <button className="btn-navy btn-sm" onClick={() => act("approve", { amount: Number(amount), note })}>Approve</button>
            </div>
            <input className="field !py-1.5 text-sm" placeholder="Note to learner (required to reject)" value={note} onChange={(e) => setNote(e.target.value)} aria-label="Note" />
            <button className="btn-outline btn-sm" onClick={() => act("reject", { note })}>Reject</button>
          </div>
        )}
        {r.status === "approved" && (
          <div className="space-y-2">
            <p className="text-xs text-slate-600">Send {kes(r.approved_amount)} to the learner (M-Pesa or bank), then record the reference.</p>
            <div className="flex gap-2">
              <input className="field !py-1.5 text-sm" placeholder="M-Pesa / bank reference" value={ref} onChange={(e) => setRef(e.target.value)} aria-label="Payout reference" />
              <button className="btn-navy btn-sm" onClick={() => act("paid-out", { method: "M-Pesa", reference: ref })}>Paid out</button>
            </div>
          </div>
        )}
        {["paid_out", "rejected", "cancelled"].includes(r.status) && <p className="text-xs text-slate-600">{r.payout_reference ? `Reference ${r.payout_reference}` : r.admin_note || "-"}</p>}
        {err && <p className="mt-1 text-xs font-semibold text-red-700" role="alert">{err}</p>}
      </td>
    </tr>
  );
}

export function RefundsTab({ onChanged }) {
  const [status, setStatus] = useState("");
  const { data, error, loading, reload } = useFetch(() => api.get(`/admin/refunds?status=${status}`), [status]);
  const changed = () => { reload(); if (onChanged) onChanged(); };
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center gap-3">
        <select className="field max-w-[220px] !py-2" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter refunds">
          <option value="">All requests</option>
          <option value="requested">Waiting for approval</option>
          <option value="approved">Approved, payout due</option>
          <option value="paid_out">Paid out</option>
          <option value="rejected">Rejected</option>
        </select>
        <button className="btn-outline btn-sm" onClick={reload}>Refresh</button>
        <a className="btn-outline btn-sm" href="/api/admin/refunds.csv" download>Download CSV</a>
      </div>
      <p className="mt-3 text-xs text-slate-500">Approving takes the amount off what the learner has paid right away, which closes the weeks and workspace access it was covering. Send the money yourself from your M-Pesa or bank, then press "Paid out" with the reference.</p>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={reload} /> : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">Date</th><th className="pr-3">Learner</th><th className="pr-3">Asked / guide</th><th className="pr-3">Reason</th><th className="pr-3">Status</th><th>Action</th></tr></thead>
            <tbody>
              {data.refunds.map((r) => <RefundRow key={r.id} r={r} onChanged={changed} />)}
              {!data.refunds.length && <tr><td colSpan={6} className="py-6 text-center text-slate-500">No refund requests.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Front desk: check a workspace pass (type the code or open the learner's QR link) and log the scan. */
export function DeskTab({ initialCode = "" }) {
  const [code, setCode] = useState(initialCode);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const ran = useRef(false);
  const recent = useFetch(() => api.get("/admin/workspace/checkins"));

  const check = async (value) => {
    setErr("");
    try {
      setResult(await api.post("/admin/workspace/verify", { code: value }));
      recent.reload();
    } catch (e) {
      setErr(e.message);
    }
  };
  useEffect(() => {
    if (initialCode && !ran.current) {
      ran.current = true;
      check(initialCode);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card p-5">
        <h2 className="font-display text-lg font-bold text-navy">Check a workspace pass</h2>
        <p className="mt-1 text-sm text-slate-600">Scan the learner's QR code with your phone camera (it opens this screen), or type the code shown under it.</p>
        <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (code.trim()) check(code.trim()); }}>
          <input className="field font-mono uppercase" placeholder="WS-1A-1B2C3D4E" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Pass code" autoFocus />
          <button className="btn-primary" disabled={!code.trim()}>Check</button>
        </form>
        {err && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{err}</p>}
        {result && (
          <div className={`mt-5 rounded-2xl p-5 text-white ${result.allowed ? "bg-path-beginner" : "bg-red-600"}`} role="status">
            <p className="font-display text-3xl font-extrabold">{result.allowed ? "ALLOWED" : "NOT ALLOWED"}</p>
            <p className="mt-1">{result.reason}</p>
            {result.learner && (
              <div className="mt-4 flex items-center gap-3 rounded-xl bg-white/15 p-3">
                {result.learner.picture ? <img src={result.learner.picture} alt="" referrerPolicy="no-referrer" className="h-14 w-14 rounded-full object-cover" /> : <span className="grid h-14 w-14 place-items-center rounded-full bg-white/30 font-display text-xl font-bold">{result.learner.name.slice(0, 1)}</span>}
                <div><p className="font-display font-bold">{result.learner.name}</p><p className="text-sm text-white/90">{result.learner.path} path{result.until ? ` \u00b7 until ${fmtDate(result.until)}` : ""}</p></div>
              </div>
            )}
            <p className="mt-3 text-xs text-white/80">Check the name and photo match the person in front of you.</p>
          </div>
        )}
      </div>
      <div className="card p-5">
        <h2 className="font-display text-lg font-bold text-navy">Last 24 hours</h2>
        {recent.loading ? <Spinner /> : recent.error ? <ErrorBox message={recent.error} onRetry={recent.reload} /> : (
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {recent.data.checkins.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-3 py-2">
                <span><b className="text-navy">{c.learner}</b> <span className="text-xs text-slate-500">{fmtDateTime(c.at)}</span></span>
                <span className={`chip ${c.allowed ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{c.allowed ? "In" : "Refused"}</span>
              </li>
            ))}
            {!recent.data.checkins.length && <li className="py-4 text-slate-500">No scans yet.</li>}
          </ul>
        )}
      </div>
    </div>
  );
}


/** Who did what: every admin action on money, prices, access and refunds is recorded here. */
export function ActivityTab() {
  const [filter, setFilter] = useState("");
  const { data, error, loading, reload } = useFetch(() => api.get(`/admin/audit?action=${encodeURIComponent(filter)}`), [filter]);
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center gap-3">
        <select className="field max-w-[220px] !py-2" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter activity">
          <option value="">Everything</option>
          <option value="payment">Payments</option>
          <option value="refund">Refunds</option>
          <option value="discount">Discounts</option>
          <option value="price">Price changes</option>
          <option value="learner">Learner changes</option>
          <option value="workspace">Workspace</option>
        </select>
        <button className="btn-outline btn-sm" onClick={reload}>Refresh</button>
      </div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={reload} /> : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2 pr-3">When</th><th className="pr-3">Who</th><th className="pr-3">Action</th><th className="pr-3">About</th><th>Details</th></tr></thead>
            <tbody>
              {data.entries.map((a) => (
                <tr key={a.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3">{fmtDateTime(a.at)}</td><td className="pr-3 font-semibold text-navy">{a.who}</td>
                  <td className="pr-3 font-mono text-xs">{a.action}</td><td className="pr-3 font-mono text-xs">{a.target}</td><td className="text-slate-600">{a.detail}</td>
                </tr>
              ))}
              {!data.entries.length && <tr><td colSpan={5} className="py-6 text-center text-slate-500">Nothing recorded yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


/** Check the M-Pesa setup and see exactly what Safaricom answers. */
export function MpesaTab() {
  const { data, error, loading, reload } = useFetch(() => api.get("/admin/mpesa/status"));
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const run = async (withPhone) => {
    setBusy(true);
    setErr("");
    setResult(null);
    try {
      setResult(await api.post("/admin/mpesa/test", withPhone ? { phone } : {}));
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const s = (result && result.settings) || data.settings;
  const rows = [["Product", s.product], ["Environment", s.env + (s.simulate ? " (simulation on)" : "")], ["Transaction type", s.transaction_type], ["Shortcode (BusinessShortCode)", s.shortcode || "-"], ["Party B (receiving party)", s.party_b || "-"], ["Safaricom address", s.base_url], ["Callback URL", s.callback_url]];

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <h2 className="font-display text-lg font-bold text-navy">M-Pesa settings (secrets hidden)</h2>
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[220px_1fr]">
          {rows.map(([k, v]) => (<Fragment key={k}><dt className="text-slate-500">{k}</dt><dd className="break-all font-mono text-navy">{v}</dd></Fragment>))}
        </dl>
        {s.warnings.length ? (
          <ul className="mt-4 space-y-1 rounded-xl bg-amber-50 p-4 text-sm font-semibold text-amber-900">{s.warnings.map((w) => <li key={w}>&bull; {w}</li>)}</ul>
        ) : (
          <p className="mt-4 rounded-xl bg-green-50 p-3 text-sm font-semibold text-green-800">The settings look complete.</p>
        )}
        {s.product.startsWith("Till") && (
          <p className="mt-3 text-xs text-slate-500">Till (Buy Goods): the shortcode is your store / head-office number, party B is the Till number, and the passkey is the one Safaricom issued for that shortcode. STK Push for Buy Goods only works in production.</p>
        )}
      </div>
      <div className="card p-5">
        <h2 className="font-display text-lg font-bold text-navy">Test it</h2>
        <p className="mt-1 text-sm text-slate-600">Step 1 checks your keys. Step 2 sends a KES 1 prompt to a phone so you can see Safaricom's real answer. The test is not credited to any learner.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="btn-outline btn-sm" disabled={busy} onClick={() => run(false)}>Test connection only</button>
          <input className="field max-w-[220px] !py-2" placeholder="0712 345 678" value={phone} onChange={(e) => setPhone(e.target.value)} aria-label="Phone for the test prompt" />
          <button className="btn-navy btn-sm" disabled={busy || !phone.trim()} onClick={() => run(true)}>{busy ? "Testing..." : "Send KES 1 test prompt"}</button>
        </div>
        {err && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{err}</p>}
        {result && (
          <ol className="mt-4 space-y-2">
            {result.steps.map((st) => (
              <li key={st.name} className={`rounded-xl p-3 text-sm ${st.ok ? "bg-green-50 text-green-900" : "bg-red-50 text-red-900"}`}>
                <p className="font-bold">{st.ok ? "OK" : "FAILED"}: {st.name}</p>
                {st.detail && <p className="mt-1 break-words">{st.detail}</p>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
