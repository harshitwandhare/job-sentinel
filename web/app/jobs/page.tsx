import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { getJobs } from "@/lib/api";

export const dynamic = "force-dynamic";

const STATUS_STYLES: Record<string, string> = {
  new: "bg-emerald-900/60 text-emerald-300",
  seen: "bg-sky-900/60 text-sky-300",
  applied: "bg-violet-900/60 text-violet-300",
  ignored: "bg-neutral-800 text-neutral-400",
  closed: "bg-neutral-800 text-neutral-500",
};

export default async function JobsPage() {
  const jobs = await getJobs(50);

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-12">
      <h1 className="text-3xl font-bold text-neutral-100">Tracked jobs</h1>

      {jobs.length === 0 ? (
        <Card>
          <CardTitle>No jobs tracked yet</CardTitle>
          <CardSub className="mt-2">
            Run <code>job-sentinel scrape</code> (after <code>job-sentinel login</code>) to
            populate postings, then refresh.
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
                <CardSub className="mt-1 text-amber-400">Deadline: {j.deadline}</CardSub>
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
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                STATUS_STYLES[j.status] ?? "bg-neutral-800 text-neutral-400"
              }`}
            >
              {j.status}
            </span>
          </Card>
        ))
      )}
    </div>
  );
}
