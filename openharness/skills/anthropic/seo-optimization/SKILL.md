---
name: seo-optimization
description: Optimize web pages for search engines. TRIGGER when the user asks to improve SEO, add meta tags, optimize for search rankings, set up structured data, or improve page discoverability.
---
# SEO Optimization

Optimize web pages for search engine visibility, crawlability, and ranking.

## Steps

1. **Audit the current state** - Review existing meta tags, page structure, and performance.
2. **Fix technical SEO** - Ensure proper HTML structure, meta tags, and crawlability.
3. **Add structured data** - Implement JSON-LD schema markup for rich results.
4. **Optimize content** - Improve headings, URLs, and internal linking.
5. **Verify** - Test with Google's Rich Results Test and validate structured data.

## Technical SEO Essentials

### Meta Tags
```html
<head>
  <!-- Title: 50-60 characters, primary keyword near the front -->
  <title>Best Running Shoes for Beginners | ShoeStore</title>

  <!-- Description: 150-160 characters, compelling with call to action -->
  <meta name="description" content="Find the perfect running shoes for beginners. Compare comfort, support, and price across top brands. Free shipping on orders over $50.">

  <!-- Canonical URL (prevents duplicate content) -->
  <link rel="canonical" href="https://www.example.com/running-shoes/beginners">

  <!-- Open Graph (social sharing) -->
  <meta property="og:title" content="Best Running Shoes for Beginners">
  <meta property="og:description" content="Find the perfect running shoes for beginners.">
  <meta property="og:image" content="https://www.example.com/images/running-shoes.jpg">
  <meta property="og:url" content="https://www.example.com/running-shoes/beginners">
  <meta property="og:type" content="article">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Best Running Shoes for Beginners">
  <meta name="twitter:description" content="Find the perfect running shoes for beginners.">
  <meta name="twitter:image" content="https://www.example.com/images/running-shoes.jpg">

  <!-- Viewport for mobile -->
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <!-- Language -->
  <html lang="en">

  <!-- Robots directive -->
  <meta name="robots" content="index, follow">
</head>
```

### Structured Data (JSON-LD)
```html
<!-- Article -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Best Running Shoes for Beginners",
  "author": {
    "@type": "Person",
    "name": "Jane Doe"
  },
  "datePublished": "2025-01-15",
  "dateModified": "2025-03-01",
  "image": "https://www.example.com/images/running-shoes.jpg",
  "publisher": {
    "@type": "Organization",
    "name": "ShoeStore",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.example.com/logo.png"
    }
  }
}
</script>

<!-- Product -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Ultra Runner Pro",
  "image": "https://www.example.com/images/ultra-runner.jpg",
  "description": "Lightweight running shoe for beginners",
  "brand": { "@type": "Brand", "name": "RunFast" },
  "offers": {
    "@type": "Offer",
    "price": "89.99",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.5",
    "reviewCount": "127"
  }
}
</script>

<!-- FAQ -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What makes a good running shoe for beginners?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Good beginner running shoes provide cushioning, stability, and a comfortable fit."
      }
    }
  ]
}
</script>
```

### Sitemap
```xml
<!-- public/sitemap.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.example.com/</loc>
    <lastmod>2025-03-01</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.example.com/running-shoes/beginners</loc>
    <lastmod>2025-03-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

### Robots.txt
```
# public/robots.txt
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /private/

Sitemap: https://www.example.com/sitemap.xml
```

## Page Structure

```html
<!-- One H1 per page -->
<h1>Best Running Shoes for Beginners in 2025</h1>

<!-- Logical heading hierarchy -->
<h2>Top Picks</h2>
  <h3>Ultra Runner Pro</h3>
  <h3>ComfortStride 500</h3>
<h2>Buying Guide</h2>
  <h3>Cushioning Types</h3>
  <h3>Sizing Tips</h3>

<!-- Descriptive URLs -->
<!-- BAD: /page?id=123 -->
<!-- GOOD: /running-shoes/beginners -->

<!-- Image optimization -->
<img
  src="shoes.webp"
  alt="Blue Ultra Runner Pro running shoes side view"
  width="800"
  height="600"
  loading="lazy"
>
```

## Performance (Core Web Vitals)

```html
<!-- Preload critical resources -->
<link rel="preload" href="/fonts/main.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/css/critical.css" as="style">

<!-- Lazy load below-the-fold images -->
<img src="product.webp" loading="lazy" alt="Product photo">

<!-- Use modern image formats -->
<picture>
  <source srcset="image.avif" type="image/avif">
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="Description">
</picture>
```

## Rules

- Every page must have a unique title and meta description
- Use one H1 per page with the primary keyword
- All images must have descriptive alt text
- URLs should be descriptive, lowercase, and use hyphens
- Ensure the site is mobile-friendly and passes Core Web Vitals
- Validate structured data with Google's Rich Results Test
- Do not stuff keywords -- write naturally for humans
- Add canonical tags to prevent duplicate content issues
- Submit sitemap to Google Search Console after deployment
