import { useMemo } from "react";

type Position = [number, number];

type SectionShapePreviewProps = {
  geometry?: GeoJSON.Geometry | null;
  color: string;
  title: string;
};

const VIEWBOX_SIZE = 120;
const PADDING = 12;

function collectRings(geometry?: GeoJSON.Geometry | null) {
  if (!geometry) {
    return [] as Position[][];
  }

  if (geometry.type === "Polygon") {
    return geometry.coordinates as Position[][];
  }

  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.flat() as Position[][];
  }

  return [] as Position[][];
}

function normalizeRings(rings: Position[][]) {
  const points = rings.flat();

  if (points.length === 0) {
    return [] as string[];
  }

  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  points.forEach(([x, y]) => {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  });

  const width = Math.max(maxX - minX, 1e-6);
  const height = Math.max(maxY - minY, 1e-6);
  const scale = Math.min(
    (VIEWBOX_SIZE - PADDING * 2) / width,
    (VIEWBOX_SIZE - PADDING * 2) / height,
  );
  const offsetX = (VIEWBOX_SIZE - width * scale) / 2;
  const offsetY = (VIEWBOX_SIZE - height * scale) / 2;

  return rings.map((ring) =>
    ring
      .map(([x, y], index) => {
        const normalizedX = offsetX + (x - minX) * scale;
        const normalizedY = VIEWBOX_SIZE - (offsetY + (y - minY) * scale);
        const command = index === 0 ? "M" : "L";
        return `${command}${normalizedX.toFixed(2)} ${normalizedY.toFixed(2)}`;
      })
      .join(" ")
      .concat(" Z"),
  );
}

export function SectionShapePreview({
  geometry,
  color,
  title,
}: SectionShapePreviewProps) {
  const paths = useMemo(() => normalizeRings(collectRings(geometry)), [geometry]);

  return (
    <div className="mt-6 flex w-full justify-center self-center">
      {paths.length > 0 ? (
        <svg
          viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
          className="mx-auto block h-32 w-full max-w-[12rem]"
          role="img"
          aria-label={`Shape preview for ${title}`}
        >
          {paths.map((path, index) => (
            <path
              key={`${index}-${path.length}`}
              d={path}
              fill={color}
              fillOpacity={0.32}
              stroke="rgba(255,255,255,0.18)"
              strokeWidth={0.9}
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
      ) : (
        <div
          className="mx-auto h-24 w-24 rounded-full"
          style={{
            background: `radial-gradient(circle, ${color}55 0%, ${color}18 52%, transparent 72%)`,
          }}
          aria-label={`Shape preview for ${title}`}
          role="img"
        />
      )}
    </div>
  );
}
