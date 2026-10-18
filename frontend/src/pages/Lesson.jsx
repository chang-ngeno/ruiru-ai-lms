import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  FiAlertTriangle, FiArrowLeft, FiArrowRight, FiAward, FiBookOpen, FiCheck, FiCheckCircle, FiCopy, FiEdit3,
  FiFlag, FiList, FiMessageCircle, FiSend, FiTarget, FiTerminal, FiX, FiZap,
} from "react-icons/fi";
import Paywall from "../components/Paywall";
import { ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePageTitle } from "../lib/usePageTitle";
import { useFetch } from "../lib/hooks";

function Section({ id, title, icon: I, color, children }) {
  return (
    <section id={id} className="card scroll-mt-24 p-5 md:p-7">
      <h2 className="flex items-center gap-3 font-display text-xl font-bold text-navy">
        <span className="grid h-9 w-9 place-items-center rounded-lg text-white" style={{ background: color }}><I className="h-5 w-5" aria-hidden="true" /></span>
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function CopyButton({ text }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      className="inline-flex items-center gap-1 rounded-full bg-navy px-3 py-1 text-xs font-bold text-white hover:bg-navy-700"
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1500); } catch { /* clipboard blocked */ }
      }}
    >
      {ok ? <FiCheck /> : <FiCopy />} {ok ? "Copied" : "Copy"}
    </button>
  );
}

function SelfCheck({ quiz, saved, onSave, color }) {
  const [shown, setShown] = useState({});
  const [marks, setMarks] = useState({});
  const [typed, setTyped] = useState({});
  const answered = Object.keys(marks).length;
  const score = Object.values(marks).filter(Boolean).length;
  const done = answered === quiz.length;

  useEffect(() => {
    if (done) onSave(score);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, score]);

  return (
    <div>
      <p className="text-sm text-slate-600">Try to answer in your own words first, then reveal the model answer and mark yourself honestly.</p>
      {saved?.total ? <p className="mt-2 text-sm font-bold text-navy">Last saved score: {saved.score}/{saved.total}</p> : null}
      <ol className="mt-4 space-y-4">
        {quiz.map((q, i) => (
          <li key={i} className="rounded-xl border border-slate-200 p-4">
            <p className="font-semibold text-navy">{i + 1}. {q.q}</p>
            <textarea className="field mt-3 !py-2 text-sm" rows={2} placeholder="Your answer (optional)" value={typed[i] || ""} onChange={(e) => setTyped({ ...typed, [i]: e.target.value })} aria-label={`Your answer to question ${i + 1}`} />
            {!shown[i] ? (
              <button className="btn-outline btn-sm mt-3" onClick={() => setShown({ ...shown, [i]: true })}>Show answer</button>
            ) : (
              <div className="mt-3 rounded-lg bg-green-50 p-3">
                <p className="text-sm font-semibold text-green-900">{q.a}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className={`btn btn-sm ${marks[i] === true ? "bg-path-beginner text-white" : "bg-white text-path-beginner ring-2 ring-path-beginner"}`} onClick={() => setMarks({ ...marks, [i]: true })}>I got it</button>
                  <button className={`btn btn-sm ${marks[i] === false ? "bg-red-600 text-white" : "bg-white text-red-600 ring-2 ring-red-600"}`} onClick={() => setMarks({ ...marks, [i]: false })}>Not yet</button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
      {done && (
        <p className="mt-4 rounded-xl p-4 text-center font-display text-lg font-bold text-white" style={{ background: color }}>
          You scored {score} out of {quiz.length}. {score === quiz.length ? "Perfect!" : score >= quiz.length * 0.8 ? "Great work!" : "Review the key points and try again tomorrow."}
        </p>
      )}
    </div>
  );
}

function Notes({ number, initial }) {
  const [text, setText] = useState(initial || "");
  const [status, setStatus] = useState("");
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    setStatus("Saving...");
    const t = setTimeout(() => {
      api.put(`/lessons/${number}/progress`, { notes: text }).then(() => setStatus("Saved")).catch(() => setStatus("Could not save"));
    }, 800);
    return () => clearTimeout(t);
  }, [text, number]);
  return (
    <div>
      <textarea className="field" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Write what you learned, questions to ask your trainer, ideas to try..." aria-label="My notes" />
      <p className="mt-1 text-right text-xs font-semibold text-slate-500" aria-live="polite">{status}</p>
    </div>
  );
}

function Coach({ number, color }) {
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => { if (open && enabled === null) api.get("/coach/status").then((r) => setEnabled(r.enabled)).catch(() => setEnabled(false)); }, [open, enabled]);
  useEffect(() => { end.current?.scrollIntoView?.({ behavior: "smooth" }); }, [msgs, open]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    const history = msgs.map((m) => ({ role: m.role, content: m.content }));
    setMsgs((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.post("/coach", { lesson_number: number, message: text, history });
      setMsgs((m) => [...m, { role: "assistant", content: r.reply }]);
    } catch (ex) {
      setMsgs((m) => [...m, { role: "assistant", content: ex.message, error: true }]);
    } finally { setBusy(false); }
  };

  return (
    <>
      <button onClick={() => setOpen(true)} className="no-print fixed bottom-24 right-4 z-30 flex items-center gap-2 rounded-full bg-brand px-5 py-3 font-display font-bold text-navy shadow-glow md:bottom-6" aria-label="Open AI Coach">
        <FiMessageCircle /> AI Coach
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/40 p-0 md:p-6" role="dialog" aria-modal="true" aria-label="AI Coach">
          <div className="flex h-[85vh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl md:h-[600px] md:max-w-md md:rounded-3xl">
            <div className="flex items-center justify-between bg-navy p-4 text-white">
              <div><p className="font-display font-bold">Your AI Coach</p><p className="text-xs text-white/70">Turns today&rsquo;s lesson into one action</p></div>
              <button onClick={() => setOpen(false)} aria-label="Close coach" className="rounded-full p-2 hover:bg-white/10"><FiX /></button>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto bg-panel p-4">
              {enabled === false && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">The AI Coach is not switched on yet. Ask your trainer, and use the lesson&rsquo;s homework as your action for today.</p>}
              {enabled && msgs.length === 0 && (
                <div className="space-y-2">
                  <p className="rounded-xl bg-white p-3 text-sm shadow-sm">Hi! Tell me what you want to do with AI, or ask about today&rsquo;s lesson. I will give you one specific action.</p>
                  {["Give me one action to try today", "Explain the main idea simply", "Help me practise with an example"].map((q) => (
                    <button key={q} onClick={() => setInput(q)} className="mr-2 rounded-full border border-navy px-3 py-1 text-xs font-bold text-navy hover:bg-navy hover:text-white">{q}</button>
                  ))}
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={`max-w-[90%] whitespace-pre-wrap rounded-2xl p-3 text-sm shadow-sm ${m.role === "user" ? "ml-auto bg-navy text-white" : m.error ? "bg-red-50 text-red-800" : "bg-white"}`}>{m.content}</div>
              ))}
              {busy && <div className="w-16 rounded-2xl bg-white p-3 text-center text-sm shadow-sm" aria-label="Coach is typing">...</div>}
              <div ref={end} />
            </div>
            <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3">
              <input className="field !py-2" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask your coach..." maxLength={1000} disabled={enabled === false} aria-label="Message" />
              <button className="btn-navy btn-sm" disabled={busy || !input.trim() || enabled === false} aria-label="Send"><FiSend /></button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

export default function Lesson() {
  const { number } = useParams();
  const n = Number(number);
  const nav = useNavigate();
  const { user } = useAuth();
  const { data, error, status, errorData, loading, reload } = useFetch(() => api.get(`/lessons/${n}`), [n]);
  usePageTitle(data ? `Day ${data.lesson.number}: ${data.lesson.title}` : "Lesson");
  const [completed, setCompleted] = useState(false);
  const [steps, setSteps] = useState([]);
  const [quizSaved, setQuizSaved] = useState(null);
  const [finishedAll, setFinishedAll] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!data) return;
    setCompleted(data.progress.completed);
    setSteps(data.progress.steps_done);
    setQuizSaved(data.progress.quiz_total ? { score: data.progress.quiz_score, total: data.progress.quiz_total } : null);
    setFinishedAll(false);
    window.scrollTo?.({ top: 0 });
  }, [data]);

  const color = user.path.color;
  const toc = useMemo(() => [["objectives", "Objectives"], ["learn", "Learn"], ["template", "Template"], ["lab", "Lab"], ["practice", "Practice"], ["selfcheck", "Self-check"], ["recap", "Recap"], ["action", "Homework"], ["notes", "Notes"]], []);

  if (loading) return <Spinner />;
  if (status === 402) return <Paywall info={errorData} title={`Lesson ${n} is locked`} />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const { lesson } = data;
  const c = lesson.content;
  const hasCode = Boolean(c.code);

  const toggleStep = (i) => {
    const next = steps.includes(i) ? steps.filter((x) => x !== i) : [...steps, i];
    setSteps(next);
    api.put(`/lessons/${n}/progress`, { steps_done: next }).catch(() => setSteps(steps));
  };
  const toggleComplete = async () => {
    setBusy(true);
    try {
      const r = completed ? await api.del(`/lessons/${n}/complete`) : await api.post(`/lessons/${n}/complete`);
      setCompleted(!completed);
      setFinishedAll(r.summary.finished);
    } finally { setBusy(false); }
  };
  const saveQuiz = (score) => api.post(`/lessons/${n}/quiz`, { score }).then((r) => setQuizSaved({ score: r.quiz_score, total: r.quiz_total })).catch(() => {});

  return (
    <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
      <aside className="no-print hidden lg:block">
        <nav className="sticky top-24 space-y-1 text-sm" aria-label="On this page">
          <Link to="/app/curriculum" className="mb-3 flex items-center gap-1 font-bold text-navy"><FiArrowLeft /> All lessons</Link>
          {toc.filter(([id]) => id !== "template" || hasCode).map(([id, label]) => (
            <a key={id} href={`#${id}`} className="block rounded-lg px-3 py-2 font-semibold text-slate-600 hover:bg-white hover:text-navy">{label}</a>
          ))}
        </nav>
      </aside>

      <div className="min-w-0 space-y-6">
        <header className="rounded-3xl p-6 text-white shadow-lg md:p-8" style={{ background: `linear-gradient(135deg, #071A47, ${color})` }}>
          <p className="text-sm font-bold uppercase tracking-wide text-white/80">Week {lesson.week}: {lesson.week_title}</p>
          <h1 className="mt-1 font-display text-2xl font-extrabold md:text-4xl">Day {lesson.number}: {lesson.title}</h1>
          <p className="mt-2 text-sm text-white/80">Lesson {lesson.number} of {lesson.total} &middot; about 3 hours in class</p>
          {completed && <span className="chip mt-3 bg-brand text-navy"><FiCheckCircle /> Completed</span>}
        </header>

        <Section id="objectives" title="Today's objectives" icon={FiTarget} color={color}>
          <ul className="space-y-2">{c.objectives.map((o) => <li key={o} className="flex gap-3"><FiCheckCircle className="mt-1 h-5 w-5 shrink-0" style={{ color }} aria-hidden="true" /><span>{o}</span></li>)}</ul>
          <p className="mt-4 leading-relaxed text-slate-700">{c.intro}</p>
        </Section>

        <Section id="learn" title="Learn" icon={FiBookOpen} color={color}>
          <div className="space-y-5">
            {c.concepts.map((k, i) => (
              <article key={k.heading} className="rounded-xl border border-slate-200 p-4 md:p-5">
                <h3 className="font-display text-lg font-bold text-navy"><span className="mr-2 text-brand-600">{i + 1}.</span>{k.heading}</h3>
                <p className="mt-2 leading-relaxed text-slate-700">{k.text}</p>
                <ul className="mt-3 rounded-lg bg-panel p-3 text-sm">
                  {k.points.map((p) => <li key={p} className="flex gap-2 py-0.5"><FiCheck className="mt-0.5 h-4 w-4 shrink-0 text-navy-700" aria-hidden="true" /><span className="font-semibold text-navy">{p}</span></li>)}
                </ul>
              </article>
            ))}
          </div>
        </Section>

        {hasCode && (
          <Section id="template" title={user.path.slug === "advanced" ? "Code walkthrough" : "Worked template"} icon={FiTerminal} color={color}>
            <div className="mb-2 flex justify-end"><CopyButton text={c.code} /></div>
            <pre className="overflow-x-auto rounded-xl bg-navy-950 p-4 font-mono text-[13px] leading-relaxed text-slate-100"><code>{c.code}</code></pre>
          </Section>
        )}

        <Section id="lab" title="Hands-on lab" icon={FiList} color={color}>
          <p className="rounded-lg bg-brand/20 p-3 font-semibold text-navy">Goal: {c.lab}</p>
          <ol className="mt-4 space-y-2">
            {c.steps.map((s, i) => (
              <li key={i}>
                <label className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${steps.includes(i) ? "border-green-300 bg-green-50" : "border-slate-200 hover:bg-panel"}`}>
                  <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-green-700" checked={steps.includes(i)} onChange={() => toggleStep(i)} />
                  <span className={steps.includes(i) ? "text-slate-500 line-through" : ""}><b className="mr-1">Step {i + 1}.</b>{s}</span>
                </label>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-sm font-semibold text-slate-500">{steps.length} of {c.steps.length} steps done</p>
        </Section>

        <Section id="practice" title="Practice and common mistakes" icon={FiZap} color={color}>
          <div className="space-y-3">
            {c.examples.map((ex) => (
              <div key={ex.label} className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between gap-2"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{ex.label}</p><CopyButton text={ex.text} /></div>
                <p className="mt-2 text-slate-800">{ex.text}</p>
              </div>
            ))}
          </div>
          <h3 className="mt-6 flex items-center gap-2 font-display font-bold text-navy"><FiAlertTriangle className="text-amber-600" aria-hidden="true" /> Mistakes to avoid</h3>
          <ul className="mt-2 list-disc space-y-1 pl-6 text-slate-700">{c.mistakes.map((m) => <li key={m}>{m}</li>)}</ul>
        </Section>

        <Section id="selfcheck" title="Self-check" icon={FiEdit3} color={color}>
          <SelfCheck key={n} quiz={c.quiz} saved={quizSaved} onSave={saveQuiz} color={color} />
        </Section>

        <Section id="recap" title="Key takeaways and words to know" icon={FiFlag} color={color}>
          <ul className="space-y-2">{c.takeaways.map((t) => <li key={t} className="flex gap-3 font-semibold text-navy"><FiCheckCircle className="mt-1 h-5 w-5 shrink-0" style={{ color }} aria-hidden="true" />{t}</li>)}</ul>
          <dl className="mt-5 grid gap-3 sm:grid-cols-2">
            {c.glossary.map((g) => <div key={g.term} className="rounded-xl bg-panel p-3"><dt className="font-display font-bold text-navy">{g.term}</dt><dd className="text-sm text-slate-700">{g.meaning}</dd></div>)}
          </dl>
        </Section>

        <section id="action" className="scroll-mt-24 rounded-2xl bg-brand p-5 text-navy shadow-glow md:p-7">
          <p className="text-xs font-extrabold uppercase tracking-wide">Today&rsquo;s action &middot; homework</p>
          <p className="mt-1 font-display text-xl font-bold">{c.homework}</p>
        </section>

        <Section id="notes" title="My notes" icon={FiEdit3} color={color}>
          <Notes key={n} number={n} initial={data.progress.notes} />
        </Section>

        <div className="card flex flex-col items-stretch gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-2">
            {n > 1 && <Link to={`/app/learn/${n - 1}`} className="btn-outline btn-sm"><FiArrowLeft /> Previous</Link>}
            {n < lesson.total && <Link to={`/app/learn/${n + 1}`} className="btn-outline btn-sm">Next <FiArrowRight /></Link>}
          </div>
          <button onClick={toggleComplete} disabled={busy} className={completed ? "btn-outline" : "btn-primary"}>
            {completed ? <>Mark as not done</> : <><FiCheckCircle /> Mark lesson complete</>}
          </button>
        </div>
        {completed && (
          <div className="card border-l-8 p-5" style={{ borderLeftColor: color }}>
            {finishedAll ? (
              <p className="flex flex-wrap items-center gap-3 font-display text-lg font-bold text-navy"><FiAward /> You finished the whole course! <Link to="/app/certificate" className="btn-primary btn-sm">Get your certificate</Link></p>
            ) : n < lesson.total ? (
              <p className="flex flex-wrap items-center gap-3 font-semibold text-navy">Nice work! <button className="btn-navy btn-sm" onClick={() => nav(`/app/learn/${n + 1}`)}>Start lesson {n + 1} <FiArrowRight /></button></p>
            ) : (
              <p className="font-semibold text-navy">Nice work! Check your dashboard for any lessons still to finish.</p>
            )}
          </div>
        )}
      </div>
      <Coach key={n} number={n} color={color} />
    </div>
  );
}
