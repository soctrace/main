type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description: string;
  align?: "left" | "center";
};

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
}: SectionHeadingProps) {
  const alignment = align === "center" ? "mx-auto text-center" : "";

  return (
    <div className={`max-w-3xl ${alignment}`.trim()}>
      <span className="chip">{eyebrow}</span>
      <h2 className="mt-6 text-balance text-3xl font-semibold text-white sm:text-4xl">
        {title}
      </h2>
      <p className="section-copy mt-5">{description}</p>
    </div>
  );
}
