import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

const PATH_KEY = "rl_chosen_path";
export const rememberPath = (slug) => sessionStorage.setItem(PATH_KEY, slug);
export const recallPath = () => sessionStorage.getItem(PATH_KEY);
export const forgetPath = () => sessionStorage.removeItem(PATH_KEY);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { user } = await api.get("/me");
      setUser(user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({
      user,
      loading,
      refresh,
      async signInWithGoogle(credential, pathSlug) {
        const r = await api.post("/auth/google", { credential, path_slug: pathSlug || recallPath() });
        setUser(r.user);
        forgetPath();
        return r;
      },
      async devLogin(email, name, pathSlug) {
        const r = await api.post("/auth/dev-login", { email, name, path_slug: pathSlug || recallPath() });
        setUser(r.user);
        forgetPath();
        return r;
      },
      async choosePath(slug) {
        const r = await api.post("/me/path", { path_slug: slug });
        setUser(r.user);
        forgetPath();
        return r;
      },
      async logout() {
        await api.post("/auth/logout");
        setUser(null);
      },
    }),
    [user, loading, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
