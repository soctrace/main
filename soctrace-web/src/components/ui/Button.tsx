import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
    size?: "sm" | "md";
  }
>;

export function Button({
  children,
  className = "",
  size = "md",
  variant = "primary",
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-400/40";
  const sizes = {
    sm: "h-9 px-3 text-[0.8rem]",
    md: "h-11 px-4 text-sm",
  };
  const variants = {
    primary:
      "border border-cyan-300/20 bg-[linear-gradient(135deg,rgba(37,99,235,0.95),rgba(139,92,246,0.9))] text-white shadow-[0_18px_40px_rgba(37,99,235,0.22)] hover:brightness-110",
    secondary:
      "border border-white/10 bg-white/[0.05] text-slate-100 hover:border-cyan-300/20 hover:bg-white/[0.08]",
    ghost:
      "border border-transparent bg-transparent text-slate-300 hover:border-white/8 hover:bg-white/[0.04] hover:text-white",
  };

  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}
