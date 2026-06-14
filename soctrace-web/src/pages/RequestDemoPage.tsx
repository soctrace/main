import { FormEvent, ReactNode, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Loader2, Mail } from "lucide-react";
import { Link } from "react-router-dom";
import { submitDemoRequest } from "@/lib/api";
import { navItems } from "@/landing/data/content";
import { Footer } from "@/landing/sections/Footer";
import { Navbar } from "@/landing/sections/Navbar";
import { SocTraceInsightPreview } from "@/components/marketing/SocTraceInsightPreview";

const sectorOptions = [
  "Investigación",
  "Educación",
  "Administración Pública",
  "Partido Político",
  "Empresa privada",
  "Otros",
];

type FormState = {
  organization: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  sector: string;
  reasons: string;
};

const initialForm: FormState = {
  organization: "",
  firstName: "",
  lastName: "",
  email: "",
  phone: "",
  sector: "",
  reasons: "",
};

function countWords(value: string) {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

function validate(form: FormState) {
  const errors: Partial<Record<keyof FormState, string>> = {};
  if (!form.organization.trim()) errors.organization = "Indica la organización.";
  if (!form.firstName.trim()) errors.firstName = "Indica tu nombre.";
  if (!form.lastName.trim()) errors.lastName = "Indica tus apellidos.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) errors.email = "Introduce un email válido.";
  if (form.phone.trim() && !/^[0-9+()\s.-]{7,40}$/.test(form.phone.trim())) {
    errors.phone = "Introduce un teléfono válido.";
  }
  if (!form.sector) errors.sector = "Selecciona un sector.";
  if (!form.reasons.trim()) errors.reasons = "Cuéntanos brevemente el motivo.";
  if (countWords(form.reasons) > 200) errors.reasons = "El texto no debe superar 200 palabras.";
  return errors;
}

export function RequestDemoPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [submitError, setSubmitError] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");
  const wordCount = useMemo(() => countWords(form.reasons), [form.reasons]);

  function updateField(name: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
    setSubmitError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setStatus("loading");
    setSubmitError("");
    try {
      await submitDemoRequest({
        organization: form.organization.trim(),
        firstName: form.firstName.trim(),
        lastName: form.lastName.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        sector: form.sector,
        reasons: form.reasons.trim(),
      });
      setStatus("success");
    } catch (error) {
      setStatus("idle");
      setSubmitError(error instanceof Error ? error.message : "No se pudo enviar la solicitud.");
    }
  }

  return (
    <div className="landing-shell">
      <Navbar items={navItems} />
      <main className="relative z-10">
        <section className="mx-auto grid max-w-[1400px] gap-8 px-6 py-12 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:px-10 lg:py-18">
          <div className="flex flex-col justify-between gap-8">
            <div>
              <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-300 transition hover:text-white">
                <ArrowLeft className="h-4 w-4" />
                Volver a Inicio
              </Link>
              <h1 className="mt-6 max-w-3xl text-balance text-4xl font-semibold leading-tight text-white sm:text-5xl lg:text-6xl">
                Solicita acceso a una demo gratuita de soctrace
              </h1>
              <p className="section-copy mt-6">
                Cuéntanos quién eres y qué quieres analizar. Prepararemos una demo del MVP alineada con tu contexto territorial, estratégico o académico.
              </p>
            </div>
            <SocTraceInsightPreview />
          </div>

          <div className="panel-dark overflow-hidden">
            {status === "success" ? (
              <div className="flex min-h-[680px] flex-col items-start justify-center p-6 sm:p-10">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-300">
                  <CheckCircle2 className="h-7 w-7" />
                </div>
                <h2 className="mt-7 text-3xl font-semibold text-white">
                  Solicitud en proceso
                </h2>
                <p className="mt-4 max-w-xl text-base leading-8 text-slate-300">
                  Solicitud en proceso, nos pondremos en contacto contigo con la mayor brevedad.
                </p>
                <Link
                  to="/"
                  className="mt-8 inline-flex items-center justify-center rounded-full border border-[rgba(74,111,165,0.24)] bg-white/[0.04] px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:border-[rgba(244,124,42,0.28)]"
                >
                  Volver a Inicio
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="grid gap-5 p-5 sm:p-8 lg:p-10" noValidate>
                <div className="flex items-center gap-3 border-b border-white/[0.08] pb-5">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-soc-accent">
                    <Mail className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-semibold text-white">Solicitar demo</h2>
                    <p className="mt-1 text-sm text-slate-400">Todos los campos marcados son necesarios.</p>
                  </div>
                </div>

                <Field label="Organización a la que representa" error={errors.organization}>
                  <input className="demo-input" value={form.organization} onChange={(event) => updateField("organization", event.target.value)} />
                </Field>

                <div className="grid gap-5 sm:grid-cols-2">
                  <Field label="Nombre" error={errors.firstName}>
                    <input className="demo-input" value={form.firstName} onChange={(event) => updateField("firstName", event.target.value)} />
                  </Field>
                  <Field label="Apellidos" error={errors.lastName}>
                    <input className="demo-input" value={form.lastName} onChange={(event) => updateField("lastName", event.target.value)} />
                  </Field>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <Field label="Correo electrónico" error={errors.email}>
                    <input className="demo-input" type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} />
                  </Field>
                  <Field label="Número de teléfono" error={errors.phone}>
                    <input className="demo-input" value={form.phone} onChange={(event) => updateField("phone", event.target.value)} />
                  </Field>
                </div>

                <Field label="Sector al que representa" error={errors.sector}>
                  <select className="demo-input" value={form.sector} onChange={(event) => updateField("sector", event.target.value)}>
                    <option value="">Selecciona una opción</option>
                    {sectorOptions.map((sector) => (
                      <option key={sector} value={sector}>
                        {sector}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Motivos por los que solicita acceso a una demo gratuita" error={errors.reasons}>
                  <textarea
                    className="demo-input min-h-[170px] resize-y"
                    value={form.reasons}
                    onChange={(event) => updateField("reasons", event.target.value)}
                  />
                  <div className={`mt-2 text-right text-xs ${wordCount > 200 ? "text-red-300" : "text-slate-500"}`}>
                    {wordCount}/200 palabras
                  </div>
                </Field>

                {submitError ? (
                  <div className="rounded-2xl border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">
                    {submitError}
                  </div>
                ) : null}

                <button
                  type="submit"
                  disabled={status === "loading"}
                  className="inline-flex items-center justify-center rounded-full border border-[rgba(244,124,42,0.38)] bg-[linear-gradient(135deg,#f1f5f9_0%,#f47c2a_18%,#4a6fa5_100%)] px-6 py-3 text-sm font-semibold text-white shadow-[0_20px_70px_rgba(74,111,165,0.22)] transition hover:-translate-y-0.5 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
                >
                  {status === "loading" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Enviar
                </button>
              </form>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-200">{label}</span>
      <div className="mt-2">{children}</div>
      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}
    </label>
  );
}
