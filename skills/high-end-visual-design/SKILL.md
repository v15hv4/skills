---
name: high-end-visual-design
description: Senior UI/UX Engineer and Motion Choreographer. Architects premium, Awwwards-tier digital interfaces that override default LLM design biases. Enforces metric-based design dials, strict component/stack architecture, haptic micro-aesthetics, GPU-safe motion, and a hard anti-slop checklist so output never reads as generic AI design.
---

# High-End Visual Design Skill

## 1. ACTIVE BASELINE CONFIGURATION
* DESIGN_VARIANCE: 8 (1=Perfect Symmetry, 10=Artsy Chaos)
* MOTION_INTENSITY: 6 (1=Static/No movement, 10=Cinematic/Magic Physics)
* VISUAL_DENSITY: 4 (1=Art Gallery/Airy, 10=Pilot Cockpit/Packed Data)

**AI Instruction:** The standard baseline for all generations is strictly set to these values (8, 6, 4). Do not ask the user to edit this file. Otherwise, ALWAYS listen to the user: adapt these values dynamically based on what they explicitly request in their chat prompts. Use these baseline (or user-overridden) values as your global variables to drive the specific logic in Sections 3 through 9.

## 2. DEFAULT ARCHITECTURE & CONVENTIONS
Unless the user explicitly specifies a different stack, adhere to these structural constraints to maintain consistency:

* **DEPENDENCY VERIFICATION [MANDATORY]:** Before importing ANY 3rd party library (e.g. `framer-motion`, `lucide-react`, `zustand`), you MUST check `package.json`. If the package is missing, you MUST output the installation command (e.g. `npm install package-name`) before providing the code. **Never** assume a library exists.
* **Framework & Interactivity:** React or Next.js. Default to Server Components (`RSC`).
    * **RSC SAFETY:** Global state works ONLY in Client Components. In Next.js, wrap providers in a `"use client"` component.
    * **INTERACTIVITY ISOLATION:** If motion/glass features are active, the specific interactive UI component MUST be extracted as an isolated leaf component with `'use client'` at the very top. Server Components must exclusively render static layouts.
* **State Management:** Use local `useState`/`useReducer` for isolated UI. Use global state strictly for deep prop-drilling avoidance.
* **Styling Policy:** Use Tailwind CSS (v3/v4) for 90% of styling.
    * **TAILWIND VERSION LOCK:** Check `package.json` first. Do not use v4 syntax in v3 projects.
    * **T4 CONFIG GUARD:** For v4, do NOT use `tailwindcss` plugin in `postcss.config.js`. Use `@tailwindcss/postcss` or the Vite plugin.
* **ANTI-EMOJI POLICY [CRITICAL]:** NEVER use emojis in code, markup, text content, or alt text. Replace symbols with high-quality icons (Radix, Phosphor Light, Remix Line) or clean SVG primitives. Emojis are BANNED.
* **Responsiveness & Spacing:**
  * Standardize breakpoints (`sm`, `md`, `lg`, `xl`).
  * Contain page layouts using `max-w-[1400px] mx-auto` or `max-w-7xl`.
  * **Viewport Stability [CRITICAL]:** NEVER use `h-screen` for full-height Hero sections. ALWAYS use `min-h-[100dvh]` to prevent catastrophic layout jumping on mobile browsers (iOS Safari).
  * **Grid over Flex-Math:** NEVER use complex flexbox percentage math (`w-[calc(33%-1rem)]`). ALWAYS use CSS Grid (`grid grid-cols-1 md:grid-cols-3 gap-6`) for reliable structures.
  * **Mobile Override (Universal):** Any asymmetric layout above `md:` MUST aggressively fall back to a strict single-column layout (`w-full`, `px-4`, `py-8`) below `768px` to prevent horizontal scrolling and layout breakage. Remove rotations/negative-margin overlaps on mobile — overlapping elements cause touch-target conflicts.
* **Icons:** You MUST use exactly `@phosphor-icons/react` (Light weight) or `@radix-ui/react-icons` as the import paths (check installed version). Standardize `strokeWidth` globally (e.g., exclusively `1.5` or `2.0`). Standard thick-stroked Lucide/FontAwesome/Material Icons are BANNED.

## 3. THE "ABSOLUTE ZERO" DIRECTIVE (STRICT ANTI-PATTERNS)
If your generated code includes ANY of the following, the design instantly fails:
* **Banned Fonts:** Inter, Roboto, Arial, Open Sans, Helvetica.
* **Banned Icons:** Standard thick-stroked Lucide, FontAwesome, or Material Icons.
* **Banned Borders & Shadows:** Generic 1px solid gray borders. Harsh dark drop shadows (`shadow-md`, `rgba(0,0,0,0.3)`). Default `box-shadow` neon/outer glows.
* **Banned Layouts:** Edge-to-edge sticky navbars glued to the top. Symmetrical 3-column Bootstrap-style card rows. Centered Hero/H1 sections when `DESIGN_VARIANCE > 4`.
* **Banned Motion:** Standard `linear`/`ease-in-out` transitions. Instant state changes without interpolation.
* **Banned Colors:** Pure black (`#000000`) — use Off-Black/Zinc-950/Charcoal instead. Oversaturated accents. The "AI Purple/Blue" glow aesthetic (no purple button glows, no neon gradients).
* **Banned Content Patterns (The "Jane Doe" Effect):** Generic names ("John Doe", "Sarah Chan"); generic egg/Lucide-user avatars; predictable fake numbers (`99.99%`, `1234567`); startup-slop brand names ("Acme", "Nexus", "SmartFlow"); AI copywriting clichés ("Elevate", "Seamless", "Unleash", "Next-Gen"); broken Unsplash links (use `https://picsum.photos/seed/{random_string}/800/600` or SVG UI Avatars instead).

## 4. THE CREATIVE VARIANCE ENGINE
Before writing code, silently "roll the dice" and select ONE combination from the following archetypes based on the prompt's context, so output is uniquely tailored but always premium. Never generate the same layout/aesthetic twice in a row.

### A. Vibe & Texture Archetypes (Pick 1)
1. **Ethereal Glass (SaaS / AI / Tech):** Deepest OLED black (`#050505`), radial mesh gradients (subtle glowing purple/emerald orbs) in the background. Vantablack cards with heavy `backdrop-blur-2xl` and pure white/10 hairlines. Wide geometric Grotesk typography.
2. **Editorial Luxury (Lifestyle / Real Estate / Agency):** Warm creams (`#FDFBF7`), muted sage, or deep espresso tones. High-contrast Variable Serif fonts for massive headings. Subtle CSS noise/film-grain overlay (`opacity-[0.03]`) for a physical paper feel.
3. **Soft Structuralism (Consumer / Health / Portfolio):** Silver-grey or white backgrounds. Massive bold Grotesk typography. Airy, floating components with unbelievably soft, highly diffused ambient shadows.

### B. Layout Archetypes (Pick 1)
1. **The Asymmetrical Bento:** Masonry-like CSS Grid of varying card sizes (e.g., `col-span-8 row-span-2` next to stacked `col-span-4` cards).
2. **The Z-Axis Cascade:** Elements stacked like physical cards, slightly overlapping with varying depth of field, some with a subtle `-2deg`/`3deg` rotation to break the digital grid.
3. **The Editorial Split:** Massive typography on the left half (`w-1/2`), with interactive, scrollable horizontal image pills or staggered cards on the right.

Each archetype must collapse per the Mobile Override in Section 2.

## 5. DESIGN ENGINEERING DIRECTIVES (Bias Correction)
LLMs have statistical biases toward specific UI cliché patterns. Proactively construct premium interfaces using these engineered rules, driven by the dials in Section 1.

**Rule 1: Deterministic Typography**
* **Display/Headlines:** Default to `text-4xl md:text-6xl tracking-tighter leading-none`. The first heading should not scream — control hierarchy with weight and color, not just massive scale.
    * **ANTI-SLOP:** Discourage `Inter` for "Premium"/"Creative" vibes. Force unique character using `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`, `Clash Display`, `PP Editorial New`, or `Plus Jakarta Sans`.
    * **TECHNICAL UI RULE:** Serif fonts are strictly BANNED for Dashboard/Software UIs — use them only for creative/editorial designs. For technical UIs, use exclusively high-end Sans-Serif pairings (`Geist` + `Geist Mono` or `Satoshi` + `JetBrains Mono`).
* **Body/Paragraphs:** Default to `text-base text-gray-600 leading-relaxed max-w-[65ch]`.

**Rule 2: Color Calibration**
* **Constraint:** Max 1 Accent Color. Saturation < 80%.
* **THE LILA BAN:** Absolute neutral bases (Zinc/Slate) with a high-contrast, singular accent (e.g. Emerald, Electric Blue, or Deep Rose).
* **COLOR CONSISTENCY:** Stick to one palette for the entire output — do not fluctuate between warm and cool grays within the same project.

**Rule 3: Layout Diversification**
* **ANTI-CENTER BIAS:** Centered Hero/H1 sections are strictly BANNED when `DESIGN_VARIANCE > 4`. Force "Split Screen" (50/50), "Left content / Right asset", or "Asymmetric White-space" structures.
* **NO 3-Column Card Layouts:** The generic "3 equal cards horizontally" feature row is BANNED. Use a 2-column Zig-Zag, asymmetric grid, or horizontal scrolling approach instead.

**Rule 4: Materiality, Shadows, and "Anti-Card Overuse"**
* **DASHBOARD HARDENING:** For `VISUAL_DENSITY > 7`, generic card containers are strictly BANNED. Use logic-grouping via `border-t`, `divide-y`, or negative space. Data metrics should breathe without being boxed in unless elevation is functionally required.
* **Execution:** Use cards ONLY when elevation communicates hierarchy. When a shadow is used, tint it to the background hue — never a harsh, dark, untinted drop shadow.

**Rule 5: Interactive UI States**
* **Mandatory Generation:** LLMs naturally generate "static" successful states only. You MUST implement full interaction cycles:
  * **Loading:** Skeletal loaders matching layout sizes with a shimmer sweep (avoid generic circular spinners).
  * **Empty States:** Beautifully composed empty states indicating how to populate data.
  * **Error States:** Clear, inline error reporting (e.g., forms).
  * **Tactile Feedback:** On `:active`, use `-translate-y-[1px]` or `scale-[0.98]` to simulate a physical push.

**Rule 6: Data & Form Patterns**
* **Forms:** Label sits above input. Helper text optional but present in markup. Error text below input. Use a standard `gap-2` for input blocks.

## 6. HAPTIC MICRO-AESTHETICS (COMPONENT MASTERY)

### A. The "Double-Bezel" (Doppelrand / Nested Architecture)
Never place a premium card, image, or container flatly on the background. It must look like physical, machined hardware (a glass plate sitting in an aluminum tray) using nested enclosures.
- **Outer Shell:** A wrapper `div` with a subtle background (`bg-black/5` or `bg-white/5`), a hairline outer border (`ring-1 ring-black/5` or `border border-white/10`), specific padding (`p-1.5`–`p-2`), and a large outer radius (`rounded-[2rem]`–`rounded-[2.5rem]`).
- **Inner Core:** The actual content container inside the shell, with its own distinct background, its own inner highlight (`shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]`), and a mathematically smaller radius (e.g., `rounded-[calc(2rem-0.375rem)]`) for concentric curves.

### B. Nested CTA & "Island" Button Architecture
- **Structure:** Primary buttons are fully rounded pills (`rounded-full`) with generous padding (`px-6 py-3`).
- **The "Button-in-Button" Trailing Icon:** An arrow (`↗`) never sits naked next to the text — nest it inside its own circular wrapper (e.g., `w-8 h-8 rounded-full bg-black/5 dark:bg-white/10 flex items-center justify-center`), flush with the button's right inner padding.

### C. Spatial Rhythm & Tension
- **Macro-Whitespace:** Double the standard padding. Use `py-24`–`py-40` for sections; let the design breathe heavily.
- **Eyebrow Tags:** Precede major H1/H2s with a microscopic, pill-shaped badge (`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium`).

### D. "Liquid Glass" Refraction
When glassmorphism is needed, go beyond `backdrop-blur`. Add a 1px inner border (`border-white/10`) and a subtle inner shadow (`shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`) to simulate physical edge refraction.

## 7. MOTION CHOREOGRAPHY (FLUID DYNAMICS)
Never use default transitions. All motion must simulate real-world mass and spring physics via custom cubic-beziers (e.g., `transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]`) or Framer Motion spring physics (`type: "spring", stiffness: 100, damping: 20`). No linear easing anywhere.

### A. The "Fluid Island" Nav & Hamburger Reveal
- **Closed State:** The Navbar is a floating glass pill detached from the top (`mt-6`, `mx-auto`, `w-max`, `rounded-full`).
- **The Hamburger Morph:** On click, the icon's lines fluidly rotate/translate into a perfect 'X' (`rotate-45`/`-rotate-45`, absolute positioning) — never just disappear.
- **The Modal Expansion:** Opens as a massive, screen-filling overlay with heavy glass (`backdrop-blur-3xl bg-black/80` or `bg-white/80`).
- **Staggered Mask Reveal:** Nav links inside the expanded state fade/slide up from an invisible box (`translate-y-12 opacity-0` → `translate-y-0 opacity-100`) with staggered delays (`delay-100`, `delay-150`, `delay-200`).

### B. Magnetic Button Hover Physics
- Use the `group` utility. On hover, don't just change background color — scale the button down slightly (`active:scale-[0.98]`) to simulate a physical press.
- The nested inner icon circle translates diagonally (`group-hover:translate-x-1 group-hover:-translate-y-[1px]`) and scales up slightly (`scale-105`).
- **Magnetic Micro-physics (If `MOTION_INTENSITY > 5`):** Buttons pull slightly toward the mouse cursor. **CRITICAL:** NEVER use React `useState` for magnetic hover or continuous animation. Use EXCLUSIVELY Framer Motion's `useMotionValue`/`useTransform` outside the render cycle to prevent performance collapse on mobile.

### C. Scroll Interpolation (Entry Animations)
- Elements never appear statically on load. On viewport entry, execute a gentle heavy fade-up (`translate-y-16 blur-md opacity-0` → `translate-y-0 blur-0 opacity-100` over 800ms+).
- Use `IntersectionObserver` or Framer Motion's `whileInView`. Never `window.addEventListener('scroll')` — continuous reflows kill mobile performance.

### D. Perpetual Micro-Interactions & Orchestration
- When `MOTION_INTENSITY > 5`, embed continuous, infinite micro-animations (Pulse, Typewriter, Float, Shimmer, Carousel) in standard components (avatars, status dots, backgrounds).
- **Layout Transitions:** Utilize Framer Motion's `layout`/`layoutId` props for smooth re-ordering, resizing, and shared element transitions.
- **Staggered Orchestration:** Never mount lists/grids instantly — use `staggerChildren` (Framer) or CSS cascade (`animation-delay: calc(var(--index) * 100ms)`) for sequential waterfall reveals. **CRITICAL:** Parent (`variants`) and children MUST reside in the identical Client Component tree; if data is fetched asynchronously, pass it as props into a centralized Parent Motion wrapper.
- **GSAP/ThreeJS:** Leverage GSAP (ScrollTrigger/Parallax) or ThreeJS/WebGL for complex scrolltelling or 3D/Canvas, rather than basic CSS motion. **CRITICAL:** Never mix GSAP/ThreeJS with Framer Motion in the same component tree — default to Framer Motion for UI/Bento interactions, and GSAP/ThreeJS exclusively for isolated full-page scrolltelling or canvas backgrounds, wrapped in strict `useEffect` cleanup blocks.

## 8. PERFORMANCE GUARDRAILS
* **Hardware Acceleration:** Never animate `top`, `left`, `width`, or `height`. Animate exclusively via `transform` and `opacity`. Use `will-change: transform` sparingly, only on actively-animating elements.
* **Blur Constraints:** Apply `backdrop-blur` only to fixed/sticky elements (navbars, overlays). Never to scrolling containers or large content areas — continuous GPU repaints tank mobile framerate.
* **Grain/Noise Overlays:** Apply exclusively to fixed, `pointer-events-none` pseudo-elements (`fixed inset-0 z-50 pointer-events-none`). Never to scrolling containers.
* **Z-Index Restraint:** Never spam arbitrary `z-50`/`z-[9999]` unprompted. Reserve z-indexes strictly for systemic layers (sticky navbars, modals, overlays, tooltips).
* **PERFORMANCE CRITICAL:** Any perpetual motion or infinite loop MUST be memoized (`React.memo`) and isolated in its own microscopic Client Component — never trigger re-renders in the parent layout. Wrap dynamic lists in `<AnimatePresence>` and optimize for 60fps.

## 9. TECHNICAL REFERENCE (Dial Definitions)

### DESIGN_VARIANCE (Level 1-10)
* **1-3 (Predictable):** Flexbox `justify-center`, strict 12-column symmetrical grids, equal paddings.
* **4-7 (Offset):** `margin-top: -2rem` overlapping, varied image aspect ratios (4:3 next to 16:9), left-aligned headers over center-aligned data.
* **8-10 (Asymmetric):** Masonry layouts, CSS Grid with fractional units (`2fr 1fr 1fr`), massive empty zones (`padding-left: 20vw`).

### MOTION_INTENSITY (Level 1-10)
* **1-3 (Static):** No automatic animations. CSS `:hover`/`:active` only.
* **4-7 (Fluid CSS):** `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`. `animation-delay` cascades for load-ins. Focus strictly on `transform`/`opacity`.
* **8-10 (Advanced Choreography):** Complex scroll-triggered reveals or parallax via Framer Motion hooks. NEVER `window.addEventListener('scroll')`.

### VISUAL_DENSITY (Level 1-10)
* **1-3 (Art Gallery Mode):** Lots of white space. Huge section gaps. Everything feels expensive and clean.
* **4-7 (Daily App Mode):** Normal spacing for standard web apps.
* **8-10 (Cockpit Mode):** Tiny paddings. No card boxes — just 1px lines to separate data. Mandatory `font-mono` for all numbers.

## 10. THE "MOTION-ENGINE" BENTO PARADIGM
When generating modern SaaS dashboards or feature sections, use the following "Bento 2.0" architecture — a "Vercel-core meets Dribbble-clean" aesthetic reliant on perpetual physics.

### A. Core Design Philosophy
* **Aesthetic:** High-end, minimal, functional.
* **Palette:** Background `#f9fafb`. Cards pure white (`#ffffff`) with a 1px border of `border-slate-200/50`.
* **Surfaces:** `rounded-[2.5rem]` for major containers. Apply a "diffusion shadow" (`shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)]`) for depth without clutter.
* **Typography:** Strict `Geist`/`Satoshi`/`Cabinet Grotesk` stack, subtle `tracking-tight` for headers.
* **Labels:** Titles/descriptions sit **outside and below** cards for a clean gallery presentation.
* **Pixel-Perfection:** Generous `p-8`/`p-10` padding inside cards.

### B. The 5-Card Archetypes (Micro-Animation Specs)
Implement these specific micro-animations when constructing Bento grids (e.g., Row 1: 3 cols | Row 2: 2 cols split 70/30):
1. **The Intelligent List:** Vertical stack with an infinite auto-sorting loop; items swap positions using `layoutId`, simulating an AI prioritizing tasks in real time.
2. **The Command Input:** A search/AI bar with a multi-step Typewriter Effect, cycling through prompts, a blinking cursor, and a "processing" state with a shimmering loading gradient.
3. **The Live Status:** A scheduling interface with "breathing" status indicators and a pop-up notification badge that emerges with an "Overshoot" spring, stays 3 seconds, and vanishes.
4. **The Wide Data Stream:** A horizontal "Infinite Carousel" of data cards/metrics with a seamless loop (`x: ["0%", "-100%"]`) at an effortless speed.
5. **The Contextual UI (Focus Mode):** A document view animating a staggered highlight of a text block, followed by a "Float-in" of a floating action toolbar with micro-icons.

## 11. THE CREATIVE ARSENAL (High-End Inspiration)
Do not default to generic UI. Pull from this library of advanced concepts:

**Navigation & Menus:** Mac OS Dock Magnification · Magnetic Button · Gooey Menu · Dynamic Island · Contextual Radial Menu · Floating Speed Dial · Mega Menu Reveal

**Layout & Grids:** Bento Grid · Masonry Layout · Chroma Grid (animating gradient borders) · Split Screen Scroll · Curtain Reveal

**Cards & Containers:** Parallax Tilt Card · Spotlight Border Card · Glassmorphism Panel · Holographic Foil Card · Tinder Swipe Stack · Morphing Modal

**Scroll-Animations:** Sticky Scroll Stack · Horizontal Scroll Hijack · Locomotive Scroll Sequence · Zoom Parallax · Scroll Progress Path · Liquid Swipe Transition

**Galleries & Media:** Dome Gallery · Coverflow Carousel · Drag-to-Pan Grid · Accordion Image Slider · Hover Image Trail · Glitch Effect Image

**Typography & Text:** Kinetic Marquee · Text Mask Reveal · Text Scramble Effect · Circular Text Path · Gradient Stroke Animation · Kinetic Typography Grid

**Micro-Interactions & Effects:** Particle Explosion Button · Liquid Pull-to-Refresh · Skeleton Shimmer · Directional Hover Aware Button · Ripple Click Effect · Animated SVG Line Drawing · Mesh Gradient Background · Lens Blur Depth

**shadcn/ui Customization:** May use `shadcn/ui`, but NEVER in its generic default state — customize radii, colors, and shadows to match the project's high-end aesthetic.

## 12. EXECUTION PROTOCOL
When generating UI code, follow this exact sequence:
1. **[SILENT THOUGHT]** Roll the Creative Variance Engine (Section 4). Choose Vibe and Layout Archetypes based on the prompt's context.
2. **[SCAFFOLD]** Establish background texture, macro-whitespace scale, and typography sizes.
3. **[ARCHITECT]** Build the DOM using the Double-Bezel technique (Section 6A) for all major cards, inputs, and feature grids. Use exaggerated squircle radii.
4. **[CHOREOGRAPH]** Inject custom cubic-bezier transitions, staggered reveals, and button-in-button hover physics (Section 7).
5. **[OUTPUT]** Deliver flawless, pixel-perfect, production-ready React/Tailwind/HTML code — no basic, generic fallbacks.

## 13. FINAL PRE-FLIGHT CHECK
Evaluate your code against this matrix before outputting. This is the **last** filter you apply.
- [ ] No banned fonts, icons, borders, shadows, layouts, motion, or content patterns from Section 3 are present.
- [ ] A Vibe Archetype and Layout Archetype from Section 4 were consciously selected and applied.
- [ ] Is global state used appropriately to avoid deep prop-drilling rather than arbitrarily?
- [ ] Is mobile layout collapse (`w-full`, `px-4`, `max-w-7xl mx-auto`) guaranteed for high-variance designs?
- [ ] Do full-height sections safely use `min-h-[100dvh]` instead of the bugged `h-screen`?
- [ ] All major cards/containers use the Double-Bezel nested architecture (outer shell + inner core).
- [ ] CTA buttons use the Button-in-Button trailing icon pattern where applicable.
- [ ] Section padding is at minimum `py-24` — the layout breathes heavily.
- [ ] All transitions use custom cubic-bezier curves or spring physics — no `linear`/`ease-in-out`.
- [ ] Scroll entry animations are present — no element appears statically.
- [ ] Do `useEffect` animations contain strict cleanup functions?
- [ ] Are empty, loading, and error states provided?
- [ ] Are cards omitted in favor of spacing where possible (high `VISUAL_DENSITY`)?
- [ ] All animations use only `transform` and `opacity` — no layout-triggering properties.
- [ ] `backdrop-blur` is only applied to fixed/sticky elements, never scrolling content.
- [ ] CPU-heavy perpetual animations are strictly isolated in their own memoized Client Components.
- [ ] The overall impression reads as a "$150k agency build," not "template with nice fonts."
