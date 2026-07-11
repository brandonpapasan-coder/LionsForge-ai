import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ResearchWorkspace } from "@/components/research-workspace";
import "./research.css";
import "./sessions.css";

export default async function ResearchPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) {
    redirect("/login");
  }

  return <ResearchWorkspace />;
}
