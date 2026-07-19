import Link from "next/link";

export default function ResponsibleAiPage() {
  return (
    <main className="auth-shell"><section className="auth-card">
      <p className="eyebrow">LIONSFORGE AI</p><h1>Responsible AI and research use</h1>
      <p className="muted">LionsForge AI is an assistive research and education system, not an authority that replaces human judgment.</p>
      <h2>Review every output</h2><p>AI responses can contain errors, missing context, unsupported claims, or outdated information. Users remain responsible for checking sources and conclusions.</p>
      <h2>Evidence-first design</h2><p>The product separates claims, evidence, user judgments, confidence, and unresolved questions. Validation status is an explainable workspace signal, not a declaration of objective truth.</p>
      <h2>Professional decisions</h2><p>Do not rely on LionsForge AI as legal, medical, financial, safety-critical, or other licensed professional advice. Obtain qualified review before acting on high-impact matters.</p>
      <h2>Privacy and sensitive information</h2><p>Do not enter passwords, secret keys, classified material, protected health information, or personal information you are not authorized to process.</p>
      <h2>Report concerns</h2><p>Use the support process to report harmful output, privacy concerns, security issues, or suspected abuse.</p>
      <p><Link href="/privacy">Privacy</Link> · <Link href="/terms">Terms</Link> · <Link href="/support">Support</Link></p>
    </section></main>
  );
}
