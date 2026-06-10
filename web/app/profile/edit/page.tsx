"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type Experience,
  getProfile,
  type Profile,
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

const EMPTY_EXP: Experience = {
  company: "",
  role: "",
  location: "",
  start: "",
  end: "",
  bullets: [],
  tags: [],
};

export default function ProfileEditPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getProfile().then((p) => setProfile(p && p.basics ? p : EMPTY_PROFILE));
  }, []);

  if (!profile) {
    return <div className="mx-auto max-w-3xl px-5 py-16 text-muted">Loading…</div>;
  }

  const setBasics = (k: keyof Profile["basics"], v: string) =>
    setProfile({ ...profile, basics: { ...profile.basics, [k]: v } });

  const setExp = (i: number, patch: Partial<Experience>) =>
    setProfile({
      ...profile,
      experience: profile.experience.map((x, j) => (j === i ? { ...x, ...patch } : x)),
    });

  const setSkill = (i: number, patch: Partial<SkillGroup>) =>
    setProfile({
      ...profile,
      skills: profile.skills.map((g, j) => (j === i ? { ...g, ...patch } : g)),
    });

  async function onSave() {
    setStatus("Saving…");
    const ok = await putProfile(profile!);
    setStatus(ok ? "Saved ✓" : "Save failed — is `job-sentinel serve` running?");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-5 py-12">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-ink">Edit profile</h1>
        <div className="flex items-center gap-3">
          {status && <span className="text-sm text-muted">{status}</span>}
          <Button onClick={onSave}>Save</Button>
        </div>
      </header>

      <section className="space-y-3">
        <CardTitle>Basics</CardTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input placeholder="Name" value={profile.basics.name} onChange={(e) => setBasics("name", e.target.value)} />
          <Input placeholder="Headline" value={profile.basics.headline} onChange={(e) => setBasics("headline", e.target.value)} />
          <Input placeholder="Email" value={profile.basics.email} onChange={(e) => setBasics("email", e.target.value)} />
          <Input placeholder="Phone" value={profile.basics.phone} onChange={(e) => setBasics("phone", e.target.value)} />
          <Input placeholder="Location" value={profile.basics.location} onChange={(e) => setBasics("location", e.target.value)} />
        </div>
        <Textarea
          rows={3}
          placeholder="Summary"
          value={profile.basics.summary}
          onChange={(e) => setBasics("summary", e.target.value)}
        />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <CardTitle>Experience</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setProfile({ ...profile, experience: [...profile.experience, { ...EMPTY_EXP }] })}
          >
            + Add
          </Button>
        </div>
        {profile.experience.map((x, i) => (
          <Card key={i} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input placeholder="Role" value={x.role} onChange={(e) => setExp(i, { role: e.target.value })} />
              <Input placeholder="Company" value={x.company} onChange={(e) => setExp(i, { company: e.target.value })} />
              <Input placeholder="Start" value={x.start} onChange={(e) => setExp(i, { start: e.target.value })} />
              <Input placeholder="End" value={x.end} onChange={(e) => setExp(i, { end: e.target.value })} />
            </div>
            <Textarea
              rows={3}
              placeholder="One bullet per line"
              value={x.bullets.join("\n")}
              onChange={(e) => setExp(i, { bullets: e.target.value.split("\n").filter(Boolean) })}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setProfile({ ...profile, experience: profile.experience.filter((_, j) => j !== i) })}
            >
              Remove
            </Button>
          </Card>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <CardTitle>Skills</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setProfile({ ...profile, skills: [...profile.skills, { category: "", skills: [] }] })}
          >
            + Add group
          </Button>
        </div>
        {profile.skills.map((g, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
            <Input placeholder="Category" value={g.category} onChange={(e) => setSkill(i, { category: e.target.value })} />
            <Input
              placeholder="Comma-separated skills"
              value={g.skills.join(", ")}
              onChange={(e) => setSkill(i, { skills: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
            />
            <Button variant="ghost" size="sm" onClick={() => setProfile({ ...profile, skills: profile.skills.filter((_, j) => j !== i) })}>
              ✕
            </Button>
          </div>
        ))}
      </section>

      <CardSub>
        Education, projects, certifications, and awards are preserved on save — edit those in{" "}
        <code>data/profile.yaml</code> for now.
      </CardSub>
    </div>
  );
}
