# AALVINAI TECHNOLOGIES

> **Technology That Moves Business Forward.**

AALVINAI Technologies builds intelligent AI, ERP, CRM and FinTech systems engineered with determination, precision and purpose.

🌐 Live at **[aalvinai.in](https://aalvinai.in)** (GitHub Pages, custom domain via `CNAME`) · ✉️ [hello@aalvinai.in](mailto:hello@aalvinai.in)

---

## 🚀 Key Highlights

- **Ultra-High Performance**: Engineered without heavyweight external frameworks for blazing load times and sub-millisecond interaction responses.
- **Dynamic Viewport Engine**: Custom responsive unit scaling (`--u`, `--uw`, `--h`) designed to deliver pixel-perfect proportion from mobile phones to 4K ultra-wide monitors.
- **Cognitive Intelligence Grid**: Modular AI workflow engine spanning FinTech, Healthcare, Logistics, and Enterprise Automation.
- **Subtle Visual Craft**: Ambient fractal noise overlays, smooth cubic-bezier easing, and glowing glassmorphic elements.
- **Complete Legal & Compliance**: Comprehensive Privacy Policy (`privacy.html`) and Terms of Service (`terms.html`).

---

## 📂 Repository Structure

```
├── index.html              # Home page & responsive design system
├── products.html           # Product catalogue hub (cards/chips/JSON-LD are generated)
├── products/<slug>/        # 30 generated product landing pages
├── 404.html                # Branded not-found page (served by GitHub Pages)
├── privacy.html            # Data privacy, compliance & governance policy
├── terms.html              # Enterprise service terms & mutual obligations
├── _tools/build_products.py  # Product data + page/sitemap generator (not published)
├── sitemap.xml             # Generated — every public page with git-based <lastmod>
├── llms.txt                # Generated — plain-text summary for AI search tools
├── 6bac…1144.txt           # IndexNow ownership key (do not delete)
├── robots.txt              # Crawler rules + sitemap pointer
├── og-image.png            # 1200×630 social share card (Open Graph / Twitter)
├── thiruvalluvar-white.webp  # Heritage figure used on the home page
├── favicon.ico, logo-mark.*  # Icons
└── CNAME                   # GitHub Pages custom domain (aalvinai.in)
```

---

## 🧩 Products & SEO

Product data lives in one place: the `PRODUCTS` list in `_tools/build_products.py`.
To add, edit or retire a product, change that list and run:

```bash
python _tools/build_products.py          # writes products/<slug>/, products.html blocks, sitemap.xml, llms.txt
python _tools/build_products.py --check  # CI-style check: exit 1 if anything generated is stale
```

The script warns if the hand-written counts in `products.html` (hero heading, stats, toolbar)
no longer match. After deploying, notify Bing/Yandex instantly via IndexNow:

```bash
python _tools/build_products.py --indexnow
```

---

## 💻 Local Development

Simply serve with any modern HTTP server or open directly in a browser:

```bash
# Using Python
python -m http.server 3000

# Using Node.js npx serve
npx serve .
```

Navigate to `http://localhost:3000` in your web browser.

---

## 📜 Copyright & License

Copyright © 2026 AALVINAI Technologies. All rights reserved.
