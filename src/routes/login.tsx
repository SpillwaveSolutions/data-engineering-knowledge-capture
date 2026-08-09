import { createFileRoute, Link } from "@tanstack/react-router";
import { GROK_PROVIDERS, authEnabled, signIn } from "@/lib/auth/client";

export const Route = createFileRoute("/login")({ component: Login });

function Login() {
  return (
    <main className="grid min-h-dvh place-items-center p-6 pt-[var(--grok-banner-h,0px)]">
      <div className="panel w-full max-w-sm space-y-4 p-6 shadow-xl shadow-black/30">
        <div className="space-y-1">
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-primary">
            DEKC
          </p>
          <h1 className="text-xl font-semibold tracking-tight">Sign in</h1>
          <p className="text-sm text-muted">
            Optional — the sample knowledge catalog is public in this demo.
          </p>
        </div>
        {authEnabled ? (
          <div className="space-y-2">
            {GROK_PROVIDERS.map((p) => (
              <button
                key={p.providerId}
                type="button"
                onClick={() => signIn(p.providerId, { callbackURL: "/" })}
                className="w-full rounded-md border border-border bg-surface-2 px-4 py-2.5 text-sm font-medium transition hover:border-primary/50 hover:bg-surface"
              >
                Continue with {p.label}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">Sign-in is disabled.</p>
        )}
        <Link
          to="/"
          className="block text-center text-sm text-accent underline-offset-4 hover:underline"
        >
          Back to catalog
        </Link>
      </div>
    </main>
  );
}
