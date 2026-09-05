/**
 * SidebarLogo — theme-aware sidebar logo.
 *
 * Matches logo.png visually in light mode and adapts text colours for dark mode.
 * The PNG asset is untouched; only the sidebar rendering is HTML-based so
 * individual text segments can carry proper theme-aware colours.
 *
 * Light mode  →  "Razorpay" dark navy · "AI" brand red · "Financial Copilot" slate-400
 * Dark mode   →  "Razorpay" white     · "AI" rose-500  · "Financial Copilot" slate-400
 */
export function SidebarLogo({ className }: { className?: string }) {
  return (
    <div
      className={`flex items-center gap-2.5 select-none ${className ?? ""}`}
      aria-label="Razorpay AI Financial Copilot"
      data-testid="sidebar-logo"
    >
      {/* ── Favicon icon ── */}
      <img
        src="/favicon.svg"
        alt=""
        aria-hidden="true"
        className="h-9 w-9 flex-shrink-0 object-contain"
      />

      {/* ── Text block ── */}
      <div className="flex flex-col leading-none">
        {/* Row 1 : "Razorpay" + "AI" */}
        <div className="flex items-baseline gap-[3px]">
          <span
            className="font-heading text-[16px] font-bold tracking-tight
                       text-slate-900 dark:text-white"
          >
            Razorpay
          </span>
          <span
            className="font-heading text-[16px] font-bold tracking-tight
                       text-rose-600 dark:text-rose-500"
          >
            AI
          </span>
        </div>

        {/* Row 2 : "Financial Copilot" */}
        <span
          className="mt-[3px] text-[10px] font-medium tracking-widest uppercase
                     text-slate-400 dark:text-slate-500"
        >
          Financial Copilot
        </span>
      </div>
    </div>
  );
}
