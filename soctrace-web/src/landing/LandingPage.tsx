import { enabledSections } from "@/landing/config/sections";
import {
  heroHighlights,
  heroStats,
  navItems,
} from "@/landing/data/content";
import { Footer } from "@/landing/sections/Footer";
import { HeroSection } from "@/landing/sections/HeroSection";
import { Navbar } from "@/landing/sections/Navbar";

export function LandingPage() {
  return (
    <div className="landing-shell">
      {enabledSections.navbar ? <Navbar items={navItems} /> : null}

      <main>
        {enabledSections.hero ? (
          <HeroSection stats={heroStats} highlights={heroHighlights} />
        ) : null}
      </main>

      {enabledSections.footer ? <Footer /> : null}
    </div>
  );
}
