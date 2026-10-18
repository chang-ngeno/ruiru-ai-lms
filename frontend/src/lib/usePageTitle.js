import { useEffect } from "react";

export function usePageTitle(title) {
  useEffect(() => {
    if (typeof document === "undefined") return;
    document.title = title ? `${title} | AI Training for Everyone` : "AI Training for Everyone | Ruiru, Kenya";
  }, [title]);
}
