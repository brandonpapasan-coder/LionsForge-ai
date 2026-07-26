import Link from "next/link";

import { VerificationReceiptValidator } from "@/components/verification-receipt-validator";

export default function VerificationReceiptValidationPage() {
  return (
    <main>
      <p><Link href="/review-queue/artifact-integrity">Open the unified artifact integrity workspace</Link></p>
      <VerificationReceiptValidator />
    </main>
  );
}
