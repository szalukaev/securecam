from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from app.models import get_db, Product, Category, Service, BlogPost, Brand
from app.services import seo as seo_svc
from app.config import settings
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_footer_brands(db: AsyncSession) -> list:
    try:
        result = await db.execute(
            select(Brand).where(Brand.show_in_footer == True).order_by(Brand.sort_order)
        )
        return result.scalars().all()
    except Exception:
        return []


def base_ctx(request: Request, footer_brands=None) -> dict:
    return {
        "request": request,
        "site_name": settings.SITE_NAME,
        "site_phone": settings.SITE_PHONE,
        "site_email": settings.SITE_EMAIL,
        "site_address": settings.SITE_ADDRESS,
        "footer_brands": footer_brands or [],
    }


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    # ИСПРАВЛЕНО: footer_brands теперь передаётся через base_ctx
    footer_brands = await get_footer_brands(db)

    # Featured products
    products_q = await db.execute(
        select(Product).where(Product.is_active == True, Product.is_featured == True)
        .order_by(Product.sort_order).limit(8)
    )
    featured = products_q.scalars().all()

    # Services
    svc_q = await db.execute(
        select(Service).where(Service.is_active == True, Service.is_featured == True)
        .order_by(Service.sort_order).limit(6)
    )
    services = svc_q.scalars().all()

    # Latest blog
    blog_q = await db.execute(
        select(BlogPost).where(BlogPost.is_published == True)
        .order_by(BlogPost.created_at.desc()).limit(3)
    )
    posts = blog_q.scalars().all()

    # Categories
    cat_q = await db.execute(
        select(Category).where(Category.parent_id == None).order_by(Category.sort_order)
    )
    categories = cat_q.scalars().all()

    ctx = base_ctx(request, footer_brands)
    ctx.update({
        "featured": featured,
        "services": services,
        "posts": posts,
        "categories": categories,
        "seo": {
            "title": f"Видеонаблюдение в Екатеринбурге — {settings.SITE_NAME}",
            "description": settings.SITE_DESCRIPTION,
        },
        "schema_json": json.dumps(seo_svc.org_schema(), ensure_ascii=False),
    })
    return templates.TemplateResponse("index.html", ctx)


@router.get("/catalog", response_class=HTMLResponse)
async def catalog(
    request: Request,
    page: int = Query(1, ge=1),
    q: str = Query(""),
    brand: str = Query(""),
    db: AsyncSession = Depends(get_db)
):
    # Если есть поиск/фильтр — показываем товары
    if q or brand:
        per_page = 24
        offset = (page - 1) * per_page
        query = select(Product).where(Product.is_active == True)
        count_q = select(func.count(Product.id)).where(Product.is_active == True)
        if q:
            like = f"%{q}%"
            f_filter = or_(Product.name.ilike(like), Product.sku.ilike(like), Product.brand.ilike(like))
            query = query.where(f_filter)
            count_q = count_q.where(f_filter)
        if brand:
            query = query.where(Product.brand == brand)
            count_q = count_q.where(Product.brand == brand)
        total = (await db.execute(count_q)).scalar()
        products = (await db.execute(query.order_by(Product.sort_order, Product.id).offset(offset).limit(per_page))).scalars().all()
        brands_list = (await db.execute(select(Product.brand).distinct().where(Product.is_active == True, Product.brand != ""))).scalars().all()
        fb = await get_footer_brands(db)
        ctx = base_ctx(request, fb)
        ctx.update({
            "products": products, "categories": [], "brands": sorted(brands_list),
            "total": total, "page": page, "per_page": per_page,
            "q": q, "brand": brand, "pages": (total + per_page - 1) // per_page,
            "mode": "search",
            "seo": {"title": f"Поиск: {q or brand} | {settings.SITE_NAME}", "description": ""},
        })
        return templates.TemplateResponse("catalog.html", ctx)

    # Главная каталога — показываем корневые категории
    root_cats = (await db.execute(
        select(Category).where(Category.parent_id == None).order_by(Category.sort_order)
    )).scalars().all()

    cat_counts = {}
    for cat in root_cats:
        count = (await db.execute(
            select(func.count(Product.id)).where(Product.category_id == cat.id, Product.is_active == True)
        )).scalar()
        subcats = (await db.execute(
            select(Category).where(Category.parent_id == cat.id).order_by(Category.sort_order)
        )).scalars().all()
        cat.subcategories = subcats
        cat_counts[cat.id] = count

    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({
        "root_categories": root_cats,
        "cat_counts": cat_counts,
        "mode": "categories",
        "seo": {
            "title": f"Каталог видеонаблюдения Екатеринбург | {settings.SITE_NAME}",
            "description": "Камеры, регистраторы, системы видеонаблюдения. Hikvision, Dahua, TANTOS и другие бренды.",
        },
    })
    return templates.TemplateResponse("catalog.html", ctx)


@router.get("/catalog/category/{slug}", response_class=HTMLResponse)
async def catalog_category(slug: str, request: Request, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_db)):
    cat_r = await db.execute(select(Category).options(joinedload(Category.parent)).where(Category.slug == slug))
    cat = cat_r.scalar_one_or_none()
    if not cat:
        raise HTTPException(404)

    subcats_r = await db.execute(select(Category).where(Category.parent_id == cat.id).order_by(Category.sort_order))
    subcategories = subcats_r.scalars().all()

    sub_counts = {}
    for sub in subcategories:
        count = (await db.execute(
            select(func.count(Product.id)).where(Product.category_id == sub.id, Product.is_active == True)
        )).scalar()
        sub_counts[sub.id] = count

    per_page = 24
    offset = (page - 1) * per_page
    products = (await db.execute(
        select(Product).where(Product.category_id == cat.id, Product.is_active == True)
        .order_by(Product.sort_order, Product.id).offset(offset).limit(per_page)
    )).scalars().all()
    total = (await db.execute(
        select(func.count(Product.id)).where(Product.category_id == cat.id, Product.is_active == True)
    )).scalar()

    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({
        "category": cat,
        "subcategories": subcategories,
        "sub_counts": sub_counts,
        "products": products,
        "total": total, "page": page, "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "seo": seo_svc.category_seo(cat),
    })
    return templates.TemplateResponse("catalog_category.html", ctx)


@router.get("/catalog/{slug}", response_class=HTMLResponse)
async def product_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).options(joinedload(Product.category)).where(Product.slug == slug, Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404)

    product.view_count = (product.view_count or 0) + 1
    await db.commit()

    related = (await db.execute(
        select(Product).where(Product.category_id == product.category_id, Product.id != product.id, Product.is_active == True)
        .limit(4)
    )).scalars().all()

    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({
        "product": product, "related": related,
        "seo": seo_svc.product_seo(product),
        "schema_json": json.dumps(seo_svc.product_schema(product), ensure_ascii=False),
    })
    return templates.TemplateResponse("product.html", ctx)


@router.get("/services", response_class=HTMLResponse)
async def services_list(request: Request, db: AsyncSession = Depends(get_db)):
    svc_r = await db.execute(select(Service).where(Service.is_active == True).order_by(Service.sort_order))
    services = svc_r.scalars().all()
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({
        "services": services,
        "seo": {
            "title": f"Услуги по видеонаблюдению в Екатеринбурге | {settings.SITE_NAME}",
            "description": "Проектирование, монтаж, настройка и обслуживание систем видеонаблюдения.",
        },
    })
    return templates.TemplateResponse("services.html", ctx)


@router.get("/services/{slug}", response_class=HTMLResponse)
async def service_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.slug == slug, Service.is_active == True))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(404)
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({"service": service, "seo": seo_svc.service_seo(service)})
    return templates.TemplateResponse("service_detail.html", ctx)


@router.get("/blog", response_class=HTMLResponse)
async def blog(request: Request, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_db)):
    per_page = 9
    offset = (page - 1) * per_page
    posts = (await db.execute(
        select(BlogPost).where(BlogPost.is_published == True)
        .order_by(BlogPost.created_at.desc()).offset(offset).limit(per_page)
    )).scalars().all()
    total = (await db.execute(select(func.count(BlogPost.id)).where(BlogPost.is_published == True))).scalar()
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({
        "posts": posts, "total": total, "page": page, "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "seo": {
            "title": f"Блог о видеонаблюдении | {settings.SITE_NAME}",
            "description": "Статьи, советы и новости о системах видеонаблюдения в Екатеринбурге.",
        },
    })
    return templates.TemplateResponse("blog.html", ctx)


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug, BlogPost.is_published == True))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404)
    post.view_count = (post.view_count or 0) + 1
    await db.commit()
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx.update({"post": post, "seo": seo_svc.blog_seo(post)})
    return templates.TemplateResponse("blog_post.html", ctx)


@router.get("/contacts", response_class=HTMLResponse)
async def contacts(request: Request, db: AsyncSession = Depends(get_db)):
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx["seo"] = {
        "title": f"Контакты | {settings.SITE_NAME}",
        "description": f"Свяжитесь с нами: {settings.SITE_PHONE}. {settings.SITE_ADDRESS}.",
    }
    return templates.TemplateResponse("contacts.html", ctx)


@router.get("/wishlist", response_class=HTMLResponse)
async def wishlist(request: Request, db: AsyncSession = Depends(get_db)):
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx["seo"] = {"title": f"Избранное | {settings.SITE_NAME}", "description": ""}
    return templates.TemplateResponse("wishlist.html", ctx)


@router.get("/compare", response_class=HTMLResponse)
async def compare(request: Request, db: AsyncSession = Depends(get_db)):
    fb = await get_footer_brands(db)
    ctx = base_ctx(request, fb)
    ctx["seo"] = {"title": f"Сравнение товаров | {settings.SITE_NAME}", "description": ""}
    return templates.TemplateResponse("compare.html", ctx)