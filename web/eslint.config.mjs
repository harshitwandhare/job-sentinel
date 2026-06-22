import coreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/** Next.js core-web-vitals rules + TypeScript awareness (flat config). */
const config = [
  ...coreWebVitals,
  ...nextTypescript,
  {
    settings: {
      react: { version: "19" },
    },
    rules: {
      "@next/next/no-img-element": "off",
      // react-hooks v5 added this rule but it fires on intentional patterns
      // (SSR hydration, mount-only effects). Re-enable if the rule gains an
      // escape hatch for legitimate synchronous state initialisation.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default config;
