from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import get_db, Product, Category, Service, BlogPost
from app.services.seo import generate_sitemap
from app.config import settings

router = APIRouter()


@router.get("/sitemap.xml")
async def sitemap(db: AsyncSession = Depends(get_db)):
    products = (await db.execute(select(Product).where(Product.is_active == True))).scalars().all()
    categories = (await db.execute(select(Category))).scalars().all()
    services = (await db.execute(select(Service).where(Service.is_active == True))).scalars().all()
    posts = (await db.execute(select(BlogPost).where(BlogPost.is_published == True))).scalars().all()

    xml = generate_sitemap(products, categories, services, posts, settings.SITE_DOMAIN)
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots():
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: {settings.SITE_DOMAIN}/sitemap.xml

Host: {settings.SITE_DOMAIN.replace('https://', '').replace('http://', '')}
"""
    return Response(content=content, media_type="text/plain")
