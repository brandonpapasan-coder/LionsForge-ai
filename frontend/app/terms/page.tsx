import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="auth-shell"><section className="auth-card">
      <p className="eyebrow">LIONSFORGE AI</p><h1>Terms of service</h1>
      <p className="muted">Draft for legal review before public registration opens. Last updated July 19, 2026.</p>
      <h2>Service purpose</h2><p>LionsForge AI supports research, evidence validation, learning, and mentor-assisted reasoning. It does not provide guaranteed conclusions, professional advice, or autonomous decision authority.</p>
      <h2>User responsibilities</h2><p>Users must provide accurate account information, protect credentials, submit only content they are authorized to process, review AI-generated output, respect intellectual property, and comply with applicable law.</p>
      <h2>Prohibited use</h2><p>Users may not abuse the service, bypass access controls, harm others, upload malicious code, expose another person&apos;s private data, or use the product for unlawful surveillance, fraud, or dangerous activity.</p>
      <h2>AI and research limitations</h2><p>AI responses may be incomplete, outdated, or incorrect. Evidence labels and confidence indicators are research aids rather than guarantees of truth. Important decisions require independent verification and qualified professional review where appropriate.</p>
      <h2>Availability and changes</h2><p>Features may change during beta. Access may be limited or suspended to protect users, systems, or legal compliance. Final terms must address payment, cancellation, warranties, liability, dispute resolution, governing law, and age requirements after legal review.</p>
      <p><Link href="/privacy">Privacy</Link> · <Link href="/responsible-ai">AI use</Link> · <Link href="/support">Support</Link></p>
    </section></main>
  );
}
