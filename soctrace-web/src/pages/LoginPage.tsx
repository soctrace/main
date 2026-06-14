import { FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Loader2 } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { canAccessDashboard, getAuthorizedUser } from "@/auth/accessControl";
import { getOrCreateDemoSessionId, trackDemoEvent } from "@/lib/demoAnalytics";
import { isSupabaseConfigured, supabase } from "@/lib/supabaseClient";
import { navItems } from "@/landing/data/content";
import { Footer } from "@/landing/sections/Footer";
import { Navbar } from "@/landing/sections/Navbar";
import { SocTraceInsightPreview } from "@/components/marketing/SocTraceInsightPreview";

type LocationState = {
  from?: { pathname?: string };
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useAuth();
  const from = (location.state as LocationState | null)?.from?.pathname || "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!isSupabaseConfigured || !supabase) {
      setError("Supabase Auth no está configurado todavía.");
      return;
    }

    setLoading(true);
    const normalizedEmail = email.trim().toLowerCase();
    const { session, error: signInError } = await signIn(normalizedEmail, password);

    if (signInError || !session) {
      setLoading(false);
      setError("Email o contraseña incorrectos.");
      return;
    }

    getOrCreateDemoSessionId();

    if (!canAccessDashboard(session.user.email)) {
      await trackDemoEvent("login_denied", session.user.email ?? normalizedEmail, {
        reason: "email_not_authorized",
      });
      await supabase.auth.signOut();
      setLoading(false);
      setError("Este usuario no tiene acceso autorizado a la demo.");
      return;
    }

    const authorizedUser = getAuthorizedUser(session.user.email);
    await trackDemoEvent("login_success", session.user.email ?? normalizedEmail, {
      role: authorizedUser?.role,
      access: authorizedUser?.access,
    });
    setLoading(false);
    navigate(from === "/login" ? "/dashboard" : from, { replace: true });
  }

  return (
    <div className="landing-shell">
      <Navbar items={navItems} />
      <main className="relative z-10">
        <section className="mx-auto grid min-h-[calc(100vh-11rem)] max-w-[1180px] items-center gap-8 px-6 py-12 sm:px-8 lg:grid-cols-[0.9fr_1fr] lg:px-10">
          <div>
            <Link to="/" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-300 transition hover:text-white">
              <ArrowLeft className="h-4 w-4" />
              Volver a Inicio
            </Link>
            <h1 className="mt-8 max-w-2xl text-balance text-4xl font-semibold leading-tight text-white sm:text-5xl">
              Acceso privado a la demo friends & family de soctrace.
            </h1>
            <p className="section-copy mt-6">
              Valida tus credenciales para entrar al panel MVP. El acceso está limitado a usuarios autorizados manualmente.
            </p>
            <div className="mt-8">
              <SocTraceInsightPreview />
            </div>
          </div>

          <form onSubmit={handleSubmit} className="panel-dark grid gap-5 p-6 sm:p-8 lg:p-10" noValidate>
            <div className="flex items-center gap-3 border-b border-white/[0.08] pb-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-soc-accent">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-white">Acceder</h2>
                <p className="mt-1 text-sm text-slate-400">Demo privada soctrace</p>
              </div>
            </div>

            <label className="block">
              <span className="text-sm font-semibold text-slate-200">Correo electrónico</span>
              <input
                className="demo-input mt-2"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-slate-200">Contraseña</span>
              <div className="relative mt-2">
                <input
                  className="demo-input pr-12"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-3 flex h-full w-8 items-center justify-center rounded-full text-slate-400 transition hover:text-white focus:outline-none focus:ring-2 focus:ring-[rgba(244,124,42,0.4)]"
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  onClick={() => setShowPassword((current) => !current)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>

            {error ? (
              <div className="rounded-2xl border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full border border-[rgba(244,124,42,0.38)] bg-[linear-gradient(135deg,#f1f5f9_0%,#f47c2a_18%,#4a6fa5_100%)] px-6 py-3 text-sm font-semibold text-white shadow-[0_20px_70px_rgba(74,111,165,0.22)] transition hover:-translate-y-0.5 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Validar
              {!loading ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
            </button>
          </form>
        </section>
      </main>
      <Footer />
    </div>
  );
}
