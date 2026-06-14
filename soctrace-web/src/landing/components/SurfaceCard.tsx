import type { PropsWithChildren } from "react";

type SurfaceCardProps = PropsWithChildren<{
  className?: string;
}>;

export function SurfaceCard({ children, className = "" }: SurfaceCardProps) {
  return <div className={`panel-soft ${className}`.trim()}>{children}</div>;
}
