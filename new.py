import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_bybit_prices_selenium():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options, version_main=137)

    try:
        print("🌐 Загружаем https://www.bybit.com/fiat/ua ...")
        driver.get("https://www.bybit.com/fiat/ua")

        # ⏳ Ждём таблицу офферов до 30 секунд
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".fiat-otc-ads-table"))
        )
        print("✅ Таблица офферов загружена")

        rows = driver.find_elements(By.CSS_SELECTOR, ".fiat-otc-ads-table .ant-table-row")
        print(f"🔍 Найдено строк в таблице: {len(rows)}")

        buy_price = None
        sell_price = None

        for row in rows:
            text = row.text.lower()
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) < 3:
                continue
            price_elem = cells[2]
            price_text = price_elem.text.replace(",", "").replace("₴", "").strip()

            try:
                price = float(price_text)
            except:
                continue

            print(f"➡️ Оффер: {text} | Цена: {price}")

            if "купити" in text and not buy_price:
                buy_price = price
            if "продати" in text and not sell_price:
                sell_price = price

            if buy_price and sell_price:
                break

        print(f"📈 BUY: {buy_price} | SELL: {sell_price}")
        return {"buy": buy_price, "sell": sell_price}

    except Exception as e:
        print("❌ Ошибка:", e)
        return {"buy": None, "sell": None}
    finally:
        driver.quit()

# Тест запуска
if __name__ == "__main__":
    get_bybit_prices_selenium()
