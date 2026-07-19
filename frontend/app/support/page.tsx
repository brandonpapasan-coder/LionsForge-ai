import Link from "next/link";

export default function SupportPage() {
  return (
    <main className="auth-shell"><section className="auth-card">
      <p className="eyebrow">LIONSFORGE AI</p><h1>Support and data requests</h1>
      <p className="muted">This page defines the required support process. A monitored public support address must be configured before registration opens.</p>
      <h2>Account and product support</h2><p>Include the account email, a concise description, the affected feature, approximate time, and a non-sensitive screenshot or error reference. Never send passwords, API keys, or authentication tokens.</p>
      <h2>Privacy and deletion requests</h2><p>Request access, correction, deletion, or account closure through the monitored support channel. Identity must be verified before account information is disclosed or removed.</p>
      <h2>Security reports</h2><p>Report suspected vulnerabilities privately. Do not include exploit details in public issues and do not access data belonging to another user.</p>
      <h2>AI-output and abuse reports</h2><p>Identify the affected feature and explain the concern without copying unnecessary private content. Reports involving immediate danger should be directed to appropriate emergency services.</p>
      <h2>Launch requirement</h2><p>The final deployment must replace this placeholder process with the approved support address, service owner, response targets, escalation path, and deletion verification procedure.</p>
      <p><Link href="/privacy">Privacy</Link> · <Link href="/terms">Terms</Link> · <Link href="/responsible-ai">AI use</Link></p>
    </section></main>
  );
}
