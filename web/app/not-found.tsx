import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-5 py-24 text-center">
      <p className="text-6xl font-bold text-stone-300">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-ink">Page not found</h1>
      <p className="mt-2 text-muted">That page doesn&apos;t exist.</p>
      <div className="mt-6 flex justify-center">
        <Link href="/">
          <Button>Back home</Button>
        </Link>
      </div>
    </div>
  );
}
