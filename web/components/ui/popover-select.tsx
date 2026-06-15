"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

interface PopoverSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  /** Extra classes on the trigger button (overrides height/width defaults). */
  className?: string;
  placeholder?: string;
  disabled?: boolean;
  "aria-label"?: string;
}

/**
 * A fully-custom styled dropdown — no native <select> open panel.
 * Uses a fixed-positioned portal panel so it's never clipped by table overflow.
 */
export function PopoverSelect({
  value,
  onChange,
  options,
  className,
  placeholder,
  disabled,
  "aria-label": ariaLabel,
}: PopoverSelectProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0, minWidth: 0 });
  const [openAbove, setOpenAbove] = useState(false);
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setMounted(true); }, []);

  function openPanel() {
    if (disabled || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const panelEst = Math.min(options.length * 38 + 8, 280);
    const spaceBelow = window.innerHeight - rect.bottom;
    const above = spaceBelow < panelEst && rect.top > panelEst;
    setOpenAbove(above);
    setPos({
      top: above ? rect.top - panelEst - 4 : rect.bottom + 4,
      left: rect.left,
      minWidth: rect.width,
    });
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;
    function onOutside(e: MouseEvent) {
      const t = e.target as Node;
      if (!triggerRef.current?.contains(t) && !panelRef.current?.contains(t)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onScroll() { setOpen(false); }
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  const current = options.find((o) => o.value === value);

  const panel = (
    <div
      ref={panelRef}
      role="listbox"
      aria-label={ariaLabel}
      style={{ position: "fixed", top: pos.top, left: pos.left, minWidth: pos.minWidth, zIndex: 9999 }}
      className={cn(
        "overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-xl ring-1 ring-ink/5",
        openAbove ? "origin-bottom animate-in fade-in-0 zoom-in-95" : "origin-top animate-in fade-in-0 zoom-in-95",
      )}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          role="option"
          type="button"
          aria-selected={opt.value === value}
          onClick={() => { onChange(opt.value); setOpen(false); }}
          className={cn(
            "flex w-full items-center px-3 py-2 text-sm transition-colors",
            opt.value === value
              ? "bg-brand/10 font-medium text-brand"
              : "text-ink hover:bg-bg",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : openPanel())}
        className={cn(
          "inline-flex h-10 w-full cursor-pointer items-center rounded-lg border border-line bg-surface pl-3 pr-9 text-sm text-ink shadow-sm transition-colors hover:border-ink/30 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 disabled:cursor-not-allowed disabled:opacity-50",
          !current && "text-muted",
          className,
        )}
      >
        <span className="truncate">{current?.label ?? placeholder ?? "Select…"}</span>
        <ChevronDown
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted transition-transform duration-150",
            open && "rotate-180",
          )}
        />
      </button>
      {mounted && open ? createPortal(panel, document.body) : null}
    </div>
  );
}
