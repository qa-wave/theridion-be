import { Activity, GitBranch, MonitorPlay, Plus, Radio, Server, Workflow, Zap } from "lucide-react";
import { useState } from "react";
import { Tooltip } from "./Tooltip";

export type AppMode = "requests" | "flows" | "traffic" | "monitors" | "silk" | "spin" | "hubOverview";

// Per-mode accent colors. Default (undefined) falls back to emerald-500 via CSS var.
const MODE_ACCENT: Partial<Record<AppMode, string>> = {
  silk: undefined, // uses default emerald
  spin: "#a3e635", // lime-400 — Spin brand
};

interface Props {
  mode: AppMode;
  onModeChange: (mode: AppMode) => void;
  networkEntryCount?: number;
}

/** Primary rail — always visible */
const primaryModes: { id: AppMode; icon: typeof Zap; label: string }[] = [
  { id: "requests", icon: Zap, label: "Requests" },
  { id: "flows", icon: GitBranch, label: "Flows" },
  { id: "traffic", icon: Radio, label: "Traffic" },
];

/** Secondary modules — hidden behind the "+" overflow button */
const secondaryModes: { id: AppMode; icon: typeof Zap; label: string }[] = [
  { id: "monitors", icon: Activity, label: "Monitors" },
  { id: "silk", icon: MonitorPlay, label: "Silk (Frontend tests)" },
  { id: "spin", icon: Workflow, label: "Spin (Backend tests)" },
  { id: "hubOverview", icon: Server, label: "Hub Overview" },
];

export function ActivityBar({ mode, onModeChange, networkEntryCount = 0 }: Props) {
  const [overflowOpen, setOverflowOpen] = useState(false);

  const isSecondaryActive = secondaryModes.some((m) => m.id === mode);

  function handleModeChange(newMode: AppMode) {
    onModeChange(newMode);
    setOverflowOpen(false);
  }

  return (
    <nav
      role="navigation"
      aria-label="Module switcher"
      className="flex h-full w-12 flex-col items-center border-r border-white/[0.06] bg-neutral-950 py-2 gap-1"
    >
      {primaryModes.map((m) => {
        const active = mode === m.id;
        const Icon = m.icon;
        const hasContent = m.id === "traffic" && networkEntryCount > 0;
        return (
          <Tooltip key={m.id} content={m.label} side="right">
            <button
              onClick={() => handleModeChange(m.id)}
              aria-label={m.label}
              aria-current={active ? "page" : undefined}
              className={`group relative flex h-10 w-10 items-center justify-center transition-colors ${
                active
                  ? "bg-white/[0.06]"
                  : "border-l-2 border-transparent hover:bg-white/[0.04]"
              }`}
              style={active ? {
                borderLeft: `2px solid ${MODE_ACCENT[m.id] ?? "rgb(16 185 129)"}`,
              } : undefined}
            >
              {/* Subtle glow behind icon on hover */}
              <span className="pointer-events-none absolute inset-0 rounded-lg opacity-0 transition-opacity duration-200 group-hover:opacity-100 bg-[radial-gradient(circle,rgb(var(--accent-500)/0.12)_0%,transparent_70%)]" />
              <Icon
                size={18}
                className={`relative z-10 ${active ? "text-neutral-100" : "text-neutral-500"}`}
                style={active && MODE_ACCENT[m.id] ? { color: MODE_ACCENT[m.id] } : undefined}
              />
              {/* Content dot indicator */}
              {hasContent && !active && (
                <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500" />
              )}
              {/* Badge for traffic count */}
              {m.id === "traffic" && networkEntryCount > 0 && active && (
                <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-emerald-600 px-1 text-[10px] font-bold text-white">
                  {networkEntryCount > 99 ? "99+" : networkEntryCount}
                </span>
              )}
            </button>
          </Tooltip>
        );
      })}

      {/* Overflow "+" button — shows secondary modules */}
      <div className="relative mt-auto mb-1">
        <Tooltip content="More modules" side="right">
          <button
            onClick={() => setOverflowOpen((o) => !o)}
            aria-label="More modules"
            aria-expanded={overflowOpen}
            className={`group relative flex h-10 w-10 items-center justify-center transition-colors border-l-2 ${
              overflowOpen
                ? "bg-white/[0.06] border-white/20"
                : "border-transparent hover:bg-white/[0.04]"
            }`}
          >
            <Plus
              size={16}
              className={`relative z-10 transition-transform duration-150 ${
                overflowOpen ? "text-neutral-100 rotate-45" : "text-neutral-500"
              }`}
            />
            {/* Badge dot when a secondary module is active */}
            {isSecondaryActive && !overflowOpen && (
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-cobweb-400" />
            )}
          </button>
        </Tooltip>

        {/* Overflow flyout — vertical mini-menu */}
        {overflowOpen && (
          <div
            className="absolute left-full top-0 z-50 ml-2 flex flex-col rounded-lg border border-white/[0.08] bg-neutral-900/95 py-1 shadow-xl backdrop-blur-sm"
            style={{ minWidth: "160px" }}
          >
            {secondaryModes.map((m) => {
              const active = mode === m.id;
              const Icon = m.icon;
              return (
                <button
                  key={m.id}
                  onClick={() => handleModeChange(m.id)}
                  aria-label={m.label}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2.5 px-3 py-2 text-xs transition-colors ${
                    active
                      ? "bg-white/[0.08] text-neutral-100"
                      : "text-neutral-400 hover:bg-white/[0.04] hover:text-neutral-200"
                  }`}
                  style={active ? { borderLeft: `2px solid ${MODE_ACCENT[m.id] ?? "rgb(16 185 129)"}` } : { borderLeft: "2px solid transparent" }}
                >
                  <Icon
                    size={14}
                    className="shrink-0"
                    style={active && MODE_ACCENT[m.id] ? { color: MODE_ACCENT[m.id] } : undefined}
                  />
                  <span>{m.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}
