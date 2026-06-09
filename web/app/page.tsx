import { Hero } from "@/components/Hero";
import { Card, CardSub, CardTitle } from "@/components/ui/card";

const features = [
  {
    title: "Monitor",
    body: "Pluggable adapters watch job portals and alert you the moment a posting appears.",
  },
  {
    title: "Track",
    body: "Every posting's lifecycle — new, seen, applied, closed — with deadlines.",
  },
  {
    title: "Tailor",
    body: "Generate an ATS-ready PDF per posting; a local LLM rephrases toward the role.",
  },
];

export default function HomePage() {
  return (
    <>
      <Hero />
      <section className="mx-auto grid max-w-5xl gap-4 px-5 pb-24 sm:grid-cols-3">
        {features.map((f) => (
          <Card key={f.title}>
            <CardTitle>{f.title}</CardTitle>
            <CardSub className="mt-2">{f.body}</CardSub>
          </Card>
        ))}
      </section>
    </>
  );
}
