import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { FiArrowLeft, FiArrowRight, FiShield } from "react-icons/fi";
import GoogleButton, { DevLogin } from "../components/GoogleButton";
import { Footer, PublicNav } from "../components/Layout";
import { Logo, PathCard, PathIcon, Spinner, ErrorBox } from "../components/ui";
import { api } from "../lib/api";
import { recallPath, rememberPath, useAuth } from "../lib/auth";

function usePaths() {
  const [paths, setPaths] = useState(null);
  const [error, setError] = useState("");
  const load = () => {
    setError("");
    api.get("/paths").then((d) => setPaths(d.paths)).catch((e) => setError(e.message));
  };
  useEffect(load, []);
  return { paths, error, reload: load };
}

function Shell({ children }) {
  return (
    <div className="min-h-screen bg-panel">
      <PublicNav />
      <div className="mx-auto max-w-6xl px-4 py-10 md:py-14">{children}</div>
      <Footer />
    </div>
  );
}

/** Sign up = (1) choose one of the three paths, (2) continue with Google. */
export function Signup() {
  const { user, signInWithGoogle } = useAuth();
  const nav = useNavigate();
  const { paths, error, reload } = usePaths();
  const [chosen, setChosen] = useState(recallPath());
  const [step, setStep] = useState(recallPath() ? 2 : 1);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={user.path ? "/app" : "/choose-path"} replace />;
  const path = paths?.find((p) => p.slug === chosen);

  const pick = (slug) => {
    setChosen(slug);
    rememberPath(slug);
  };
  const onCredential = async (credential) => {
    setBusy(true);
    setErr("");
    try {
      await signInWithGoogle(credential, chosen);
      nav("/app", { replace: true });
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <Shell>
      <ol className="mx-auto mb-8 flex max-w-md items-center justify-center gap-3 text-sm font-bold" aria-label="Sign-up steps">
        {["Choose your path", "Create account"].map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span className={`grid h-7 w-7 place-items-center rounded-full ${step >= i + 1 ? "bg-navy text-white" : "bg-slate-200 text-slate-500"}`}>{i + 1}</span>
            <span className={step >= i + 1 ? "text-navy" : "text-slate-400"}>{label}</span>
            {i === 0 && <span className="mx-1 h-px w-8 bg-slate-300" />}
          </li>
        ))}
      </ol>

      {error ? <ErrorBox message={error} onRetry={reload} /> : !paths ? <Spinner /> : step === 1 ? (
        <>
          <div className="text-center">
            <h1 className="font-display text-3xl font-extrabold text-navy md:text-4xl">Which path is right for you?</h1>
            <p className="mt-2 text-slate-600">Choose one to start. You can talk to your trainer if you need to move later.</p>
          </div>
          <div className="mt-8 grid gap-6 md:grid-cols-3" role="group" aria-label="Learning paths">
            {paths.map((p) => (<PathCard key={p.slug} path={p} selected={chosen === p.slug} onSelect={pick} />))}
          </div>
          <div className="mt-8 text-center">
            <button className="btn-primary" disabled={!chosen} onClick={() => setStep(2)}>Continue <FiArrowRight /></button>
            <p className="mt-4 text-sm text-slate-500">Already registered? <Link to="/login" className="font-bold text-navy underline">Sign in</Link></p>
          </div>
        </>
      ) : (
        <div className="card mx-auto max-w-md p-8 text-center">
          <Logo dark />
          <h1 className="mt-6 font-display text-2xl font-extrabold text-navy">Create your account</h1>
          {path && (
            <div className="mt-4 flex items-center gap-3 rounded-xl bg-panel p-3 text-left">
              <PathIcon icon={path.icon} color={path.color} size="h-10 w-10" iconSize="h-5 w-5" />
              <div className="flex-1">
                <p className="text-xs font-bold uppercase text-slate-500">Your path</p>
                <p className="font-display font-bold text-navy">{path.level}: {path.title}</p>
              </div>
              <button className="text-sm font-bold text-navy underline" onClick={() => setStep(1)}>Change</button>
            </div>
          )}
          <div className="mt-6">{busy ? <Spinner label="Creating your account..." /> : <GoogleButton onCredential={onCredential} text="signup_with" />}</div>
          {err && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{err}</p>}
          <DevLogin pathSlug={chosen} onDone={() => nav("/app", { replace: true })} />
          <p className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-500"><FiShield aria-hidden="true" /> We only receive your name, email and photo from Google. We never see your password.</p>
          <button className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-navy" onClick={() => setStep(1)}><FiArrowLeft /> Back</button>
        </div>
      )}
    </Shell>
  );
}

export function Login() {
  const { user, signInWithGoogle } = useAuth();
  const nav = useNavigate();
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={user.path ? "/app" : "/choose-path"} replace />;
  const onCredential = async (credential) => {
    setBusy(true);
    setErr("");
    try {
      const r = await signInWithGoogle(credential);
      nav(r.user.path ? "/app" : "/choose-path", { replace: true });
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };
  return (
    <Shell>
      <div className="card mx-auto max-w-md p-8 text-center">
        <Logo dark />
        <h1 className="mt-6 font-display text-2xl font-extrabold text-navy">Welcome back</h1>
        <p className="mt-1 text-slate-600">Sign in to continue your lessons.</p>
        <div className="mt-6">{busy ? <Spinner label="Signing you in..." /> : <GoogleButton onCredential={onCredential} text="signin_with" />}</div>
        {err && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{err}</p>}
        <DevLogin onDone={() => nav("/app", { replace: true })} />
        <p className="mt-6 text-sm text-slate-500">New here? <Link to="/signup" className="font-bold text-navy underline">Create an account</Link></p>
      </div>
    </Shell>
  );
}

/** Safety net: a signed-in account without a path (for example after signing in before choosing one). */
export function ChoosePath() {
  const { user, loading, choosePath } = useAuth();
  const nav = useNavigate();
  const { paths, error, reload } = usePaths();
  const [chosen, setChosen] = useState(recallPath());
  const [err, setErr] = useState("");
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/signup" replace />;
  if (user.path) return <Navigate to="/app" replace />;
  const go = async () => {
    try {
      await choosePath(chosen);
      nav("/app", { replace: true });
    } catch (e) {
      setErr(e.message);
    }
  };
  return (
    <Shell>
      <div className="text-center">
        <h1 className="font-display text-3xl font-extrabold text-navy md:text-4xl">Hi {user.name.split(" ")[0]}, choose your path</h1>
        <p className="mt-2 text-slate-600">Pick the level that fits you today.</p>
      </div>
      {error ? <ErrorBox message={error} onRetry={reload} /> : !paths ? <Spinner /> : (
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {paths.map((p) => (<PathCard key={p.slug} path={p} selected={chosen === p.slug} onSelect={setChosen} />))}
        </div>
      )}
      {err && <p className="mt-4 text-center font-semibold text-red-700" role="alert">{err}</p>}
      <div className="mt-8 text-center"><button className="btn-primary" disabled={!chosen} onClick={go}>Start learning <FiArrowRight /></button></div>
    </Shell>
  );
}
