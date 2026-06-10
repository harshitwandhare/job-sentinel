export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-12" aria-busy="true" aria-label="Loading">
      <div className="h-8 w-1/3 animate-pulse rounded bg-stone-200" />
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-24 animate-pulse rounded-xl bg-stone-100" />
      ))}
    </div>
  );
}
