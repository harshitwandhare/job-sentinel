"use client";

import { useEffect, useRef, useState } from "react";

import { LocalSetupGuide } from "@/components/LocalSetupGuide";
import { PaperStage, ResumePaper } from "@/components/ResumePaper";
import { SentinelLoader } from "@/components/SentinelLoader";
import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type Award,
  buildResume,
  type Certification,
  type Education,
  type Experience,
  getProfile,
  importResume,
  type Profile,
  type Project,
  type Publication,
  putProfile,
  type SkillGroup,
} from "@/lib/api";

const EMPTY_PROFILE: Profile = {
  basics: { name: "", headline: "", email: "", phone: "", location: "", links: [], summary: "" },
  education: [],
  experience: [],
  projects: [],
  skills: [],
  certifications: [],
  awards: [],
  publications: [],
};

const EMPTY_EXP: Experience = { company: "", role: "", location: "", start: "", end: "", bullets: [], tags: [] };
const EMPTY_EDU: Education = { institution: "", degree: "", location: "", start: "", end: "", gpa: "", highlights: [] };
const EMPTY_PROJECT: Project = { name: "", description: "", url: "", bullets: [], tags: [] };
const EMPTY_CERT: Certification = { name: "", issuer: "", date: "" };
const EMPTY_AWARD: Award = { title: "", issuer: "", date: "", description: "" };
const EMPTY_PUB: Publication = { title: "", venue: "", date: "", url: "" };

const splitLines = (v: string) => v.split("\n").filter((s) => s.trim() !== "");
const splitCsv = (v: string) =>
  v
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

function isEmptyProfile(p: Profile): boolean {
  return !(
    p.basics.name ||
    p.education.length ||
    p.experience.length ||
    p.projects.length ||
    p.skills.length
  );
}

/**
 * Single profile screen: the same page shows the live profile and edits it.
 * Data flow: GET /api/profile → view → "Edit" copies it into a draft →
 * "Save" PUTs the draft and re-renders the view from the API's validated
 * response, so what you see is always what's stored in profile.yaml.
 */
export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState<Profile | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [apiDown, setApiDown] = useState(false);
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getProfile().then((p) => {
      if (p === null) setApiDown(true);
      else setProfile(p);
      setLoaded(true);
    });
  }, []);

  async function onSave() {
    if (!draft) return;
    setSaving(true);
    setStatus("Saving…");
    const saved = await putProfile(draft);
    setSaving(false);
    if (saved) {
      setProfile(saved);
      setDraft(null);
      setStatus("Saved ✓");
      setTimeout(() => setStatus(""), 2500);
    } else {
      setStatus("Save failed — is `job-sentinel serve` running?");
    }
  }

  async function onImportFile(file: File) {
    setImporting(true);
    setStatus("Extracting profile from PDF…");
    try {
      const result = await importResume(file);
      if (result.ok && result.profile) {
        setDraft(result.profile);
        setStatus("Imported — review the draft, then Save.");
      } else {
        setStatus(result.detail ?? "Import failed.");
      }
    } finally {
      setImporting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function onDownloadPdf() {
    setDownloading(true);
    setStatus("Building PDF…");
    const res = await buildResume();
    setDownloading(false);
    if (res.ok && res.blob) {
      const url = URL.createObjectURL(res.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.pdf";
      a.click();
      URL.revokeObjectURL(url);
      setStatus("");
    } else {
      setStatus(res.detail ?? "PDF build failed — is LaTeX (Tectonic) installed?");
    }
  }

  const uploadControl = (
    <>
      <input
        ref={fileInput}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onImportFile(f);
        }}
      />
      <Button
        variant="outline"
        disabled={importing || saving}
        onClick={() => fileInput.current?.click()}
      >
        {importing ? "Importing…" : "Upload resume (PDF)"}
      </Button>
    </>
  );

  if (!loaded) {
    return <SentinelLoader label="Loading your profile" />;
  }

  if (apiDown) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <LocalSetupGuide context="Your profile (and the résumé engine behind it)" />
      </div>
    );
  }

  const editing = draft !== null;

  if (!editing && (!profile || isEmptyProfile(profile))) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <Card className="space-y-3">
          <CardTitle>No profile yet</CardTitle>
          <CardSub>
            Your profile is the single source of truth for the résumé engine. Create it here —
            it saves straight to <code>data/profile.yaml</code> — or import an existing resume.
          </CardSub>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => setDraft(structuredClone(profile ?? EMPTY_PROFILE))}>
              Create profile
            </Button>
            {uploadControl}
            {status && <span className="text-sm text-muted">{status}</span>}
          </div>
        </Card>
      </div>
    );
  }

  if (editing) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 px-5 py-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-ink sm:text-3xl">Edit profile</h1>
          <div className="flex flex-wrap items-center gap-3">
            {status && <span className="text-sm text-muted">{status}</span>}
            <Button variant="outline" onClick={() => setDraft(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={onSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
        <Editor draft={draft!} setDraft={setDraft} />
      </div>
    );
  }

  // View mode: the profile rendered as the actual résumé sheet, on a desk.
  return (
    <div data-nav-theme="dark" className="relative min-h-screen overflow-hidden bg-night">
      <div className="bg-grid-dark absolute inset-0" aria-hidden="true" />
      <div
        aria-hidden="true"
        className="absolute left-1/2 top-0 h-[360px] w-[640px] -translate-x-1/2 rounded-full bg-brand-500/15 blur-[140px]"
      />
      <div className="relative mx-auto max-w-5xl px-5 py-10 sm:py-14">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-medium uppercase tracking-widest text-brand-400">
              Your profile
            </p>
            <h1 className="mt-1 text-2xl font-bold text-white sm:text-3xl">
              This page is your résumé.
            </h1>
            <p className="mt-1 max-w-xl text-sm text-stone-400">
              Rendered live from <code className="font-mono text-xs">data/profile.yaml</code> — the
              same single source of truth the PDF engine prints.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {status && <span className="text-sm text-stone-300">{status}</span>}
            {uploadControl}
            <Button variant="outline" onClick={onDownloadPdf} disabled={downloading || importing}>
              {downloading ? "Building…" : "Download PDF"}
            </Button>
            <Button onClick={() => setDraft(structuredClone(profile!))}>Edit</Button>
          </div>
        </div>

        <PaperStage>
          <ResumePaper profile={profile!} />
        </PaperStage>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Edit mode — every section the backend stores is editable here
// ─────────────────────────────────────────────────────────────────────────────

interface EditorProps {
  draft: Profile;
  setDraft: (p: Profile) => void;
}

function Editor({ draft, setDraft }: EditorProps) {
  const patch = (p: Partial<Profile>) => setDraft({ ...draft, ...p });
  const setBasics = (k: keyof Profile["basics"], v: string) =>
    patch({ basics: { ...draft.basics, [k]: v } });

  // Generic list helpers — one source of add/update/remove for every section.
  function listOps<K extends keyof Profile, T>(key: K, empty: T) {
    const list = draft[key] as T[];
    return {
      add: () => patch({ [key]: [...list, structuredClone(empty)] } as Partial<Profile>),
      remove: (i: number) =>
        patch({ [key]: list.filter((_, j) => j !== i) } as Partial<Profile>),
      update: (i: number, p: Partial<T>) =>
        patch({
          [key]: list.map((x, j) => (j === i ? { ...x, ...p } : x)),
        } as Partial<Profile>),
    };
  }

  const exp = listOps<"experience", Experience>("experience", EMPTY_EXP);
  const edu = listOps<"education", Education>("education", EMPTY_EDU);
  const proj = listOps<"projects", Project>("projects", EMPTY_PROJECT);
  const skill = listOps<"skills", SkillGroup>("skills", { category: "", skills: [] });
  const cert = listOps<"certifications", Certification>("certifications", EMPTY_CERT);
  const award = listOps<"awards", Award>("awards", EMPTY_AWARD);
  const pub = listOps<"publications", Publication>("publications", EMPTY_PUB);
  const link = listOps<never, { label: string; url: string }>(
    // links live inside basics, so handle them inline below instead
    undefined as never,
    { label: "", url: "" },
  );
  void link;

  const setLinks = (links: { label: string; url: string }[]) =>
    patch({ basics: { ...draft.basics, links } });

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <CardTitle>Basics</CardTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input placeholder="Name" value={draft.basics.name} onChange={(e) => setBasics("name", e.target.value)} />
          <Input placeholder="Headline" value={draft.basics.headline} onChange={(e) => setBasics("headline", e.target.value)} />
          <Input placeholder="Email" value={draft.basics.email} onChange={(e) => setBasics("email", e.target.value)} />
          <Input placeholder="Phone" value={draft.basics.phone} onChange={(e) => setBasics("phone", e.target.value)} />
          <Input placeholder="Location" value={draft.basics.location} onChange={(e) => setBasics("location", e.target.value)} />
        </div>
        <Textarea
          rows={3}
          placeholder="Summary"
          value={draft.basics.summary}
          onChange={(e) => setBasics("summary", e.target.value)}
        />
      </section>

      <EditSection title="Links" onAdd={() => setLinks([...draft.basics.links, { label: "", url: "" }])}>
        {draft.basics.links.map((l, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
            <Input
              placeholder="Label (GitHub, LinkedIn…)"
              value={l.label}
              onChange={(e) =>
                setLinks(draft.basics.links.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))
              }
            />
            <Input
              placeholder="https://…"
              value={l.url}
              onChange={(e) =>
                setLinks(draft.basics.links.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))
              }
            />
            <RemoveButton onClick={() => setLinks(draft.basics.links.filter((_, j) => j !== i))} />
          </div>
        ))}
      </EditSection>

      <EditSection title="Experience" onAdd={exp.add}>
        {draft.experience.map((x, i) => (
          <Card key={i} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input placeholder="Role" value={x.role} onChange={(e) => exp.update(i, { role: e.target.value })} />
              <Input placeholder="Company" value={x.company} onChange={(e) => exp.update(i, { company: e.target.value })} />
              <Input placeholder="Location" value={x.location} onChange={(e) => exp.update(i, { location: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">
                <Input placeholder="Start" value={x.start} onChange={(e) => exp.update(i, { start: e.target.value })} />
                <Input placeholder="End" value={x.end} onChange={(e) => exp.update(i, { end: e.target.value })} />
              </div>
            </div>
            <Textarea
              rows={3}
              placeholder="One bullet per line"
              value={x.bullets.join("\n")}
              onChange={(e) => exp.update(i, { bullets: splitLines(e.target.value) })}
            />
            <RemoveButton onClick={() => exp.remove(i)} label="Remove" />
          </Card>
        ))}
      </EditSection>

      <EditSection title="Projects" onAdd={proj.add}>
        {draft.projects.map((p, i) => (
          <Card key={i} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input placeholder="Name" value={p.name} onChange={(e) => proj.update(i, { name: e.target.value })} />
              <Input placeholder="URL" value={p.url} onChange={(e) => proj.update(i, { url: e.target.value })} />
            </div>
            <Input
              placeholder="One-line description"
              value={p.description}
              onChange={(e) => proj.update(i, { description: e.target.value })}
            />
            <Textarea
              rows={3}
              placeholder="One bullet per line"
              value={p.bullets.join("\n")}
              onChange={(e) => proj.update(i, { bullets: splitLines(e.target.value) })}
            />
            <RemoveButton onClick={() => proj.remove(i)} label="Remove" />
          </Card>
        ))}
      </EditSection>

      <EditSection title="Education" onAdd={edu.add}>
        {draft.education.map((e, i) => (
          <Card key={i} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input placeholder="Institution" value={e.institution} onChange={(ev) => edu.update(i, { institution: ev.target.value })} />
              <Input placeholder="Degree" value={e.degree} onChange={(ev) => edu.update(i, { degree: ev.target.value })} />
              <Input placeholder="Location" value={e.location} onChange={(ev) => edu.update(i, { location: ev.target.value })} />
              <div className="grid grid-cols-3 gap-2">
                <Input placeholder="Start" value={e.start} onChange={(ev) => edu.update(i, { start: ev.target.value })} />
                <Input placeholder="End" value={e.end} onChange={(ev) => edu.update(i, { end: ev.target.value })} />
                <Input placeholder="GPA" value={e.gpa} onChange={(ev) => edu.update(i, { gpa: ev.target.value })} />
              </div>
            </div>
            <Textarea
              rows={2}
              placeholder="Highlights — one per line (coursework, honors…)"
              value={e.highlights.join("\n")}
              onChange={(ev) => edu.update(i, { highlights: splitLines(ev.target.value) })}
            />
            <RemoveButton onClick={() => edu.remove(i)} label="Remove" />
          </Card>
        ))}
      </EditSection>

      <EditSection title="Skills" onAdd={skill.add}>
        {draft.skills.map((g, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
            <Input placeholder="Category" value={g.category} onChange={(e) => skill.update(i, { category: e.target.value })} />
            <Input
              placeholder="Comma-separated skills"
              value={g.skills.join(", ")}
              onChange={(e) => skill.update(i, { skills: splitCsv(e.target.value) })}
            />
            <RemoveButton onClick={() => skill.remove(i)} />
          </div>
        ))}
      </EditSection>

      <EditSection title="Certifications" onAdd={cert.add}>
        {draft.certifications.map((c, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[2fr_1fr_1fr_auto]">
            <Input placeholder="Name" value={c.name} onChange={(e) => cert.update(i, { name: e.target.value })} />
            <Input placeholder="Issuer" value={c.issuer} onChange={(e) => cert.update(i, { issuer: e.target.value })} />
            <Input placeholder="Date" value={c.date} onChange={(e) => cert.update(i, { date: e.target.value })} />
            <RemoveButton onClick={() => cert.remove(i)} />
          </div>
        ))}
      </EditSection>

      <EditSection title="Awards" onAdd={award.add}>
        {draft.awards.map((a, i) => (
          <Card key={i} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-3">
              <Input placeholder="Title" value={a.title} onChange={(e) => award.update(i, { title: e.target.value })} />
              <Input placeholder="Issuer" value={a.issuer} onChange={(e) => award.update(i, { issuer: e.target.value })} />
              <Input placeholder="Date" value={a.date} onChange={(e) => award.update(i, { date: e.target.value })} />
            </div>
            <Input
              placeholder="Description"
              value={a.description}
              onChange={(e) => award.update(i, { description: e.target.value })}
            />
            <RemoveButton onClick={() => award.remove(i)} label="Remove" />
          </Card>
        ))}
      </EditSection>

      <EditSection title="Publications" onAdd={pub.add}>
        {draft.publications.map((p, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[2fr_1fr_1fr_2fr_auto]">
            <Input placeholder="Title" value={p.title} onChange={(e) => pub.update(i, { title: e.target.value })} />
            <Input placeholder="Venue" value={p.venue} onChange={(e) => pub.update(i, { venue: e.target.value })} />
            <Input placeholder="Date" value={p.date} onChange={(e) => pub.update(i, { date: e.target.value })} />
            <Input placeholder="URL" value={p.url} onChange={(e) => pub.update(i, { url: e.target.value })} />
            <RemoveButton onClick={() => pub.remove(i)} />
          </div>
        ))}
      </EditSection>
    </div>
  );
}

function EditSection({
  title,
  onAdd,
  children,
}: {
  title: string;
  onAdd: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <Button variant="outline" size="sm" onClick={onAdd}>
          + Add
        </Button>
      </div>
      {children}
    </section>
  );
}

function RemoveButton({ onClick, label = "✕" }: { onClick: () => void; label?: string }) {
  return (
    <Button variant="ghost" size="sm" onClick={onClick}>
      {label}
    </Button>
  );
}
