import { Component } from "react";

/** Catches a crash in any page so learners see a friendly message instead of a blank screen. */
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    // eslint-disable-next-line no-console
    console.error("Page crashed:", error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="grid min-h-screen place-items-center bg-panel p-6 text-center">
        <div className="card max-w-md p-8">
          <p className="font-script text-4xl text-navy-700">Oops!</p>
          <h1 className="mt-1 font-display text-2xl font-extrabold text-navy">Something went wrong</h1>
          <p className="mt-2 text-slate-600">Your progress is safe. Please reload the page. If it keeps happening, tell your trainer.</p>
          <button className="btn-primary mt-5" onClick={() => window.location.assign("/")}>Reload</button>
        </div>
      </div>
    );
  }
}
