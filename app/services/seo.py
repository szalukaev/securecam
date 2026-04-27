"""
SEO сервис — автогенерация мета-тегов, sitemap.xml, robots.txt,
микроразметки Schema.org (упор на Яндекс).
"""
from app.config import settings
from typing import Optional
import re


def slugify(text: str) -> str:
    """Транслитерация + slug"""
    tr = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo',
        'ж':'zh','з':'z','и':'i','й':'j','к':'k','л':'l','м':'m',
        'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
        'ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch',
        'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
    }
    text = text.lower()
    result = ''.join(tr.get(c, c) for c in text)
    result = re.sub(r'[^a-z0-9\-]', '-', result)
    result = re.sub(r'-+', '-', result).strip('-')
    return result[:200]


def product_seo(product) -> dict:
    """Генерирует SEO для товара"""
    city = "Екатеринбург"
    name = product.name
    brand = f" {product.brand}" if product.brand else ""
    sku = f" арт. {product.sku}" if product.sku else ""

    title = product.seo_title or f"Купить{brand} {name}{sku} в {city} | {settings.SITE_NAME}"
    desc = product.seo_description or (
        f"{'[' + product.brand + '] ' if product.brand else ''}{name} — "
        f"{product.short_description or 'профессиональное оборудование для видеонаблюдения'}. "
        f"Купить в {city} с доставкой и установкой. "
        f"{'Цена от ' + str(int(product.price)) + ' ₽. ' if product.price else ''}"
        f"Гарантия. Звоните: {settings.SITE_PHONE}"
    )
    return {
        "title": title[:70],
        "description": desc[:160],
        "og_title": title[:70],
        "og_description": desc[:160],
        "canonical": f"{settings.SITE_DOMAIN}/catalog/{product.slug}",
    }


def category_seo(category) -> dict:
    city = "Екатеринбург"
    name = category.name
    title = category.seo_title or f"{name} купить в {city} — цены, фото, доставка | {settings.SITE_NAME}"
    desc = category.seo_description or (
        f"Купить {name.lower()} в {city}. Широкий выбор, официальная гарантия, "
        f"профессиональная установка. {settings.SITE_PHONE}"
    )
    return {
        "title": title[:70],
        "description": desc[:160],
        "canonical": f"{settings.SITE_DOMAIN}/catalog/category/{category.slug}",
    }


def service_seo(service) -> dict:
    city = "Екатеринбург"
    name = service.name
    title = service.seo_title or f"{name} в {city} — стоимость, сроки | {settings.SITE_NAME}"
    price_info = f"от {int(service.price_from)} ₽" if service.price_from else ""
    desc = service.seo_description or (
        f"{name} в {city} {price_info}. "
        f"{service.short_description or 'Профессиональное выполнение, гарантия качества.'}. "
        f"Звоните: {settings.SITE_PHONE}"
    )
    return {
        "title": title[:70],
        "description": desc[:160],
        "canonical": f"{settings.SITE_DOMAIN}/services/{service.slug}",
    }


def blog_seo(post) -> dict:
    title = post.seo_title or f"{post.title} | {settings.SITE_NAME}"
    desc = post.seo_description or post.excerpt or post.title
    return {
        "title": title[:70],
        "description": desc[:160],
        "canonical": f"{settings.SITE_DOMAIN}/blog/{post.slug}",
    }


def product_schema(product) -> dict:
    """Schema.org разметка для товара (JSON-LD) — парсится Яндексом"""
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.short_description or product.description[:200],
        "sku": product.sku,
        "brand": {"@type": "Brand", "name": product.brand or settings.SITE_NAME},
        "offers": {
            "@type": "Offer",
            "priceCurrency": "RUB",
            "price": str(int(product.price)) if product.price else "0",
            "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock",
            "seller": {"@type": "Organization", "name": settings.SITE_NAME},
            "url": f"{settings.SITE_DOMAIN}/catalog/{product.slug}",
        },
    }
    if product.images:
        schema["image"] = [f"{settings.SITE_DOMAIN}{img}" for img in product.images[:3]]
    return schema


def org_schema() -> dict:
    """Schema.org для организации — главная страница"""
    return {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": settings.SITE_NAME,
        "description": settings.SITE_DESCRIPTION,
        "telephone": settings.SITE_PHONE,
        "email": settings.SITE_EMAIL,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Екатеринбург",
            "addressCountry": "RU",
            "streetAddress": settings.SITE_ADDRESS,
        },
        "url": settings.SITE_DOMAIN,
        "areaServed": {"@type": "City", "name": "Екатеринбург"},
        "openingHours": "Mo-Fr 09:00-18:00",
    }


def generate_sitemap(products, categories, services, posts, base_url: str) -> str:
    """Генерация sitemap.xml"""
    urls = [
        {"loc": base_url, "priority": "1.0", "changefreq": "daily"},
        {"loc": f"{base_url}/catalog", "priority": "0.9", "changefreq": "daily"},
        {"loc": f"{base_url}/services", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{base_url}/blog", "priority": "0.8", "changefreq": "weekly"},
        {"loc": f"{base_url}/contacts", "priority": "0.5", "changefreq": "monthly"},
    ]
    for cat in categories:
        urls.append({"loc": f"{base_url}/catalog/category/{cat.slug}", "priority": "0.8", "changefreq": "weekly"})
    for p in products:
        urls.append({"loc": f"{base_url}/catalog/{p.slug}", "priority": "0.7", "changefreq": "weekly"})
    for s in services:
        urls.append({"loc": f"{base_url}/services/{s.slug}", "priority": "0.7", "changefreq": "monthly"})
    for post in posts:
        urls.append({"loc": f"{base_url}/blog/{post.slug}", "priority": "0.6", "changefreq": "monthly"})

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f"""  <url>
    <loc>{u['loc']}</loc>
    <changefreq>{u.get('changefreq','weekly')}</changefreq>
    <priority>{u.get('priority','0.5')}</priority>
  </url>""")
    lines.append("</urlset>")
    return "\n".join(lines)
