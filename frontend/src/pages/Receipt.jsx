import { Link, useParams } from "react-router-dom";
import { FiArrowLeft, FiPrinter } from "react-icons/fi";
import { ErrorBox, Logo, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { fmtDateTime, kes } from "../lib/format";
import { useFetch } from "../lib/hooks";
import { usePageTitle } from "../lib/usePageTitle";

export default function Receipt() {
  const { id } = useParams();
  usePageTitle("Receipt");
  const { data, error, loading, reload } = useFetch(() => api.get(`/billing/payments/${id}/receipt`), [id]);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const r = data.receipt;
  return (
    <div className="mx-auto max-w-xl">
      <div className="no-print mb-4 flex items-center justify-between">
        <Link to="/app/billing" className="flex items-center gap-1 text-sm font-bold text-navy"><FiArrowLeft /> Payments</Link>
        <button className="btn-primary btn-sm" onClick={() => window.print()}><FiPrinter /> Print or save as PDF</button>
      </div>
      <div className="card p-8">
        <Logo dark />
        <h1 className="mt-6 font-display text-2xl font-extrabold text-navy">Payment receipt</h1>
        <p className="font-mono text-sm text-slate-500">No. {r.number}</p>
        <dl className="mt-6 grid grid-cols-2 gap-y-3 text-sm">
          <dt className="text-slate-500">Received from</dt><dd className="font-semibold text-navy">{r.learner}<br /><span className="font-normal text-slate-500">{r.email}</span></dd>
          <dt className="text-slate-500">For</dt><dd className="font-semibold text-navy">{r.path}</dd>
          <dt className="text-slate-500">Date</dt><dd>{fmtDateTime(r.date)}</dd>
          <dt className="text-slate-500">Method</dt><dd>{r.method}</dd>
          <dt className="text-slate-500">Amount paid</dt><dd className="font-display text-xl font-extrabold text-navy">{kes(r.amount)}</dd>
        </dl>
        <div className="mt-6 rounded-xl bg-panel p-4 text-sm">
          <p>Course fee after discount: <b>{kes(r.net_price)}</b></p>
          <p>Paid to date: <b>{kes(r.paid_to_date)}</b></p>
          <p>Balance: <b>{kes(r.balance)}</b></p>
        </div>
        <p className="mt-6 text-xs text-slate-500">AI Training for Everyone, Ruiru, Kenya. Thank you for learning with us.</p>
      </div>
    </div>
  );
}
