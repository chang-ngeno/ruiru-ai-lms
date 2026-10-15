import { useCallback, useEffect, useState } from "react";

/** Tiny data-fetching hook: { data, error, loading, reload }. */
export function useFetch(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: "" }));
    fn()
      .then((data) => setState({ data, error: "", loading: false }))
      .catch((e) => setState({ data: null, error: e.message || "Something went wrong.", loading: false }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(load, [load]);
  return { ...state, reload: load, setData: (data) => setState((s) => ({ ...s, data })) };
}
