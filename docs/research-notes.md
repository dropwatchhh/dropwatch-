# Research notes: reference site (options-analytics SaaS)

Reference: tradeecho.com. Pages read: `/`, `/pricing`, `/faq` (all HTTP 200). Not read: `/features/*`, `/compare/*`, `/about`, `/docs`.
Notes are paraphrased structure only. No branding, copy or imagery is to be reused. Competitor prices and marketing claims on the reference are self-reported and unverified.

## Page sections (home, in order)
1. Seasonal promo banner linking to pricing
2. Header nav
3. Hero: two-line headline, subhead, two CTAs, trust line (trader count, exchange coverage, cancel anytime), demo-video link, ticker strip (SPX, NDX, SPY, QQQ, RUT, VIX), big heatmap screenshot
4. Platform: grid of module cards (image, title, blurb, "Learn more")
5. "The math": current stack of separate tools with prices and total vs one plan
6. Getting started: 3 steps
7. Compare: feature matrix vs 3 competitors across about 10 capabilities (the reference marks itself "Included" everywhere)
8. Mobile: app-store badges, push alerts
9. Members: one testimonial
10. Inline FAQ (about 5 Q&As)
11. Closing CTA
12. Footer

## Feature modules
GEX/dealer-positioning heatmap (key levels, several view modes), ranked setup scanner, options flow with per-print score and tier filters, dark pool levels, algo-trade signal feed with filter channels and per-ticker alerts, charting with positioning overlays and replay, AI agent builder (paper first, rule-bound) plus marketplace, copy trading via the user's own broker with sizing/stop/cap controls. Extras: daily brief, news, journal, AI-assistant (MCP) access, social/competitions.

## Pricing / CTA flow
- Tiers: Free (no card, limited AI chat and brief), Monthly, Yearly, Lifetime. Promo codes shown on cards with a copy button; struck-through list price; "Save X" badge.
- Free CTA goes to register. Paid CTAs go straight to Stripe checkout. Hero/nav "Start free" goes to pricing#free. "Sign in" goes to the app.
- Billing: upgrades instant, downgrades at renewal, cancel anytime.

## Nav
Features (mega-menu), Pricing, Learn (About, Wins, FAQ, Community), Sign in, promo CTA, Start free.

## Footer
Newsletter signup, socials, status line ("all systems operational"), link columns (Product, Compare, Resources, Company, Legal), and a risk/not-advice/not-a-registered-adviser disclaimer.

## Visual style (measured from computed CSS)
- Page background near-black `#0a0a0b`; card surface `#0e0e10`; body text `#ededed`; muted text `#a8a8b0`; accent bright green `#00cf1c`.
- Type: Inter for UI/body (16px; 13 to 15px for buttons and labels, weight 500 to 600); a serif display face (Newsreader) for H1 (72px) and H2 (48px) at weight 400. Mixing a serif display with a sans UI is the signature.
- Buttons: pill-shaped (999px radius) with a 1px translucent white border (`rgba(255,255,255,.22)`) for secondary; small 6px radius for nav-style buttons; green text for small accent links.
- Cards: dark surface, hairline border, modest radius. Pricing cards carry badge, struck price, promo chip, bullet list.
- Tables: text cells ("Included" / "Not included"), price in column header.
- Patterns: two-line section headings (bold lead, contrasting second line), large product screenshots in cards, generous vertical spacing.

## Takeaways for our build (original, not copied)
Keep: section order, module set, cost-stack comparison, 3-step flow, matrix, FAQ, free-vs-Pro pricing, serif-plus-sans dark look.
Change: all names, copy, palette accent (pick our own), logo, imagery (we draw our own mock UI in code).
