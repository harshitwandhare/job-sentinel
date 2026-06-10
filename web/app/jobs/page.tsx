import { JobActions } from "@/components/JobActions";
import { ScraperControls } from "@/components/ScraperControls";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { getJobs } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobsPage() {
  const jobs = await getJobs(50);

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-12">
      <h1 className="text-3xl font-bold text-ink">Tracked jobs</h1>

      <ScraperControls />

      {jobs.length === 0 ? (
        <Card>
          <CardTitle>No jobs tracked yet</CardTitle>
          <CardSub className="mt-2">
            Use <strong>Login</strong> above to sign in to the portal once, then{" "}
            <strong>Run scraper</strong> to populate postings — the list refreshes
            automatically when the scrape finishes.
          </CardSub>
        </Card>
      ) : (
        jobs.map((j) => (
          <Card key={j.posting_id} className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>{j.title}</CardTitle>
              <CardSub>
                {[j.employer, j.location, j.job_type].filter(Boolean).join(" · ")}
              </CardSub>
              {j.deadline && (
                <CardSub className="mt-1 text-amber-600">Deadline: {j.deadline}</CardSub>
              )}
              {j.portal_url && (
                <a
                  href={j.portal_url}
                  className="mt-1 inline-block text-sm text-brand hover:underline"
                >
                  View posting →
                </a>
              )}
            </div>
            <JobActions postingId={j.posting_id} status={j.status} />
          </Card>
        ))
      )}
    </div>
  );
}
