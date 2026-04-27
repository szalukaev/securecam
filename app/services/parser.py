import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
"""
Парсер сайтов производителей.
Использует requests + BeautifulSoup (без браузера).

Конфиг PARSER_SOURCES в .env, каждая строка:
  Название|url_каталога|css_селектор_артикула|css_селектор_цены

Пример:
  matrixcam|https://matrixcam.ru/ip-videonablyudenie|.article|.price
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import Product, AsyncSessionLocal

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text.replace("\xa0", "").replace(" ", ""))
    cleaned = cleaned.replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _get_sources() -> list[dict]:
    sources = []
    raw = settings.PARSER_SOURCES.strip()
    if not raw:
        return sources
    # Поддерживаем два формата: каждый источник на новой строке ИЛИ через ";"
    if "\n" not in raw and ";" in raw:
        lines = raw.split(";")
    else:
        lines = raw.splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            sources.append({
                "name": parts[0].strip(),
                "url": parts[1].strip(),
                "sku_selector": parts[2].strip(),
                "price_selector": parts[3].strip(),
            })
    return sources


def _fetch_page(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.warning(f"Не удалось загрузить {url}: {e}")
        return None


def _find_next_page(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    """Ищем ссылку на следующую страницу пагинации"""
    # rel=next
    tag = soup.find("a", rel="next")
    if tag and tag.get("href"):
        href = tag["href"]
        if href.startswith("http"):
            return href
        base = "/".join(current_url.split("/")[:3])
        return base + href

    # Кнопки типа "Следующая", "Вперёд", "›", "»"
    for text in ["Следующая", "Вперёд", "следующая", ">", "›", "»"]:
        tag = soup.find("a", string=re.compile(re.escape(text)))
        if tag and tag.get("href"):
            href = tag["href"]
            if href.startswith("http"):
                return href
            base = "/".join(current_url.split("/")[:3])
            return base + href

    return None


def _parse_source(source: dict) -> list[dict]:
    results = []
    url = source["url"]
    page_num = 0
    max_pages = 30
    visited = set()

    logger.info(f"[{source['name']}] Начинаем парсинг: {url}")

    while url and page_num < max_pages:
        if url in visited:
            break
        visited.add(url)
        page_num += 1

        soup = _fetch_page(url)
        if not soup:
            break

        skus = soup.select(source["sku_selector"])
        prices = soup.select(source["price_selector"])

        page_results = 0
        for sku_el, price_el in zip(skus, prices):
            # Чистим артикул — убираем префиксы типа "Код товара:", "Арт.:", "SKU:" и т.д.
            sku_raw = sku_el.get_text(strip=True)
            sku_text = re.sub(r'^[^a-zA-Z0-9а-яА-Я]*(?:код\s*товара|арт(?:икул)?|sku|article)[:\s]*', '', sku_raw, flags=re.IGNORECASE).strip()
            if not sku_text:
                sku_text = sku_raw  # если ничего не осталось — берём как есть
            price_text = price_el.get_text(strip=True)
            price_val = _parse_price(price_text)
            if sku_text and price_val:
                results.append({"sku": sku_text, "price": price_val})
                page_results += 1

        logger.info(f"[{source['name']}] Стр.{page_num}: найдено {page_results} товаров (SKU эл-тов: {len(skus)}, цен: {len(prices)})")

        # Если на странице вообще нет элементов по селектору — возможно неверный селектор
        if page_num == 1 and len(skus) == 0:
            logger.warning(
                f"[{source['name']}] ВНИМАНИЕ: селектор '{source['sku_selector']}' "
                f"не нашёл ни одного элемента. Проверьте CSS-селектор через DevTools браузера."
            )

        url = _find_next_page(soup, url)

    logger.info(f"[{source['name']}] Итого спарсено: {len(results)} товаров за {page_num} стр.")
    return results


async def update_prices_from_parsed(parsed_items: list[dict], db: AsyncSession) -> int:
    discount = settings.PARSER_DISCOUNT_PERCENT
    multiplier = 1.0 - (discount / 100.0)
    updated = 0

    for item in parsed_items:
        sku = item.get("sku", "").strip()
        price = item.get("price")
        if not sku or not price:
            continue

        result = await db.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()
        if product:
            new_price = round(price * multiplier, 2)
            product.old_price = product.price
            product.price = new_price
            product.parsed_sku = sku
            updated += 1
            logger.info(f"Обновлена цена: {sku} → {new_price} ₽ (было {product.old_price} ₽)")

    await db.commit()
    return updated


async def run_parser():
    sources = _get_sources()
    if not sources:
        logger.info("PARSER_SOURCES пуст — парсинг пропущен")
        return

    logger.info(f"=== Запуск парсинга, источников: {len(sources)} ===")

    async with AsyncSessionLocal() as db:
        for source in sources:
            try:
                # Специальные парсеры для конкретных сайтов
                if "dssl.ru" in source["url"]:
                    items = await asyncio.to_thread(
                        lambda s=source: asyncio.get_event_loop().run_until_complete(parse_dssl(s["url"]))
                        if False else __import__("asyncio").run(parse_dssl(s["url"]))
                    )
                else:
                    items = await asyncio.to_thread(_parse_source, source)
                if items:
                    updated = await update_prices_from_parsed(items, db)
                    logger.info(f"[{source['name']}] Обновлено товаров в БД: {updated}")
                else:
                    logger.warning(f"[{source['name']}] Товаров не найдено")
            except Exception as e:
                logger.error(f"[{source['name']}] Ошибка: {e}", exc_info=True)

    logger.info("=== Парсинг завершён ===")


import asyncio


async def parse_dssl(url: str) -> list[dict]:
    """Специальный парсер для dssl.ru — использует data-атрибуты"""
    import urllib3
    urllib3.disable_warnings()
    results = []
    page_num = 0
    visited = set()
    
    while url and page_num < 50:
        if url in visited:
            break
        visited.add(url)
        page_num += 1
        
        soup = _fetch_page_verify_false(url)
        if not soup:
            break
            
        items = soup.select("div.catalog_item_wrapp")
        logger.info(f"[dssl] Стр.{page_num}: карточек товаров: {len(items)}", )
        
        for item in items:
            # Используем data-item-id как артикул (совпадает с полем sku в БД)
            item_id = item.get("data-item-id", "").strip()
            name = item.get("data-name", "").strip()
            price_str = item.get("data-price", "").strip()
            price = _parse_price(price_str)
            if price and (item_id or name):
                # Пробуем сначала по item-id, потом по name
                results.append({"sku": item_id or name, "price": price, "name": name})
        
        next_link = soup.select_one("a[rel=next], .navigation a.next, a:contains('Следующая')")
        if next_link and next_link.get("href"):
            href = next_link["href"]
            url = href if href.startswith("http") else "https://www.dssl.ru" + href
        else:
            break
    
    logger.info(f"[dssl] Итого: {len(results)} товаров за {page_num} стр.")
    return results


def _fetch_page_verify_false(url: str):
    import urllib3
    urllib3.disable_warnings()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.warning(f"Не удалось загрузить {url}: {e}")
        return None
