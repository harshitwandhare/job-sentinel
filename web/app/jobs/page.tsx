import { JobActions } from "@/components/JobActions";
import { ScraperControls } from "@/components/ScraperControls";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { getJobs, type JobDetail, type JobPosting } from "@/lib/api";
import { externalUrl } from "@/lib/utils";

export const dynamic = "force-dynamic";

function detailOf(job: JobPosting): JobDetail | undefined {
  return job.raw_data?.detail;
}

function FactRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-40 shrink-0 text-muted">{label}</span>
      <span className="text-ink">{String(value)}</span>
    </div>
  );
}

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
        jobs.map((j) => {
          const d = detailOf(j);
          return (
            <Card key={j.posting_id} className="space-y-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>{j.title}</CardTitle>
                  <CardSub>
                    {[j.employer, j.location, j.job_type].filter(Boolean).join(" · ")}
                  </CardSub>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                    {j.posted_date && <CardSub>Posted: {j.posted_date}</CardSub>}
                    {j.deadline && (
                      <CardSub className="text-amber-600">Deadline: {j.deadline}</CardSub>
                    )}
                    {d?.salary && <CardSub className="text-emerald-700">{d.salary}</CardSub>}
                    {typeof d?.num_applicants === "number" && (
                      <CardSub>{d.num_applicants} applicants</CardSub>
                    )}
                  </div>
                  {j.portal_url && (
                    <a
                      href={externalUrl(j.portal_url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-sm text-brand hover:underline"
                    >
                      View posting →
                    </a>
                  )}
                </div>
                <JobActions postingId={j.posting_id} status={j.status} />
              </div>

              {(d?.description || j.description_snippet) && (
                <details className="group">
                  <summary className="cursor-pointer select-none text-sm font-medium text-brand">
                    Job details
                  </summary>
                  <div className="mt-2 space-y-2 border-l-2 border-border pl-3">
                    <div className="space-y-0.5">
                      <FactRow label="Job function" value={d?.job_function} />
                      <FactRow label="Industry" value={d?.industry} />
                      <FactRow label="Openings" value={d?.openings} />
                      <FactRow
                        label="Work-study required"
                        value={
                          d?.work_study_required === undefined || d?.work_study_required === null
                            ? undefined
                            : d.work_study_required
                              ? "Yes"
                              : "No"
                        }
                      />
                      <FactRow label="Work authorization" value={d?.required_work_auth} />
                      <FactRow
                        label="Documents"
                        value={d?.application_documents?.length ? d.application_documents.join(", ") : undefined}
                      />
                      <FactRow
                        label="Contact"
                        value={
                          d?.contact_name
                            ? `${d.contact_name}${d.contact_email ? ` · ${d.contact_email}` : ""}`
                            : undefined
                        }
                      />
                    </div>
                    <p className="whitespace-pre-line text-sm text-muted">
                      {d?.description || j.description_snippet}
                    </p>
                  </div>
                </details>
              )}
            </Card>
          );
        })
      )}
    </div>
  );
}
