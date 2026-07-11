import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ExecutiveDashboard } from "@/components/executive-dashboard";

export default async function DashboardPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) {
    redirect("/login");
  }

  return (
    <main>
      <ExecutiveDashboard />
    </main>
  );
}
