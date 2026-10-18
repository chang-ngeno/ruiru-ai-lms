import { QRCodeSVG } from "qrcode.react";
import { Link } from "react-router-dom";
import { FiCheckCircle, FiLock, FiMapPin, FiSun } from "react-icons/fi";
import { ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePageTitle } from "../lib/usePageTitle";
import { fmtDate, kes } from "../lib/format";
import { useFetch } from "../lib/hooks";

/** The learner's digital pass for the training space. It is only active while payments cover it. */
export default function Workspace() {
  const { user } = useAuth();
  usePageTitle("Workspace pass");
  const { data, error, loading, reload } = useFetch(() => api.get("/workspace"));
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const w = data.workspace;
  const link = `${typeof window !== "undefined" && window.location ? window.location.origin : ""}/app/admin?code=${w.code}`;

  return (
    <div className="mx-auto max-w-md space-y-5">
      <header className="text-center">
        <h1 className="font-display text-3xl font-extrabold text-navy">Workspace pass</h1>
        <p className="mt-1 flex items-center justify-center gap-1 text-slate-600"><FiMapPin aria-hidden="true" /> Training space &amp; facility, Ruiru</p>
      </header>

      <div className={`overflow-hidden rounded-3xl shadow-xl ring-1 ${w.active ? "ring-green-300" : "ring-red-200"}`}>
        <div className={`p-5 text-center text-white ${w.active ? "bg-path-beginner" : "bg-slate-500"}`}>
          {w.active ? <FiCheckCircle className="mx-auto h-9 w-9" aria-hidden="true" /> : <FiLock className="mx-auto h-9 w-9" aria-hidden="true" />}
          <p className="mt-1 font-display text-2xl font-extrabold">{w.active ? "ACTIVE" : "LOCKED"}</p>
          <p className="text-sm text-white/90">{w.reason}</p>
        </div>
        <div className="bg-white p-6 text-center">
          <p className="font-display text-xl font-extrabold text-navy">{user.name}</p>
          <p className="text-sm text-slate-500">{user.path.level} path</p>
          {w.active ? (
            <>
              <div className="mx-auto mt-5 inline-block rounded-2xl bg-white p-3 ring-1 ring-slate-200" aria-label="Pass QR code">
                <QRCodeSVG value={link} size={200} level="M" />
              </div>
              <p className="mt-3 font-mono text-lg font-bold tracking-widest text-navy">{w.code}</p>
              {w.until && <p className="mt-1 text-sm text-slate-600">Valid until {fmtDate(w.until)}</p>}
              <p className="mt-4 flex items-center justify-center gap-1 text-xs text-slate-500"><FiSun aria-hidden="true" /> Turn your screen brightness up when you show the code.</p>
            </>
          ) : (
            <div className="mt-5">
              {w.required > 0 && <p className="text-sm text-slate-600">Access starts once you have paid {kes(w.required)} ({w.min_percent}% of your price). You have paid {kes(w.paid)}.</p>}
              <Link to="/app/billing" className="btn-primary mt-4">Pay with M-Pesa</Link>
            </div>
          )}
        </div>
      </div>
      <p className="text-center text-xs text-slate-500">Show this at the front desk. The pass lasts {w.days} days from your first payment unless your trainer extends it. If you are refunded, the pass stops.</p>
    </div>
  );
}
