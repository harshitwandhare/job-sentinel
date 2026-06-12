import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

/** Next.js core-web-vitals rules + TypeScript awareness (flat config). */
const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
  {
    rules: {
      // The brand mark and terminal art are decorative; next/image adds no
      // value for an app that always runs on localhost.
      "@next/next/no-img-element": "off",
    },
  },
];

export default config;
