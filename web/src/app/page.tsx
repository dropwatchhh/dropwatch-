import { Nav, PromoBanner } from "@/components/marketing/Header";
import { Hero } from "@/components/marketing/Hero";
import { ClosingCta, Compare, Faq, Features, Footer, Mobile, Steps, Testimonial } from "@/components/marketing/Sections";

export default function Home() {
  return (
    <>
      <PromoBanner />
      <Nav />
      <main>
        <Hero />
        <Features />
        <Steps />
        <Compare />
        <Mobile />
        <Testimonial />
        <Faq />
        <ClosingCta />
      </main>
      <Footer />
    </>
  );
}
