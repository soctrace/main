import type { AnchorHTMLAttributes, PropsWithChildren } from "react";

type ActionButtonProps = PropsWithChildren<
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    variant?: "primary" | "secondary";
  }
>;

export function ActionButton({
  children,
  className = "",
  variant = "primary",
  ...props
}: ActionButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition duration-200";
  const variants = {
    primary:
      "border border-[rgba(244,124,42,0.38)] bg-[linear-gradient(135deg,#f1f5f9_0%,#f47c2a_18%,#4a6fa5_100%)] text-white shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_20px_70px_rgba(74,111,165,0.22)] hover:-translate-y-0.5 hover:brightness-110",
    secondary:
      "border border-[rgba(74,111,165,0.24)] bg-[linear-gradient(135deg,rgba(74,111,165,0.08),rgba(244,124,42,0.05))] text-white hover:-translate-y-0.5 hover:border-[rgba(244,124,42,0.28)] hover:bg-[linear-gradient(135deg,rgba(74,111,165,0.12),rgba(244,124,42,0.08))]",
  };

  return (
    <a className={`${base} ${variants[variant]} ${className}`.trim()} {...props}>
      {children}
    </a>
  );
}
