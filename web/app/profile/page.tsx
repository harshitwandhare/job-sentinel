import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { getProfile } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const profile = await getProfile();

  if (!profile || !profile.basics.name) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <Card>
          <CardTitle>No profile yet</CardTitle>
          <CardSub className="mt-2">
            Start the API (<code>job-sentinel serve</code>) and create a profile with{" "}
            <code>job-sentinel resume init</code>, then refresh.
          </CardSub>
        </Card>
      </div>
    );
  }

  const { basics, experience, projects, skills, education } = profile;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-5 py-12">
      <header>
        <h1 className="text-3xl font-bold text-neutral-100">{basics.name}</h1>
        {basics.headline && <p className="mt-1 text-neutral-400">{basics.headline}</p>}
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-neutral-400">
          {basics.location && <span>{basics.location}</span>}
          {basics.email && <span>{basics.email}</span>}
          {basics.links.map((l) => (
            <a key={l.url} href={l.url} className="text-brand hover:underline">
              {l.label}
            </a>
          ))}
        </div>
        {basics.summary && <p className="mt-4 text-neutral-300">{basics.summary}</p>}
      </header>

      {experience.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-neutral-100">Experience</h2>
          {experience.map((x, i) => (
            <Card key={`${x.company}-${i}`}>
              <CardTitle>
                {x.role} · {x.company}
              </CardTitle>
              <CardSub>
                {x.start} – {x.end}
                {x.location ? ` · ${x.location}` : ""}
              </CardSub>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-neutral-300">
                {x.bullets.map((b, j) => (
                  <li key={j}>{b}</li>
                ))}
              </ul>
            </Card>
          ))}
        </section>
      )}

      {projects.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-neutral-100">Projects</h2>
          {projects.map((p, i) => (
            <Card key={`${p.name}-${i}`}>
              <CardTitle>{p.name}</CardTitle>
              {p.description && <CardSub>{p.description}</CardSub>}
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-neutral-300">
                {p.bullets.map((b, j) => (
                  <li key={j}>{b}</li>
                ))}
              </ul>
            </Card>
          ))}
        </section>
      )}

      {education.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-neutral-100">Education</h2>
          {education.map((e, i) => (
            <Card key={`${e.institution}-${i}`}>
              <CardTitle>{e.institution}</CardTitle>
              <CardSub>
                {e.degree}
                {e.gpa ? ` · GPA ${e.gpa}` : ""}
              </CardSub>
            </Card>
          ))}
        </section>
      )}

      {skills.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-neutral-100">Skills</h2>
          <div className="space-y-2">
            {skills.map((g, i) => (
              <p key={`${g.category}-${i}`} className="text-sm text-neutral-300">
                <span className="font-medium text-neutral-100">{g.category}:</span>{" "}
                {g.skills.join(", ")}
              </p>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
