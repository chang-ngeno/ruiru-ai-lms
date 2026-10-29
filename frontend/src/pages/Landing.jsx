import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FaFire, FaWhatsapp } from "react-icons/fa";
import { FiArrowRight, FiCheckCircle, FiClock, FiMapPin, FiPhone, FiWifi } from "react-icons/fi";
import { Footer, PublicNav } from "../components/Layout";
import { Icon, PathCard, ProgressRing } from "../components/ui";
import { api } from "../lib/api";
import { audiences, learnItems, perks, site, steps } from "../siteConfig";

// Static copy of the three paths (from the poster) so the landing page works even before the API is up.
const PATHS = [
  { slug: "beginner", level: "Beginner", icon: "bulb", color: "#1B8A3A", price_kes: 8000, title: "AI Foundations & Everyday Productivity", blurb: "AI basics, tools, and everyday productivity.", outcomes: ["Write clear prompts with the R-T-C-F recipe", "Use AI for writing, research, study and spreadsheets", "Spot scams and protect your private data"] },
  { slug: "intermediate", level: "Intermediate", icon: "gear", color: "#2F6FDE", price_kes: 15000, title: "AI Projects, Content & Automation", blurb: "Practical projects, content creation, automation and business use.", outcomes: ["Run a content engine for a brand", "Build no-code automations with AI steps", "Package and price AI services for clients"] },
  { slug: "advanced", level: "Advanced", icon: "code", color: "#7B3FC4", price_kes: 25000, title: "Building Custom AI Solutions", blurb: "Custom AI solutions, automation, APIs, and real-world applications.", outcomes: ["Call model APIs from Python with validation", "Build document Q&A (RAG) and agents with tools", "Deploy, secure and monitor a real application"] },
];

const FAQ = [
  ["Do I need any experience?", "No. The Beginner path starts from zero. If you can use a phone, you can start. The Intermediate path suits people who already use AI tools each week, and the Advanced path needs basic Python."],
  ["Which path should I choose?", "Pick Beginner if AI is new to you, Intermediate if you want projects, content, automation or client work, and Advanced if you can code and want to build and deploy AI applications. Your trainer can help you decide."],
  ["How do payments work?", "You pay by M-Pesa in the app, in any amounts you like. Day 1 is a free preview, and every quarter of the price you pay opens another week of lessons. Discount codes are applied before you pay."],
  ["What is the workspace pass?", "All learners get unlimited access to the training space. Your digital pass switches on with your first payment and shows as a QR code in the app, which the front desk scans."],
  ["Can I get a refund?", "You can request one in the app. If you have not started any paid lesson you can ask for a full refund; if you have started, a partial refund may be possible within the first few days. A trainer reviews every request, and a refund closes the weeks and workspace access it was paying for."],
  ["Will I get a certificate?", "Yes. Finish all 20 lessons in your path and you can print your certificate from the app."],
];

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-navy-950 via-navy to-navy-700 text-white">
      <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-14 md:grid-cols-2 md:py-24">
        <div>
          <p className="font-script text-3xl text-brand md:text-4xl">Practical AI, step by step</p>
          <h1 className="mt-3 font-display text-4xl font-extrabold uppercase leading-[1.05] sm:text-5xl lg:text-6xl">
            Online AI <br />
            <span className="brush">Classes</span>
          </h1>
          <p className="mt-4 inline-block rounded-lg bg-white/10 px-4 py-2 font-display text-lg font-bold">
            From <span className="text-brand">Beginners</span> to <span className="text-brand">Advanced</span>
          </p>
          <p className="mt-5 max-w-xl text-lg text-white/85">
            Follow a guided learning path, practise useful AI skills and build real projects from wherever you are.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary text-lg">Choose your path <FiArrowRight /></Link>
            <Link to="/login" className="btn-ghost text-lg">Sign in</Link>
          </div>
          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-brand p-4 text-navy shadow-glow">
              <FiClock className="h-6 w-6" aria-hidden="true" />
              <p className="mt-1 font-display text-xl font-extrabold leading-tight">1 MONTH</p>
              <p className="text-sm font-bold uppercase">Training sessions</p>
            </div>
            <div className="rounded-xl bg-navy-900 p-4 ring-2 ring-brand/70">
              <FiWifi className="h-6 w-6 text-brand" aria-hidden="true" />
              <p className="mt-1 font-display text-lg font-extrabold leading-tight">UNLIMITED ACCESS</p>
              <p className="text-sm text-white/80">to workspace &amp; facility, all day, every day</p>
            </div>
          </div>
        </div>

        {/* dashboard preview, in the spirit of a real LMS */}
        <div className="relative mx-auto w-full max-w-md" aria-hidden="true">
          <div className="rounded-3xl bg-white p-5 text-slate-800 shadow-2xl ring-1 ring-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase text-slate-400">Welcome back</p>
                <p className="font-display text-xl font-extrabold text-navy">Wanjiru</p>
              </div>
              <span className="chip text-white" style={{ background: "#2F6FDE" }}>Intermediate</span>
            </div>
            <div className="mt-4 flex items-center gap-5 rounded-2xl bg-navy p-4 text-white">
              <ProgressRing percent={65} size={92} stroke={10}>
                <span className="font-display text-xl font-extrabold">65%</span>
              </ProgressRing>
              <div>
                <p className="flex items-center gap-1 font-display text-lg font-bold"><FaFire className="text-orange-400" /> 9 day streak</p>
                <p className="text-sm text-white/70">13 of 20 lessons done</p>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {[["Week 1", 100], ["Week 2", 100], ["Week 3", 60], ["Week 4", 0]].map(([w, p]) => (
                <div key={w}>
                  <div className="flex justify-between text-xs font-bold text-slate-500"><span>{w}</span><span>{p}%</span></div>
                  <div className="h-2 rounded-full bg-slate-200"><div className="h-2 rounded-full bg-path-intermediate" style={{ width: `${p}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl bg-brand/20 p-3 text-sm">
              <p className="text-xs font-bold uppercase text-navy-700">Today&rsquo;s action</p>
              <p className="font-semibold text-navy">Send your price list to 5 local businesses.</p>
            </div>
          </div>
          <div className="absolute -bottom-5 -left-4 hidden rotate-[-4deg] rounded-xl bg-brand px-4 py-2 font-script text-2xl text-navy shadow-glow sm:block">Everyone can learn AI!</div>
        </div>
      </div>
    </section>
  );
}

export function OnlineClasses() {
  const [paths, setPaths] = useState(PATHS);
  useEffect(() => {
    // Show the live prices the admin has set; the static ones above are only a fallback.
    api.get("/paths").then((d) => setPaths(PATHS.map((p) => ({ ...p, price_kes: d.paths.find((x) => x.slug === p.slug)?.price_kes ?? p.price_kes })))).catch(() => {});
  }, []);
  return (
    <div className="bg-panel">
      <PublicNav />
      <main id="main">
      <Hero />

      <section className="bg-white py-6">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-4 px-4 text-center md:grid-cols-4">
          {[["3", "learning paths"], ["60", "hands-on lessons"], ["1 month", "of training"], ["All ages", "welcome"]].map(([a, b]) => (
            <div key={b}><p className="font-display text-3xl font-extrabold text-navy">{a}</p><p className="text-sm font-semibold text-slate-500">{b}</p></div>
          ))}
        </div>
      </section>

      <section id="paths" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-16">
        <div className="text-center">
          <h2 className="font-display text-3xl font-extrabold uppercase text-navy md:text-4xl"><span className="brush">Course path</span></h2>
          <p className="mt-4 text-lg text-slate-600">Build skills step by step, at your own pace.</p>
        </div>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          <article className="card flex flex-col p-6">
            <span className="chip w-fit bg-brand text-navy">Early booking open</span>
            <h3 className="mt-4 font-display text-xl font-bold text-navy">AI Essentials</h3>
            <p className="mt-1 text-slate-600">A beginner-friendly introduction to AI tools and how to use them thoughtfully.</p>
            <div className="mt-auto pt-5">
              <p className="font-display text-2xl font-extrabold text-navy">KES 1,000</p>
              <a
                className="btn-primary btn-sm mt-4 w-fit"
                href={`https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.introClassMessage)}`}
                target="_blank"
                rel="noreferrer"
              >
                Book early <FaWhatsapp />
              </a>
            </div>
          </article>
          {paths.map((p) => (<PathCard key={p.slug} path={p} footer={null} />))}
          <article className="card flex flex-col p-6">
            <span className="chip w-fit bg-navy text-white">For leaders and teams</span>
            <h3 className="mt-4 font-display text-xl font-bold text-navy">Executive AI Training</h3>
            <p className="mt-1 text-slate-600">Focused AI training for executives and organisations, shaped around your team’s priorities.</p>
            <div className="mt-auto pt-5">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-500">Price by enquiry</p>
              <a
                className="btn-navy btn-sm mt-4 w-fit"
                href={`https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.executiveTrainingMessage)}`}
                target="_blank"
                rel="noreferrer"
              >
                Enquire <FaWhatsapp />
              </a>
            </div>
          </article>
        </div>
        <p className="mx-auto mt-8 max-w-2xl text-center text-slate-600">Pay by <b>M-Pesa</b> in instalments: every quarter of the price opens another week of lessons, and Day 1 is a free preview. Discount codes are available for early bookings, groups and students.</p>
        <p className="mt-4 text-center font-script text-3xl text-navy-700">From curiosity to confidence!</p>
        <div className="mt-4 text-center"><Link to="/signup" className="btn-navy">Pick your path <FiArrowRight /></Link></div>
      </section>

      <section id="learn" className="scroll-mt-20 bg-navy py-16 text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 md:grid-cols-5">
          <div className="md:col-span-2">
            <h2 className="font-display text-3xl font-extrabold uppercase md:text-4xl"><span className="brush">What you&rsquo;ll learn</span></h2>
            <p className="mt-5 text-lg text-white/80">Every lesson follows the same proven loop: understand it, try it, check it, apply it. You leave with real work in your portfolio.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 md:col-span-3">
            {learnItems.map((it) => (
              <div key={it.label} className="flex items-center gap-4 rounded-xl bg-white/10 p-4 ring-1 ring-white/10">
                <span className="grid h-11 w-11 place-items-center rounded-lg bg-brand/15 text-brand"><Icon name={it.icon} className="h-6 w-6" /></span>
                <span className="font-semibold">{it.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-16">
        <h2 className="text-center font-display text-3xl font-extrabold uppercase text-navy md:text-4xl"><span className="brush">How it works</span></h2>
        <div className="mt-10 grid gap-5 md:grid-cols-4">
          {steps.map((s) => (
            <div key={s.n} className="card p-6">
              <span className="font-display text-4xl font-extrabold text-brand-600">{s.n}</span>
              <h3 className="mt-2 font-display text-lg font-bold text-navy">{s.title}</h3>
              <p className="mt-1 text-slate-600">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white py-16">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 md:grid-cols-2">
          <div>
            <h2 className="font-display text-3xl font-extrabold uppercase text-navy md:text-4xl"><span className="brush">All ages welcome</span></h2>
            <p className="mt-5 text-lg text-slate-600">No experience needed. If you can use a phone, you can start. <span className="font-script text-2xl text-navy-700">Everyone can learn AI!</span></p>
          </div>
          <ul className="grid grid-cols-2 gap-3">
            {audiences.map((a) => (
              <li key={a} className="flex items-center gap-3 rounded-xl bg-panel p-4 font-bold text-navy"><FiCheckCircle className="h-5 w-5 text-path-beginner" aria-hidden="true" /> {a}</li>
            ))}
          </ul>
        </div>
      </section>

      <section id="workspace" className="scroll-mt-20 bg-gradient-to-br from-navy-900 to-navy py-16 text-white">
        <div className="mx-auto max-w-7xl px-4">
          <div className="max-w-2xl">
            <h2 className="font-display text-3xl font-extrabold uppercase md:text-4xl">Unlimited access to <span className="brush">workspace &amp; facility</span></h2>
            <p className="mt-5 text-lg text-white/80">All learners get unlimited access to our training space and workspace during the training month. Study, work on your projects, collaborate and grow, at your convenience.</p>
            <p className="mt-3 text-white/70">Your digital workspace pass switches on with your first M-Pesa payment and shows as a QR code in the app.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {perks.map((p) => (
              <div key={p.title} className="rounded-2xl bg-white p-5 text-slate-800">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-navy text-brand"><Icon name={p.icon} className="h-6 w-6" /></span>
                <h3 className="mt-3 font-display font-bold text-navy">{p.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{p.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 pt-4 pb-10">
        <h2 className="text-center font-display text-3xl font-extrabold uppercase text-navy md:text-4xl"><span className="brush">Questions</span></h2>
        <div className="mt-8 space-y-3">
          {FAQ.map(([q, a]) => (
            <details key={q} className="card group p-5">
              <summary className="cursor-pointer list-none font-display font-bold text-navy marker:content-none">{q}</summary>
              <p className="mt-3 text-slate-600">{a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16">
        <div className="overflow-hidden rounded-3xl bg-navy p-8 text-white shadow-xl md:p-12">
          <p className="font-script text-3xl text-brand">Your AI Journey Starts Here!</p>
          <h2 className="mt-2 font-display text-3xl font-extrabold uppercase md:text-4xl">Book your spot today</h2>
          <p className="mt-3 text-lg text-white/80">Learn | Build | Grow</p>
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <Link to="/signup" className="btn-primary">Create your account <FiArrowRight /></Link>
            <a className="btn-ghost" href={`https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.whatsappMessage)}`} target="_blank" rel="noreferrer"><FaWhatsapp /> WhatsApp us</a>
          </div>
          <div className="mt-6 flex flex-wrap gap-6 text-sm text-white/80">
            {site.phoneNumbers.map((phone) => (
              <a key={phone} href={`tel:${phone.replace(/\s/g, "")}`} className="flex items-center gap-2 hover:text-brand"><FiPhone /> {phone}</a>
            ))}
            <span className="flex items-center gap-2"><FiMapPin /> {site.location}</span>
          </div>
        </div>
      </section>
      </main>
      <Footer />
    </div>
  );
}

function ClassVideo() {
  if (site.introVideoUrl) {
    return (
      <video
        className="aspect-video w-full rounded-2xl bg-navy object-cover"
        controls
        playsInline
        preload="metadata"
        poster="/sequa-launchpad-main.jpeg"
      >
        <source src={site.introVideoUrl} type="video/mp4" />
        Your browser does not support embedded videos.
      </video>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-2xl bg-navy">
      <img
        src="/sequa-launchpad-main.jpeg"
        alt="Sequa Launchpad AI Masterclasses"
        className="aspect-video w-full object-cover opacity-70"
      />
      <div className="absolute inset-0 grid place-items-center bg-navy/25 p-6 text-center text-white">
        <div>
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-brand text-navy" aria-hidden="true">
            <span className="ml-1 text-2xl">▶</span>
          </span>
          <p className="mt-3 font-display text-lg font-bold">AI Introduction Class</p>
          <p className="mt-1 text-sm text-white/85">Class video coming soon</p>
        </div>
      </div>
    </div>
  );
}

export default function Landing() {
  const introBookingUrl = `https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.introClassMessage)}`;
  const executiveEnquiryUrl = `https://wa.me/${site.whatsapp}?text=${encodeURIComponent(site.executiveTrainingMessage)}`;

  return (
    <div className="bg-panel">
      <PublicNav />
      <main id="main">
        <section className="overflow-hidden bg-gradient-to-br from-navy-950 via-navy to-navy-700 text-white">
          <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-12 md:grid-cols-2 md:py-20">
            <div>
              <p className="font-display text-sm font-bold uppercase tracking-[0.2em] text-brand">Sequa Launchpad presents</p>
              <h1 className="mt-4 font-display text-4xl font-extrabold leading-tight sm:text-5xl lg:text-6xl">
                AI skills, <span className="text-brand">step by step.</span>
              </h1>
              <p className="mt-5 max-w-xl text-lg text-white/85">
                Start with a simple introduction to AI, then choose the masterclass that fits your goals.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href="#masterclasses" className="btn-primary text-lg">Explore masterclasses <FiArrowRight /></a>
                <Link to="/online-classes" className="btn-ghost text-lg">Online classes</Link>
              </div>
            </div>
            <img
              src="/sequa-launchpad-main.jpeg"
              alt="Sequa Launchpad AI Masterclasses — Spark, Build, Forge"
              className="mx-auto w-full max-w-2xl rounded-3xl shadow-2xl ring-1 ring-white/15"
            />
          </div>
        </section>

        <section id="masterclasses" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-14 md:py-20">
          <div className="mx-auto max-w-2xl text-center">
            <p className="font-display text-sm font-bold uppercase tracking-[0.2em] text-brand-700">Choose your starting point</p>
            <h2 className="mt-2 font-display text-3xl font-extrabold text-navy md:text-4xl">AI masterclasses</h2>
            <p className="mt-3 text-slate-600">Practical learning for individuals and teams, from a first introduction to executive-level training.</p>
          </div>

          <div className="mt-10 grid items-stretch gap-6 lg:grid-cols-2">
            <article className="card flex flex-col p-5 sm:p-7">
              <ClassVideo />
              <div className="mt-6 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="chip bg-brand text-navy">Early booking open</span>
                  <h3 className="mt-3 font-display text-2xl font-extrabold text-navy">AI Essentials</h3>
                </div>
                <p className="font-display text-2xl font-extrabold text-navy">KES 1,000</p>
              </div>
              <p className="mt-3 text-slate-600">
                A simple, beginner-friendly introduction to what AI is, how to try useful tools, and how to use them thoughtfully.
              </p>
              <a className="btn-primary mt-6 w-fit" href={introBookingUrl} target="_blank" rel="noreferrer">
                Book early <FaWhatsapp />
              </a>
            </article>

            <article className="card flex flex-col justify-between p-6 sm:p-8">
              <div>
                <span className="chip bg-navy text-white">For leaders and teams</span>
                <h3 className="mt-4 font-display text-2xl font-extrabold text-navy">Executive AI Training</h3>
                <p className="mt-3 text-slate-600">
                  Focused AI training for executives and organisations, shaped around your team’s priorities and work.
                </p>
              </div>
              <div className="mt-10 border-t border-slate-200 pt-5">
                <p className="text-sm font-bold uppercase tracking-wide text-slate-500">Pricing</p>
                <p className="mt-1 font-display text-2xl font-extrabold text-navy">By enquiry</p>
                <a className="btn-navy mt-5 w-fit" href={executiveEnquiryUrl} target="_blank" rel="noreferrer">
                  Enquire about executive training <FaWhatsapp />
                </a>
              </div>
            </article>
          </div>
        </section>

        <section className="bg-white py-10">
          <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 text-center sm:flex-row sm:text-left">
            <div>
              <h2 className="font-display text-xl font-extrabold text-navy">Ready to explore the full programme?</h2>
              <p className="mt-1 text-slate-600">Explore AI Essentials, three guided learning paths, and executive training.</p>
            </div>
            <Link to="/online-classes" className="btn-navy shrink-0">Online classes <FiArrowRight /></Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
