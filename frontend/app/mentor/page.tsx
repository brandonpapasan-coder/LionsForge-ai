import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { MentorWorkspace } from "@/components/mentor-workspace";

type MentorPageProps = {
  searchParams: Promise<{
    research_project?: string;
    research_session?: string;
  }>;
};

export default async function MentorPage({ searchParams }: MentorPageProps) {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) {
    redirect("/login");
  }

  const params = await searchParams;
  return (
    <main>
      <MentorWorkspace
        researchProjectId={params.research_project ?? null}
        researchSessionId={params.research_session ?? null}
      />
    </main>
  );
}
