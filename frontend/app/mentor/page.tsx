import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { MentorWorkspace } from "@/components/mentor-workspace";

export default async function MentorPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) {
    redirect("/login");
  }

  return (
    <main>
      <MentorWorkspace />
    </main>
  );
}
