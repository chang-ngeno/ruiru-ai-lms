import { useEffect, useRef, useState } from "react";
import { useAuth } from "../lib/auth";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

/** Renders the official "Sign in with Google" button (Google Identity Services). */
export default function GoogleButton({ onCredential, text = "continue_with" }) {
  const box = useRef(null);
  const cb = useRef(onCredential);
  cb.current = onCredential;
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (!CLIENT_ID) {
      setProblem("Google sign-in is not set up yet (missing VITE_GOOGLE_CLIENT_ID).");
      return;
    }
    const init = () => {
      if (!box.current || !window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (res) => cb.current(res.credential),
        ux_mode: "popup",
      });
      window.google.accounts.id.renderButton(box.current, {
        theme: "filled_blue",
        size: "large",
        shape: "pill",
        text,
        logo_alignment: "left",
        width: Math.min(360, box.current.offsetWidth || 320),
      });
    };
    if (window.google?.accounts?.id) {
      init();
      return;
    }
    let script = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (!script) {
      script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", init);
    script.addEventListener("error", () => setProblem("Could not load Google sign-in. Check your internet connection."));
    return () => script.removeEventListener("load", init);
  }, [text]);

  return (
    <div className="w-full">
      <div ref={box} className="flex min-h-[44px] w-full justify-center" />
      {problem && <p className="mt-2 text-center text-sm text-red-700" role="alert">{problem}</p>}
    </div>
  );
}

/** Development helper, only rendered when VITE_DEV_AUTH=true. */
export function DevLogin({ pathSlug, onDone }) {
  const { devLogin } = useAuth();
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  if (import.meta.env.VITE_DEV_AUTH !== "true") return null;
  const submit = async (e) => {
    e.preventDefault();
    try {
      await devLogin(email, email.split("@")[0], pathSlug);
      onDone();
    } catch (ex) {
      setErr(ex.message);
    }
  };
  return (
    <form onSubmit={submit} className="mt-6 rounded-xl border-2 border-dashed border-amber-400 bg-amber-50 p-4 text-left">
      <p className="text-xs font-bold uppercase tracking-wide text-amber-800">Development sign-in (no Google)</p>
      <div className="mt-2 flex gap-2">
        <input className="field !py-2" type="email" required placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
        <button className="btn-navy btn-sm">Go</button>
      </div>
      {err && <p className="mt-2 text-sm text-red-700">{err}</p>}
    </form>
  );
}
