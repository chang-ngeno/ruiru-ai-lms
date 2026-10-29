import { useEffect } from "react";
import { site } from "../siteConfig";

export function usePageTitle(title) {
  useEffect(() => {
    if (typeof document === "undefined") return;
    document.title = title ? `${title} | ${site.name}` : `${site.name} | ${site.location}`;
  }, [title]);
}
