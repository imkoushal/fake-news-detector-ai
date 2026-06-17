export function AccuracySection() {
  return (
    <section id="accuracy" className="bg-hero-bg py-24 px-8 lg:px-16 text-center">
      <div className="text-primary text-[clamp(4rem,12vw,8rem)] font-bold leading-none mb-2">
        96.46%
      </div>
      <div className="text-muted-foreground text-xl mb-4 font-medium">
        Classification accuracy
      </div>
      <p className="text-muted-foreground/60 text-sm max-w-md mx-auto">
        Across 157,000+ real-world articles using a 5-model ensemble with TF-IDF vectorization
      </p>
    </section>
  )
}
