import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { InvestigationWorkspace } from "@/components/investigation-workspace";
import "../education/education.css";

export default async function InvestigationsPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) redirect("/login");
  return <InvestigationWorkspace />;
}
