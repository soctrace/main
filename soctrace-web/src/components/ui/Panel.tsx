import type { HTMLAttributes, PropsWithChildren } from "react";

type PanelProps = PropsWithChildren<
  HTMLAttributes<HTMLDivElement> & {
    tone?: "default" | "elevated";
  }
>;

export function Panel({ children, className = "", tone = "default", ...props }: PanelProps) {
  const tones = {
    default:
      "border border-white/[0.06] bg-[linear-gradient(180deg,rgba(14,19,29,0.94),rgba(10,14,24,0.94))]",
    elevated:
      "border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(17,24,39,0.96),rgba(9,13,22,0.98))] shadow-[0_24px_80px_rgba(0,0,0,0.35)]",
  };

  return (
    <div className={`rounded-[1.4rem] ${tones[tone]} ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}
