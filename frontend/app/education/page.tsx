import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { CompetencyTrends } from "@/components/competency-trends";
import { EducationHub } from "@/components/education-hub";
import "./education.css";

export default async function EducationPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) redirect("/login");
  return (
    <>
      <EducationHub />
      <CompetencyTrends />
    </>
  );
}
