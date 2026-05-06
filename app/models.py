from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, func
)
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    image_url = Column(String(500), default="")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    seo_title = Column(String(300), default="")
    seo_description = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    logo_url = Column(String(500), default="")
    website = Column(String(500), default="")
    is_official_dealer = Column(Boolean, default=True)
    show_in_footer = Column(Boolean, default=False)
    show_in_catalog = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    seo_title = Column(Text, default="")
    seo_description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    products = relationship("Product", back_populates="brand_rel", foreign_keys="Product.brand_id")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(300), nullable=False)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    sku = Column(String(100), default="", index=True)
    brand = Column(String(100), default="")
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    description = Column(Text, default="")
    short_description = Column(Text, default="")
    price = Column(Float, default=0.0)
    old_price = Column(Float, default=0.0)
    in_stock = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    # Медиа: images[0] = основное фото, images[1:] = дополнительные
    images = Column(JSON, default=list)
    video_url = Column(String(500), default="")
    # Файлы для скачивания: [{"name": "Руководство", "url": "/static/uploads/file.pdf"}, ...]
    files = Column(JSON, default=list)
    # Характеристики
    specs = Column(JSON, default=dict)
    # SEO
    seo_title = Column(String(300), default="")
    seo_description = Column(String(500), default="")
    # Парсинг
    parsed_from = Column(String(300), default="")
    parsed_sku = Column(String(100), default="")
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    category = relationship("Category", back_populates="products")
    brand_rel = relationship("Brand", back_populates="products", foreign_keys=[brand_id])


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    short_description = Column(String(500), default="")
    price_from = Column(Float, default=0.0)
    price_to = Column(Float, default=0.0)
    image_url = Column(String(500), default="")
    icon = Column(String(100), default="shield")
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    seo_title = Column(String(300), default="")
    seo_description = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    excerpt = Column(String(500), default="")
    content = Column(Text, default="")
    cover_image = Column(String(500), default="")
    is_published = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    seo_title = Column(String(300), default="")
    seo_description = Column(String(500), default="")
    seo_keywords = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    customer_email = Column(String(200), default="")
    comment = Column(Text, default="")
    items = Column(JSON, default=list)
    total = Column(Float, default=0.0)
    status = Column(String(50), default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SiteSettings(Base):
    __tablename__ = "site_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")
