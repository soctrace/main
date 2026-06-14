import type { PropsWithChildren } from "react";

type SectionShellProps = PropsWithChildren<{
  id?: string;
  className?: string;
}>;

export function SectionShell({ children, className = "", id }: SectionShellProps) {
  return (
    <section
      id={id}
      className={`relative z-10 mx-auto w-full max-w-7xl px-6 py-16 sm:px-8 sm:py-20 lg:px-12 ${className}`.trim()}
    >
      {children}
    </section>
  );
}
