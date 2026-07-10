"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import type { AuthResult } from "@/lib/auth";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);

    const form = new FormData(event.currentTarget);
    const payload = {
      email: String(form.get("email") ?? ""),
      secret: String(form.get("secret") ?? ""),
      ...(mode === "register" ? { full_name: String(form.get("full_name") ?? "") } : {}),
    };

    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json()) as AuthResult;
      setMessage(result.message);
      if (response.ok) {
        if (mode === "login") {
          router.push("/dashboard");
          router.refresh();
        } else {
          router.push("/login?registered=1");
        }
      }
    } catch {
      setMessage("The authentication service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-card">
        <p className="eyebrow">LIONSFORGE AI</p>
        <h1>{mode === "login" ? "Welcome back." : "Create your account."}</h1>
        <p className="auth-copy">
          {mode === "login"
            ? "Continue your research, validation, and learning workspace."
            : "Start building evidence-backed research and financial expertise."}
        </p>

        <form onSubmit={handleSubmit}>
          {mode === "register" ? (
            <label>
              Full name
              <input name="full_name" type="text" maxLength={120} autoComplete="name" />
            </label>
          ) : null}
          <label>
            Email
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <label>
            Password
            <input
              name="secret"
              type="password"
              required
              minLength={8}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        {message ? <p className="form-message" role="status">{message}</p> : null}
        <p className="auth-switch">
          {mode === "login" ? "Need an account?" : "Already have an account?"} {" "}
          <Link href={mode === "login" ? "/register" : "/login"}>
            {mode === "login" ? "Register" : "Sign in"}
          </Link>
        </p>
      </section>
    </div>
  );
}
