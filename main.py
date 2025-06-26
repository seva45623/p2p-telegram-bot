import asyncio
import aiohttp
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Токен Telegram-бота
TOKEN = '7728031836:AAHHTy5F_teDHnkvLG6xXQvA4ITMn3QCQOw'

user_chat_id = -4614762358  # получим после команды /start

ALLOWED_BANKS = ["Monobank", "PrivatBank", "PUMB"]
SPREAD_THRESHOLD = 2.6  # 1%
CHECK_INTERVAL = 5  # секунд

async def get_binance_prices():
    url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
    headers = {'Content-Type': 'application/json'}

    async with aiohttp.ClientSession() as session:
        async def get_price(trade_type):
            payload = {
                "asset": "USDT",
                "fiat": "UAH",
                "tradeType": trade_type,
                "page": 1,
                "rows": 10,
                "payTypes": ALLOWED_BANKS
            }
            async with session.post(url, json=payload, headers=headers) as r:
                data = await r.json()
                advs = data.get("data", [])
                for adv in advs:
                    return float(adv["adv"]["price"])
            return None

        buy = await get_price("BUY")
        sell = await get_price("SELL")
        return {"buy": buy, "sell": sell}


from aiohttp import ClientTimeout

from aiohttp import ClientTimeout

async def get_bybit_prices():
    url = 'https://api2.bybit.com/fiat/otc/item/online'
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bybit.com/",
        "Origin": "https://www.bybit.com",
        "Connection": "keep-alive",
    }

    timeout = ClientTimeout(total=10)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        results = {}
        for side in ['BUY', 'SELL']:
            payload = {
                "userId": "",
                "tokenId": "USDT",
                "currencyId": "UAH",
                "payment": [],  # можно попробовать ALLOWED_BANKS после отладки
                "side": side,
                "size": 10,
                "page": 1
            }

            try:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        print(f"❌ Bybit API вернул статус {response.status}")
                        continue
                    data = await response.json()
                    items = data.get('result', {}).get('items', [])
                    print(f"\n🔄 Bybit {side}: получено {len(items)} офферов")

                    for item in items:
                        payments = item.get('payments', [])
                        print(f"📦 Платёжки оффера: {payments}")

                        # 🔧 временно принимаем первый оффер без фильтра по банкам:
                        price = float(item['price'])
                        results['buy' if side == 'BUY' else 'sell'] = price
                        print(f"💰 Bybit {side} цена: {price}")
                        break  # берём только первый подходящий оффер

            except asyncio.TimeoutError:
                print(f"⏱ Таймаут при подключении к Bybit ({side})")
            except Exception as e:
                print(f"❌ Ошибка получения Bybit {side}:", e)

        return results


async def check_arbitrage(bot: Bot):
    global user_chat_id
    while True:
        try:
            binance = await get_binance_prices()
            bybit = await get_bybit_prices()

            print("\n📊 Обновление цен:")
            print(f"🔹 Binance: Купить: {binance.get('buy')} | Продать: {binance.get('sell')}")
            print(f"🔸 Bybit:   Купить: {bybit.get('buy')} | Продать: {bybit.get('sell')}")

            for name, prices in [("Binance", binance), ("Bybit", bybit)]:
                buy = prices.get("buy")
                sell = prices.get("sell")

                if buy is None or sell is None:
                    print(f"⚠️ Недостаточно данных от {name} для расчёта спреда.")
                    continue

                spread = ((sell - buy) / buy) * 100
                print(f"📈 {name} Спред: {spread:.2f}%")

                if spread >= SPREAD_THRESHOLD:
                    message = (
                        f"📍 {name} P2P\n"
                        f"🔻 Купить USDT: {buy:.2f} грн\n"
                        f"🔺 Продать USDT: {sell:.2f} грн\n"
                        f"📈 Спред: {spread:.2f}%"
                    )
                    print(f"📬 Отправка уведомления в Telegram (спред {spread:.2f}%)")

                    if user_chat_id:
                        await bot.send_message(chat_id=user_chat_id, text=message)
                    else:
                        print("⚠️ chat_id не установлен. Уведомление не отправлено.")
                else:
                    print(f"📉 Спред {spread:.2f}% < {SPREAD_THRESHOLD}%, уведомление не отправляется.")

        except Exception as e:
            print("❌ Общая ошибка в check_arbitrage:", e)

        await asyncio.sleep(CHECK_INTERVAL)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id
    user_chat_id = update.effective_chat.id
    await update.message.reply_text(f"✅ Бот запущен. Ваш chat_id: {user_chat_id}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # запускаем задачу мониторинга после старта
    bot = Bot(token=TOKEN)
    app.job_queue.run_once(lambda ctx: asyncio.create_task(check_arbitrage(bot)), when=1)

    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()
