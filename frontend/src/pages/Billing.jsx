import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { FiCheckCircle, FiClock, FiLock, FiMapPin, FiRotateCcw, FiSmartphone, FiTag, FiXCircle } from "react-icons/fi";
import { Bar, ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePageTitle } from "../lib/usePageTitle";
import { fmtDate, fmtDateTime, kes } from "../lib/format";
import { useFetch } from "../lib/hooks";

const REFUND_STATUS = {
  requested: ["Waiting for approval", "bg-amber-100 text-amber-800"],
  approved: ["Approved: payout coming", "bg-blue-100 text-blue-800"],
  paid_out: ["Refunded", "bg-green-100 text-green-800"],
  rejected: ["Not approved", "bg-red-100 text-red-800"],
  cancelled: ["Cancelled", "bg-slate-200 text-slate-700"],
};

function RefundSection({ data, setData, reload }) {
  const r = data.refund;
  const [reason, setReason] = useState("");
  const [amount, setAmount] = useState(String(r.eligible || r.refundable || ""));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (!r.enabled || (r.refundable <= 0 && r.history.length === 0)) return null;

  const guide = `Full refund if you have not started any paid lesson; ${r.partial_percent}% if you start and ask within ${r.partial_days} days of your first payment; after that refunds are at the trainer's discretion. A trainer reviews every request.`;
  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      setData(await api.post("/billing/refund", { reason, amount: Number(amount) }));
      setReason("");
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };
  const cancel = async (id) => {
    try {
      setData(await api.post(`/billing/refund/${id}/cancel`));
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <section className="card p-6">
      <h2 className="flex items-center gap-2 font-display text-lg font-bold text-navy"><FiRotateCcw aria-hidden="true" /> Refunds</h2>
      <p className="mt-2 text-sm text-slate-600">{guide}</p>
      {r.open ? (
        <div className="mt-4 rounded-xl bg-amber-50 p-4">
          <p className="font-semibold text-amber-900">Your request for {kes(r.open.requested_amount)} is waiting for a trainer to review.</p>
          <p className="mt-1 text-sm text-amber-900">Your lessons stay open until it is approved.</p>
          <button className="btn-outline btn-sm mt-3" onClick={() => cancel(r.open.id)}>Cancel request</button>
        </div>
      ) : r.can_request ? (
        <form onSubmit={submit} className="mt-4 space-y-3">
          <p className="rounded-xl bg-panel p-3 text-sm text-navy">
            {r.tier === "full" && <>You have not started a paid lesson, so you can ask for up to <b>{kes(r.eligible)}</b>.</>}
            {r.tier === "partial" && <>You have started, and you are inside the {r.partial_days}-day window: the guide is <b>{kes(r.eligible)}</b> ({r.partial_percent}%).</>}
            {r.tier === "none" && <>The guide amount is KES 0, but you can still ask and a trainer will decide.</>}
            {" "}Refunding closes the weeks and workspace access that the money was paying for.
          </p>
          <label className="block text-sm font-bold text-slate-700">Why are you asking?
            <textarea className="field mt-1" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} required minLength={5} maxLength={500} />
          </label>
          <label className="block text-sm font-bold text-slate-700">Amount you are asking for (KES)
            <input className="field mt-1 max-w-[220px]" type="number" min="1" max={r.refundable} step="1" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          {err && <p className="text-sm font-semibold text-red-700" role="alert">{err}</p>}
          <button className="btn-outline" disabled={busy}>{busy ? "Sending..." : "Request a refund"}</button>
        </form>
      ) : null}
      {!r.open && err && !r.can_request && <p className="mt-2 text-sm font-semibold text-red-700" role="alert">{err}</p>}
      {r.history.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm">
          {r.history.map((h) => {
            const [label, cls] = REFUND_STATUS[h.status] || [h.status, "bg-slate-100"];
            return (
              <li key={h.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 p-3">
                <span className={`chip ${cls}`}>{label}</span>
                <span className="font-semibold">{kes(h.approved_amount ?? h.requested_amount)}</span>
                <span className="text-slate-500">{fmtDate(h.created_at)}</span>
                {h.admin_note && <span className="w-full text-slate-600">Trainer: {h.admin_note}</span>}
                {h.payout_reference && <span className="w-full font-mono text-xs text-slate-600">Payout reference {h.payout_reference}</span>}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

const STATUS = {
  success: ["Paid", "bg-green-100 text-green-800"],
  pending: ["Waiting", "bg-amber-100 text-amber-800"],
  initiated: ["Starting", "bg-amber-100 text-amber-800"],
  failed: ["Not paid", "bg-red-100 text-red-800"],
  expired: ["Expired", "bg-slate-200 text-slate-700"],
  review: ["Under review", "bg-purple-100 text-purple-800"],
};

function Weeks({ open, total }) {
  return (
    <div className="mt-3 flex gap-2" aria-label={`${open} of ${total} weeks unlocked`}>
      {Array.from({ length: total }, (_, i) => (
        <div key={i} className={`flex-1 rounded-xl p-3 text-center text-sm font-bold ${i < open ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-500"}`}>
          {i < open ? <FiCheckCircle className="mx-auto mb-1" aria-hidden="true" /> : <FiLock className="mx-auto mb-1" aria-hidden="true" />}
          Week {i + 1}
        </div>
      ))}
    </div>
  );
}

export default function Billing() {
  const { user } = useAuth();
  usePageTitle("Payments");
  const { data, error, loading, reload, setData } = useFetch(() => api.get("/billing"));
  const [code, setCode] = useState("");
  const [codeMsg, setCodeMsg] = useState({ ok: true, text: "" });
  const [phone, setPhone] = useState(() => localStorage.getItem("rl_phone") || "");
  const [amount, setAmount] = useState("");
  const [formErr, setFormErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState(null); // the payment we are waiting for
  const timer = useRef(null);

  const b = data?.billing;
  useEffect(() => {
    if (b && !amount && b.suggestions?.length) setAmount(String(b.suggestions[0].amount));
  }, [b, amount]);

  // Poll the payment until Safaricom answers (the server also double-checks with Safaricom).
  useEffect(() => {
    if (!active || !["pending", "initiated"].includes(active.status)) return undefined;
    let tries = 0;
    const tick = async () => {
      tries += 1;
      try {
        const r = await api.get(`/billing/payments/${active.id}`);
        setActive(r.payment);
        if (!["pending", "initiated"].includes(r.payment.status)) {
          reload();
          return;
        }
      } catch { /* try again */ }
      if (tries < 45) timer.current = setTimeout(tick, 4000);
      else setActive((a) => ({ ...a, status: "expired", result_desc: "We did not get a reply. If money left your phone, contact your trainer with the M-Pesa message." }));
    };
    timer.current = setTimeout(tick, 4000);
    return () => clearTimeout(timer.current);
  }, [active?.id, active?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const applyCode = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/billing/discount", { code });
      setData(r);
      setCode("");
      setCodeMsg({ ok: true, text: r.message });
    } catch (ex) {
      setCodeMsg({ ok: false, text: ex.message });
    }
  };

  const pay = async (e) => {
    e.preventDefault();
    setFormErr("");
    setBusy(true);
    try {
      localStorage.setItem("rl_phone", phone);
      const r = await api.post("/billing/pay", { phone, amount: Number(amount) });
      setActive(r.payment);
    } catch (ex) {
      setFormErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const simulate = async (success) => {
    const r = await api.post(`/dev/mpesa/complete/${active.id}`, { success });
    setActive(r.payment);
    reload();
  };

  const waiting = active && ["pending", "initiated"].includes(active.status);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="font-display text-3xl font-extrabold text-navy">Payments</h1>
        <p className="mt-1 text-slate-600">{data.path.level} path: {data.path.title}</p>
      </header>

      <section className="card p-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[["Price", kes(b.price)], ["Discount", b.discount ? `- ${kes(b.discount)}` : "None"], ["You pay", kes(b.net)], ["Paid so far", kes(b.paid)]].map(([k, v]) => (
            <div key={k}><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{k}</p><p className="font-display text-xl font-extrabold text-navy">{v}</p></div>
          ))}
        </div>
        {b.discount_code && <p className="mt-2 text-sm font-semibold text-green-700"><FiTag className="mr-1 inline" aria-hidden="true" />Code {b.discount_code} applied{b.discount_note ? `: ${b.discount_note}` : ""}</p>}
        {!b.discount_code && b.discount > 0 && <p className="mt-2 text-sm font-semibold text-green-700"><FiTag className="mr-1 inline" aria-hidden="true" />{b.discount_note || "Discount applied by your trainer"}</p>}
        <div className="mt-4"><Bar value={b.paid} total={b.net || 1} color="#1B8A3A" /></div>
        <p className="mt-1 text-sm font-semibold text-slate-600">{b.fully_paid ? "Fully paid" : `Balance ${kes(b.balance)}`}</p>
        {b.refunded > 0 && <p className="mt-2 text-sm font-semibold text-slate-600">Refunded to you: {kes(b.refunded)}</p>}
        {b.open_all ? (
          <p className="mt-3 rounded-xl bg-green-50 p-3 text-sm font-semibold text-green-800">All lessons are open on your account.</p>
        ) : (
          <>
            <Weeks open={b.unlocked_weeks} total={b.total_weeks} />
            <p className="mt-3 text-sm text-slate-600">Day {b.preview_lessons} is a free preview. Each quarter of the price you pay opens one more week.</p>
          </>
        )}
      </section>

      {data.workspace && (
        <section className="card flex flex-wrap items-center justify-between gap-3 p-5">
          <p className="flex items-center gap-2 font-semibold text-navy"><FiMapPin aria-hidden="true" /> Workspace access:
            <span className={`chip ${data.workspace.active ? "bg-green-100 text-green-800" : "bg-slate-200 text-slate-700"}`}>{data.workspace.active ? "Active" : "Locked"}</span>
          </p>
          <p className="text-sm text-slate-600">{data.workspace.reason}</p>
          <Link to="/app/workspace" className="btn-outline btn-sm">Open my pass</Link>
        </section>
      )}

      {!b.fully_paid && !b.open_all && (
        <section className="card p-6">
          <h2 className="flex items-center gap-2 font-display text-xl font-bold text-navy"><FiSmartphone aria-hidden="true" /> Pay with M-Pesa</h2>
          {!data.mpesa_ready && (
            <p className="mt-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">M-Pesa is not switched on yet. Please pay your trainer directly and they will record it so your lessons unlock.</p>
          )}
          {waiting ? (
            <div className="mt-4 rounded-xl bg-panel p-5 text-center" role="status">
              <FiClock className="mx-auto h-8 w-8 text-navy" aria-hidden="true" />
              <p className="mt-2 font-display text-lg font-bold text-navy">Check your phone</p>
              <p className="text-slate-600">Enter your M-Pesa PIN to pay {kes(active.amount)}. This page updates by itself.</p>
              {data.simulate && (
                <div className="mt-4 flex justify-center gap-2">
                  <button className="btn-navy btn-sm" onClick={() => simulate(true)}>Simulate success</button>
                  <button className="btn-outline btn-sm" onClick={() => simulate(false)}>Simulate cancel</button>
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={pay} className="mt-4 space-y-4">
              {active && active.status === "success" && (
                <p className="flex items-center gap-2 rounded-xl bg-green-50 p-3 font-semibold text-green-800" role="status"><FiCheckCircle /> Payment received{active.receipt ? `, receipt ${active.receipt}` : ""}. Your lessons are unlocked.</p>
              )}
              {active && ["failed", "expired", "review"].includes(active.status) && (
                <p className="flex items-start gap-2 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-800" role="alert"><FiXCircle className="mt-0.5 shrink-0" /> {active.result_desc || "The payment did not go through."} You can try again.</p>
              )}
              <div className="flex flex-wrap gap-2" role="group" aria-label="Quick amounts">
                {b.suggestions.map((s) => (
                  <button type="button" key={s.label} onClick={() => setAmount(String(s.amount))} className={`rounded-full border-2 px-4 py-2 text-sm font-bold ${String(s.amount) === amount ? "border-navy bg-navy text-white" : "border-navy text-navy hover:bg-panel"}`}>
                    {s.label}: {kes(s.amount)}
                  </button>
                ))}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-bold text-slate-700">M-Pesa phone number
                  <input className="field mt-1" inputMode="tel" autoComplete="tel" placeholder="0712 345 678" value={phone} onChange={(e) => setPhone(e.target.value)} required />
                </label>
                <label className="block text-sm font-bold text-slate-700">Amount (KES)
                  <input className="field mt-1" inputMode="numeric" type="number" min={Math.min(b.min_payment, b.balance)} max={b.balance} step="1" value={amount} onChange={(e) => setAmount(e.target.value)} required />
                </label>
              </div>
              {formErr && <p className="text-sm font-semibold text-red-700" role="alert">{formErr}</p>}
              <button className="btn-primary w-full sm:w-auto" disabled={busy || !data.mpesa_ready}>{busy ? "Sending request..." : `Pay ${amount ? kes(amount) : ""} with M-Pesa`}</button>
            </form>
          )}
        </section>
      )}

      {!b.discount_code && b.discount === 0 && !b.fully_paid && (
        <section className="card p-6">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold text-navy"><FiTag aria-hidden="true" /> Have a discount code?</h2>
          <form onSubmit={applyCode} className="mt-3 flex gap-2">
            <input className="field uppercase" placeholder="CODE" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Discount code" />
            <button className="btn-navy" disabled={!code.trim()}>Apply</button>
          </form>
          {codeMsg.text && <p className={`mt-2 text-sm font-semibold ${codeMsg.ok ? "text-green-700" : "text-red-700"}`} role="status">{codeMsg.text}</p>}
        </section>
      )}

      <RefundSection data={data} setData={setData} reload={reload} />

      <section className="card p-6">
        <h2 className="font-display text-lg font-bold text-navy">Payment history</h2>
        {data.payments.length === 0 ? <p className="mt-2 text-slate-500">No payments yet.</p> : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-sm">
              <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2">Date</th><th>Amount</th><th>Method</th><th>Status</th><th>Receipt</th></tr></thead>
              <tbody>
                {data.payments.map((p) => {
                  const [label, cls] = STATUS[p.status] || [p.status, "bg-slate-100"];
                  return (
                    <tr key={p.id} className="border-b border-slate-100">
                      <td className="py-2">{fmtDateTime(p.created_at)}</td>
                      <td className="font-semibold">{kes(p.amount)}</td>
                      <td>{p.method === "manual" ? "Recorded by trainer" : "M-Pesa"}</td>
                      <td><span className={`chip ${cls}`}>{label}</span></td>
                      <td className="font-mono text-xs">{p.receipt || "-"}{p.status === "success" && <><br /><Link to={`/app/receipt/${p.id}`} className="font-sans font-bold text-navy underline">Receipt</Link></>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
