import { JobsExplorer } from "@/components/JobsExplorer";
import { ScraperControls } from "@/components/ScraperControls";
import { getJobs } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobsPage() {
  const jobs = await getJobs(50);

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-ink">Tracked jobs</h1>
        <p className="mt-1 text-sm text-muted">
          Every posting the watcher has seen — search it, triage it, generate documents for it.
        </p>
      </div>

      <ScraperControls />

      <JobsExplorer jobs={jobs} />
    </div>
  );
}
