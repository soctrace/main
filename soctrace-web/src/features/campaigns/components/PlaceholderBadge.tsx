export function PlaceholderBadge({ children = "Ejemplo de estructura" }: { children?: string }) {
  return <span className="campaign-placeholder-badge">{children}</span>;
}
