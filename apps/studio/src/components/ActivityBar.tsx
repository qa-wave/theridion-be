import { Activity, GitBranch, MonitorPlay, Radio, Server, Workflow, Zap } from "lucide-react";
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

const modes: { id: AppMode; icon: typeof Zap; label: string }[] = [
  { id: "requests", icon: Zap, label: "Requests" },
  { id: "flows", icon: GitBranch, label: "Flows" },
  { id: "traffic", icon: Radio, label: "Traffic" },
  { id: "monitors", icon: Activity, label: "Monitors" },
  { id: "silk", icon: MonitorPlay, label: "Silk (Frontend tests)" },
  { id: "spin", icon: Workflow, label: "Spin (Backend tests)" },
  { id: "hubOverview", icon: Server, label: "Hub Overview" },
];

export function ActivityBar({ mode, onModeChange, networkEntryCount = 0 }: Props) {
  return (
    <div className="flex h-full w-12 flex-col items-center border-r border-white/[0.06] bg-neutral-950 py-2 gap-1">
      {modes.map((m) => {
        const active = mode === m.id;
        const Icon = m.icon;
        const hasContent = m.id === "traffic" && networkEntryCount > 0;
        return (
          <Tooltip key={m.id} content={m.label} side="right">
            <button
              onClick={() => onModeChange(m.id)}
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
    </div>
  );
}
