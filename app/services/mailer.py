"""
Email сервис — отправка заказов на почту администратора
"""
import aiosmtplib
from email.message import EmailMessage
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_order_email(order) -> bool:
    """Отправляет уведомление о новом заказе"""
    if not settings.SMTP_USER or not settings.ORDER_EMAIL:
        logger.warning("SMTP не настроен, письмо не отправлено")
        return False

    items_html = "".join(
        f"<tr><td>{item.get('name','')}</td><td>{item.get('sku','')}</td>"
        f"<td>{item.get('qty', 1)} шт.</td><td>{item.get('price', 0):,.0f} ₽</td></tr>"
        for item in (order.items or [])
    )

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
  <div style="background: #0f1923; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="color: #00e5ff; margin: 0; font-size: 22px;">🛒 Новый заказ #{order.id}</h1>
    <p style="color: #aaa; margin: 5px 0 0;">Сайт: {settings.SITE_NAME}</p>
  </div>
  <div style="background: #f9f9f9; padding: 20px; border: 1px solid #e0e0e0;">
    <h2 style="color: #0f1923;">Данные покупателя</h2>
    <table style="width: 100%; border-collapse: collapse;">
      <tr><td style="padding: 6px; color: #666; width: 140px;">Имя:</td><td><strong>{order.customer_name}</strong></td></tr>
      <tr><td style="padding: 6px; color: #666;">Телефон:</td><td><strong>{order.customer_phone}</strong></td></tr>
      {"<tr><td style='padding: 6px; color: #666;'>Email:</td><td>" + order.customer_email + "</td></tr>" if order.customer_email else ""}
      {"<tr><td style='padding: 6px; color: #666;'>Комментарий:</td><td>" + order.comment + "</td></tr>" if order.comment else ""}
    </table>

    <h2 style="color: #0f1923; margin-top: 20px;">Состав заказа</h2>
    <table style="width: 100%; border-collapse: collapse; border: 1px solid #e0e0e0;">
      <thead>
        <tr style="background: #0f1923; color: white;">
          <th style="padding: 8px; text-align: left;">Товар</th>
          <th style="padding: 8px; text-align: left;">Артикул</th>
          <th style="padding: 8px; text-align: center;">Кол-во</th>
          <th style="padding: 8px; text-align: right;">Цена</th>
        </tr>
      </thead>
      <tbody>{items_html}</tbody>
      <tfoot>
        <tr style="background: #f0f0f0; font-weight: bold;">
          <td colspan="3" style="padding: 10px;">ИТОГО:</td>
          <td style="padding: 10px; text-align: right; color: #0f1923;">{order.total:,.0f} ₽</td>
        </tr>
      </tfoot>
    </table>

    <p style="margin-top: 20px; color: #666; font-size: 13px;">
      Дата: {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '—'}
    </p>
  </div>
  <div style="background: #0f1923; padding: 10px 20px; border-radius: 0 0 8px 8px; text-align: center;">
    <a href="{settings.SITE_DOMAIN}/admin/orders/{order.id}" 
       style="color: #00e5ff; text-decoration: none; font-size: 13px;">
      Открыть в админке →
    </a>
  </div>
</body>
</html>
"""

    msg = EmailMessage()
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ORDER_EMAIL
    msg["Subject"] = f"Новый заказ #{order.id} — {order.customer_name} | {settings.SITE_NAME}"
    msg.set_content(f"Новый заказ #{order.id} от {order.customer_name}, тел: {order.customer_phone}")
    msg.add_alternative(html, subtype="html")

    try:
        if settings.SMTP_SSL:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
        logger.info(f"Письмо о заказе #{order.id} отправлено на {settings.ORDER_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки письма: {e}")
        return False
