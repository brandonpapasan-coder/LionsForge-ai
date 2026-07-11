"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: String(form.get("email") ?? ""),
          secret: String(form.get("secret") ?? ""),
          full_name: null,
        }),
      });
      if (!response.ok) {
        const payload = await response.json();
        setMessage(payload.detail ?? "Unable to sign in.");
        return;
      }
      router.push("/mentor");
      router.refresh();
    } catch {
      setMessage("The authentication service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="eyebrow">LIONSFORGE AI</p>
        <h1>Enter the Mentor Workspace.</h1>
        <p className="muted">Sign in to continue your research, learning, and mentor conversations.</p>
        <form onSubmit={handleSubmit}>
          <label>Email<input name="email" type="email" required autoComplete="email" /></label>
          <label>Password<input name="secret" type="password" required autoComplete="current-password" /></label>
          <button type="submit" disabled={submitting}>{submitting ? "Signing in..." : "Sign in"}</button>
        </form>
        {message ? <p role="alert" className="form-message">{message}</p> : null}
      </section>
    </main>
  );
}
