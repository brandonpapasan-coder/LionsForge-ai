import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PracticumReviewerWorkspace } from "@/components/practicum-reviewer-workspace";
import "./reviewer.css";

export default async function PracticumReviewerPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) redirect("/login");
  return <PracticumReviewerWorkspace />;
}
