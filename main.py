import os
import asyncio
import requests
import pandas as pd
from datetime import datetime, timezone
import biquote

# ============================================================
# ۱. خواندن کلیدهای تلگرام از تنظیمات امن GitHub
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ============================================================
# ۲. گرفتن داده طلا (XAUUSD، کندل ۵ دقیقه‌ای)
# ============================================================
def get_gold_data():
    try:
        bq = biquote.Biquote()
        # گرفتن ۱۰۰ کندل ۵ دقیقه‌ای اخیر
        bars = bq.ohlc("XAUUSD", interval="5m", limit=100)
        df = pd.DataFrame(bars)
        df["openTime"] = pd.to_datetime(df["openTime"])
        df = df.set_index("openTime").sort_index()
        return df
    except Exception as e:
        print(f"خطا در گرفتن داده: {e}")
        return None

# ============================================================
# ۳. یک منطق بسیار محافظه‌کارانه (فقط برای اینکه اول کار راه بیفته)
# ============================================================
def check_signal(df):
    if df is None or len(df) < 30:
        return None

    # محاسبه میانگین نوسان ۲۰ کندل اخیر
    df["range"] = df["high"] - df["low"]
    avg_range = df["range"].rolling(20).mean().iloc[-1]

    last_candle = df.iloc[-1]

    # شرط: نوسان کندل آخر ۱.۵ برابر بیشتر از میانگین باشه و کندل صعودی باشه → BUY
    if last_candle["range"] > 1.5 * avg_range and last_candle["close"] > last_candle["open"]:
        return {
            "direction": "BUY",
            "entry": round(last_candle["close"], 2),
            "reason": f"نوسان کندل ۵ دقیقه‌ای بیشتر از حد معمول ({last_candle['range']:.2f} > میانگین {avg_range:.2f}) و کندل صعودی."
        }

    # برعکس: نوسان زیاد و کندل نزولی → SELL
    if last_candle["range"] > 1.5 * avg_range and last_candle["close"] < last_candle["open"]:
        return {
            "direction": "SELL",
            "entry": round(last_candle["close"], 2),
            "reason": f"نوسان کندل ۵ دقیقه‌ای بیشتر از حد معمول ({last_candle['range']:.2f} > میانگین {avg_range:.2f}) و کندل نزولی."
        }

    return None  # شرط کامل نیست، سیگنال نمی‌دیم

# ============================================================
# ۴. ارسال پیام به تلگرام
# ============================================================
async def send_telegram(text):
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)

# ============================================================
# ۵. برنامه اصلی: یک بار بیدار شو، یک بار بررسی کن، بخواب
# ============================================================
async def main():
    print("ربات بیدار شد، در حال بررسی...")
    df = get_gold_data()
    signal = check_signal(df)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if signal is None:
        message = f"""🚫 NO TRADE
📊 نماد: XAUUSD | ⏱ M5
🕒 زمان بررسی: {now_utc} UTC
📌 شرایط ورود کامل نیست. سیگنالی صادر نشد."""
    else:
        entry = signal["entry"]
        sl = entry - 2.0 if signal["direction"] == "BUY" else entry + 2.0
        tp1 = entry + 3.0 if signal["direction"] == "BUY" else entry - 3.0

        message = f"""🔔 سیگنال جدید
🆔 شناسه: SIG-{now_utc.replace(' ', '-').replace(':', '')}
📊 نماد: XAUUSD
⏱ تایم‌فریم: M5
📈 جهت: {signal['direction']}
💰 قیمت ورود: {entry}
🛑 حد ضرر: {round(sl, 2)}
🎯 حد سود ۱: {round(tp1, 2)} | R:R: 1:1.5
⚖️ ریسک پیشنهادی: ۰.۲۵٪
📌 دلیل ورود: {signal['reason']}
⏳ اعتبار سیگنال: ۱۵ دقیقه
🕒 زمان صدور: {now_utc} UTC
⚠️ این سیگنال توصیه مالی نیست و مسئولیت تصمیم با کاربر است."""

    await send_telegram(message)
    print("بررسی تمام شد، پیام پردازش شد.")

if __name__ == "__main__":
    asyncio.run(main())
