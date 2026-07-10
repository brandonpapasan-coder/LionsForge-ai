"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type ModuleCompletionButtonProps = {
  courseId: string;
  moduleId: string;
  completed: boolean;
};

export function ModuleCompletionButton({ courseId, moduleId, completed }: ModuleCompletionButtonProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  async function completeModule() {
    setSubmitting(true);
    try {
      const response = await fetch("/api/education/completions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ course_id: courseId, module_id: moduleId }),
      });
      if (response.ok) router.refresh();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <button
      type="button"
      className={`module-complete-button ${completed ? "completed" : ""}`}
      onClick={completeModule}
      disabled={completed || submitting}
    >
      {completed ? "Completed" : submitting ? "Saving..." : "Mark complete"}
    </button>
  );
}
