import { Link } from "react-router-dom"

/* Last updated — keep in sync with extension/PRIVACY.md */
const UPDATED = "July 11, 2026"

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="text-xl font-bold mb-3">{title}</h2>
      <div className="space-y-3 text-sm text-muted-foreground leading-relaxed">{children}</div>
    </section>
  )
}

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background pt-28 px-4 md:px-12 lg:px-20 text-foreground pb-20">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-3">
            Privacy <span className="text-primary">Policy</span>
          </h1>
          <p className="text-muted-foreground text-sm">Last updated: {UPDATED}</p>
        </div>

        <Section title="Overview">
          <p>
            VerifAI helps you fact-check text and detect misinformation and scams. This policy
            explains what data the VerifAI website and the VerifAI browser extension collect, why,
            and what we do with it. In short: we only process the text you explicitly submit for
            verification, and we never sell your data or track your browsing.
          </p>
        </Section>

        <Section title="What we collect">
          <p>
            <strong className="text-foreground">Text you submit.</strong> When you run a check — by
            pasting text, submitting a URL, uploading audio, or (in the extension) selecting text and
            choosing “Check with VerifAI” — that content is sent to the VerifAI API so it can be
            verified. Nothing is sent until you start a check.
          </p>
          <p>
            <strong className="text-foreground">Account data (website only).</strong> If you sign in
            with Google OAuth, we store your basic profile (name, email) to maintain your account and
            history. The extension does not require an account.
          </p>
          <p>
            <strong className="text-foreground">What we do NOT collect.</strong> We do not collect
            your browsing history, the pages you visit, keystrokes, cookies for advertising,
            fingerprints, location, or any special-category personal data. The extension reads only
            the text you actively select or paste.
          </p>
        </Section>

        <Section title="How your submitted text is used">
          <p>
            Submitted text is analyzed to produce a verdict (real/fake), a confidence score, and
            supporting evidence. Verified claims may be cached to speed up repeat checks, and public
            claims may be published as indexable claim pages with their evidence. Please do not submit
            private or sensitive personal information for verification.
          </p>
        </Section>

        <Section title="The browser extension">
          <p>
            The extension is a thin client over the same VerifAI service. It requests only the
            permissions it needs:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong className="text-foreground">Context menu</strong> — to add the “Check with VerifAI” right-click item.</li>
            <li><strong className="text-foreground">Active tab &amp; scripting</strong> — to show the verdict card on the page you’re viewing, only after you invoke a check.</li>
            <li><strong className="text-foreground">Access to the VerifAI API host</strong> — to send your check and receive the result.</li>
          </ul>
          <p>
            The extension stores nothing on your device beyond its configuration, uses no analytics or
            trackers, and transmits data only when you trigger a check.
          </p>
        </Section>

        <Section title="Data sharing and retention">
          <p>
            We do not sell your data or share it with third parties for advertising. Verification is
            powered by third-party services (a hosted LLM and a news-search API) that receive the
            submitted text solely to return a result. Account and history data persist until you
            delete your account or request removal.
          </p>
        </Section>

        <Section title="Contact">
          <p>
            Questions about this policy: VerifAI, built by Koushal Ray. Learn more{" "}
            <Link to="/about" className="text-primary hover:underline">about VerifAI</Link>, or open
            an issue on the project repository.
          </p>
        </Section>

        <div className="pt-4 border-t border-border text-xs text-muted-foreground">
          🔍 Verified by VerifAI
        </div>
      </div>
    </div>
  )
}
