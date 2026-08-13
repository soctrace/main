import { useEffect, useState } from "react";
import type { CampaignChapter } from "@/features/campaigns/types";

export function ReadingProgress() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const update = () => { const max = document.documentElement.scrollHeight - innerHeight; setProgress(max > 0 ? Math.min(100, (scrollY / max) * 100) : 0); };
    update(); addEventListener("scroll", update, { passive: true }); addEventListener("resize", update);
    return () => { removeEventListener("scroll", update); removeEventListener("resize", update); };
  }, []);
  return <div className="campaign-progress" role="progressbar" aria-label="Progreso de lectura" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}><span style={{ transform: `scaleX(${progress / 100})` }} /></div>;
}

export function StickyChapterNav({ chapters }: { chapters: CampaignChapter[] }) {
  const [active, setActive] = useState(chapters[0]?.id);
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => { const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (visible) setActive(visible.target.id); }, { rootMargin: "-20% 0px -65%", threshold: [0, 0.15, 0.5] });
    chapters.forEach(({ id }) => { const element = document.getElementById(id); if (element) observer.observe(element); });
    return () => observer.disconnect();
  }, [chapters]);
  const groups = [["context", "Comprender Mijas"], ["diagnosis", "Comprender el electorado"], ["execution", "Convertir evidencia"], ["methodology", "Método"]] as const;
  return <nav className="campaign-chapter-nav" aria-label="Índice del informe"><div>{groups.map(([group, label]) => {
    const items = chapters.filter((chapter) => chapter.group === group); const groupActive = items.some((item) => item.id === active);
    if (!items.length) return null;
    return <section key={group} className={`${groupActive ? "active" : ""} ${items.some(item => item.id === "your-campaign") ? "campaign-nav-commercial" : ""}`} aria-label={label}><p>{label}</p><div>{items.map((item) => <a key={item.id} href={`#${item.id}`} title={item.title} className={`${active === item.id ? "active" : ""} ${item.id === "your-campaign" ? "commercial" : ""}`} aria-current={active === item.id ? "location" : undefined}><span>{item.number}</span><b>{item.navLabel}</b></a>)}</div></section>;
  })}</div></nav>;
}
