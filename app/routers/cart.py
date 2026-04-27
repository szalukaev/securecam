from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.models import get_db, Order, Product
from app.services.mailer import send_order_email
import logging

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class OrderItem(BaseModel):
    id: int
    name: str
    sku: str = ""
    price: float
    qty: int = 1


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = ""
    comment: Optional[str] = ""
    items: list[OrderItem]


@router.post("/order")
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    if not data.items:
        raise HTTPException(400, "Корзина пуста")
    if not data.customer_name.strip() or not data.customer_phone.strip():
        raise HTTPException(400, "Укажите имя и телефон")

    total = sum(item.price * item.qty for item in data.items)
    order = Order(
        customer_name=data.customer_name.strip(),
        customer_phone=data.customer_phone.strip(),
        customer_email=data.customer_email or "",
        comment=data.comment or "",
        items=[item.model_dump() for item in data.items],
        total=total,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Отправляем email асинхронно (не блокируем ответ)
    try:
        await send_order_email(order)
    except Exception as e:
        logger.error(f"Email error: {e}")

    return {"ok": True, "order_id": order.id}


@router.get("/product/{product_id}/info")
async def product_info(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_active == True))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404)
    return {
        "id": p.id, "name": p.name, "sku": p.sku,
        "price": p.price, "in_stock": p.in_stock,
        "image": p.images[0] if p.images else ""
    }
