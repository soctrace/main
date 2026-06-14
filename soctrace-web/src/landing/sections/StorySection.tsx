import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import { SurfaceCard } from "@/landing/components/SurfaceCard";
import type { StoryBlock } from "@/landing/data/content";

type StorySectionProps = {
  block: StoryBlock;
};

export function StorySection({ block }: StorySectionProps) {
  return (
    <SectionShell id={block.id}>
      <div className="grid gap-8 lg:grid-cols-[0.8fr_minmax(0,1.2fr)]">
        <SectionHeading
          eyebrow={block.eyebrow}
          title={block.title}
          description={block.description}
        />
        <SurfaceCard className="grid gap-4 p-6 sm:grid-cols-3">
          {block.metrics.map((metric) => (
            <div
              key={metric}
              className="rounded-[1.3rem] border border-white/[0.08] bg-slate-950/55 px-5 py-6 text-center text-sm font-medium text-slate-200"
            >
              {metric}
            </div>
          ))}
        </SurfaceCard>
      </div>
    </SectionShell>
  );
}
