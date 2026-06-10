"use client";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-2xl px-5 py-20">
      <Card>
        <CardTitle>Something went wrong</CardTitle>
        <CardSub className="mt-2">
          {error.message || "An unexpected error occurred while rendering this page."}
        </CardSub>
        <div className="mt-4">
          <Button onClick={reset}>Try again</Button>
        </div>
      </Card>
    </div>
  );
}
