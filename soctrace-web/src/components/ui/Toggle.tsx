type ToggleProps = {
  checked: boolean;
  onChange: () => void;
};

export function Toggle({ checked, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      onClick={onChange}
      aria-pressed={checked}
      className={`relative inline-flex h-6 w-11 min-w-11 shrink-0 items-center rounded-full border transition ${
        checked
          ? "border-cyan-300/30 bg-[linear-gradient(135deg,#2563eb,#60a5fa)]"
          : "border-white/10 bg-white/[0.06]"
      }`}
    >
      <span
        className={`h-4 w-4 rounded-full bg-white shadow-[0_4px_12px_rgba(0,0,0,0.45)] transition ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}
