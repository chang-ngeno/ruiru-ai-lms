import { Link } from "react-router-dom";
import { FiLock, FiSmartphone } from "react-icons/fi";
import { kes } from "../lib/format";

/** Shown instead of lesson content (or downloads) that the learner has not paid for yet. */
export default function Paywall({ info, title = "This part is locked" }) {
  const toUnlock = info?.to_unlock;
  return (
    <div className="card mx-auto my-8 max-w-lg p-8 text-center">
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-brand text-navy shadow-glow"><FiLock className="h-7 w-7" aria-hidden="true" /></span>
      <h1 className="mt-4 font-display text-2xl font-extrabold text-navy">{title}</h1>
      <p className="mt-2 text-slate-600">
        {info?.week ? `Week ${info.week} opens as you pay. ` : ""}
        {toUnlock ? `Pay ${kes(toUnlock)} more to unlock it.` : "Make a payment to unlock your lessons."}
      </p>
      <p className="mt-1 text-sm text-slate-500">Pay any amount by M-Pesa. Every quarter of the price opens another week.</p>
      <Link to="/app/billing" className="btn-primary mt-6"><FiSmartphone /> Pay with M-Pesa</Link>
    </div>
  );
}
