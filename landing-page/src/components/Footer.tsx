export function Footer() {
  return (
    <footer className="bg-background border-t border-border py-8 px-8 lg:px-16 flex flex-col md:flex-row justify-between items-center gap-4">
      <div className="text-foreground text-xl font-semibold tracking-tight">
        VERIF<span className="text-primary">AI</span>
      </div>
      <div className="text-muted-foreground text-sm text-center md:text-right">
        Built by Koushal Kishor Ray · B.Tech CSE · Parul University
      </div>
    </footer>
  )
}
