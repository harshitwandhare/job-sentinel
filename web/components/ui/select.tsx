import { ChevronDown } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * A native <select> styled to match the app: appearance stripped, custom
 * chevron, consistent border/focus with Input. Keeps full native a11y +
 * keyboard behaviour while looking on-theme instead of OS-default.
 */
export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <div className="relative">
    <select
      ref={ref}
      className={cn(
        "h-10 w-full cursor-pointer appearance-none rounded-lg border border-line bg-surface pl-3 pr-9 text-sm text-ink shadow-sm transition-colors hover:border-ink/30 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30",
        className,
      )}
      {...props}
    >
      {children}
    </select>
    <ChevronDown
      aria-hidden="true"
      className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
    />
  </div>
));
Select.displayName = "Select";
