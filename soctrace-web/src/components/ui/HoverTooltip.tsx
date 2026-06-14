import { useRef, useState, type CSSProperties, type PropsWithChildren, type ReactNode } from "react";

type HoverTooltipProps = PropsWithChildren<{
  content: ReactNode;
  className?: string;
  tooltipClassName?: string;
  style?: CSSProperties;
  autoFlip?: boolean;
  placement?: "top" | "bottom";
}>;

export function HoverTooltip({
  children,
  className = "",
  content,
  style,
  tooltipClassName = "",
  autoFlip = false,
  placement = "top",
}: HoverTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [horizontalPlacement, setHorizontalPlacement] = useState<"left" | "right">("left");

  const updatePlacement = () => {
    if (!autoFlip || !tooltipRef.current) {
      return;
    }

    window.requestAnimationFrame(() => {
      const rect = tooltipRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }

      setHorizontalPlacement(rect.right > window.innerWidth - 10 ? "right" : "left");
    });
  };

  return (
    <div
      className={`group relative ${className}`.trim()}
      style={style}
      onMouseEnter={updatePlacement}
      onFocus={updatePlacement}
    >
      {children}
      <div
        ref={tooltipRef}
        role="tooltip"
        className={`pointer-events-none absolute z-30 w-full translate-y-1 opacity-0 transition duration-200 ease-out group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100 ${
          placement === "bottom" ? "top-full mt-3" : "bottom-full mb-3"
        } ${horizontalPlacement === "right" ? "right-0" : "left-0"} ${tooltipClassName}`.trim()}
      >
        {content}
      </div>
    </div>
  );
}
