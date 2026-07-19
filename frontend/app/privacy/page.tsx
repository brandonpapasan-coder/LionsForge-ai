import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="eyebrow">LIONSFORGE AI</p>
        <h1>Privacy notice</h1>
        <p className="muted">Draft for legal review before public registration opens. Last updated July 19, 2026.</p>
        <h2>Information we process</h2>
        <p>We process account identifiers, authentication records, research content, evidence, learning activity, mentor conversations, service logs, and support requests needed to operate and secure LionsForge AI.</p>
        <h2>How information is used</h2>
        <p>Information is used to provide the service, preserve user work, personalize research and education features, prevent abuse, diagnose failures, support users, and improve reliability. We do not present private user content to other users.</p>
        <h2>AI processing</h2>
        <p>Selected prompts and context may be sent to configured AI providers to generate requested responses. Users should not submit secrets, regulated data, or information they are not authorized to process.</p>
        <h2>Retention and deletion</h2>
        <p>Account and workspace information is retained while the account is active and for limited operational, security, backup, and legal periods afterward. A verified deletion request will remove or de-identify eligible information subject to documented exceptions.</p>
        <h2>Security and access</h2>
        <p>Access is restricted by authentication, owner isolation, least-privilege operational controls, encrypted transport, and monitored production systems. No security measure eliminates all risk.</p>
        <h2>Contact</h2>
        <p>Privacy and deletion requests must use the support process published on the support page. The final public notice must name the legal entity, mailing address, jurisdiction-specific rights, subprocessors, retention periods, and effective date after legal review.</p>
        <p><Link href="/support">Support and data requests</Link> · <Link href="/terms">Terms</Link> · <Link href="/responsible-ai">AI use</Link></p>
      </section>
    </main>
  );
}
