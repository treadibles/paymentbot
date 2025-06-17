import logging
import random
import requests
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# — CONFIGURATION —
TELEGRAM_TOKEN = "7295095936:AAHfwxMhrghzd_t424LHG7QnUxtQAbdJyrg"

# Predefined BTC addresses (first 3 only)
ADDRESSES = [
    "bc1qysz8djfek75qey0fj56w4qj7tq7jtdhckzr0ys",
    "bc1qme0n3j4hjzyyy9zhm8mc2yj4vw39drqn74lzgd",
    "bc1q3natm8yay26erppsfk3vjk4xamuadv9wzlgcvc",
]

# — GOOGLE SHEETS SETUP —
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
GC = gspread.authorize(CREDS)
SPREADSHEET_KEY = '1rFMAR5PqkocChPG5z4lUKntFrw6-AINrvSL2Yux7G5w'
sheet = GC.open_by_key(SPREADSHEET_KEY).sheet1

# — STATE —
pending_payments = {}

# — HELPERS —
def get_btc_price_bitstamp() -> float:
    resp = requests.get("https://www.bitstamp.net/api/v2/ticker/btcusd")
    resp.raise_for_status()
    return float(resp.json()['last'])


def fetch_tx_details(txid: str) -> dict | None:
    try:
        resp = requests.get(f"https://blockchain.info/rawtx/{txid}?format=json", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        logging.exception("Error fetching TX details")
    return None


def get_confirmations(txid: str) -> int:
    try:
        resp = requests.get(f"https://blockchain.info/q/txconfirmations/{txid}", timeout=10)
        resp.raise_for_status()
        return int(resp.text)
    except Exception:
        logging.exception("Error fetching confirmation count")
    return 0

# — HANDLERS —
async def start_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! To start, send: /pay @your_username <amount_in_usd>"
    )

async def pay_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logging.info("▶️ pay_command called; ctx.args=%r", ctx.args)
    try:
        if len(ctx.args) != 2:
            return await update.message.reply_text(
                "Usage: /pay @your_username <amount_in_usd>"
            )

        username, amount_str = ctx.args
        if not username.startswith('@'):
            return await update.message.reply_text(
                "First argument must be your @username."
            )

        usd_amount = float(amount_str)
        address = random.choice(ADDRESSES)
        logging.info("Selected BTC address %s", address)
        price_usd = get_btc_price_bitstamp()
        amount_btc = usd_amount / price_usd

        # Record session
        sheet.append_row([
            username,
            usd_amount,
            f"{amount_btc:.8f}",
            address,
            "",  # TXID placeholder
            "",  # Order placeholder
            ""   # Address placeholder
        ])
        row_index = len(sheet.get_all_values())
        chat_id = update.effective_chat.id
        pending_payments[chat_id] = {
            'username': username,
            'fiat': usd_amount,
            'address': address,
            'amount_btc': amount_btc,
            'txid': None,
            'awaiting_details': False,
            'row_index': row_index,
            'jobs': {}
        }

        # Schedule existence check with context
        job_exist = ctx.application.job_queue.run_repeating(
            callback=check_tx_existence,
            interval=30.0,
            first=5.0,
            context=chat_id
        )
        pending_payments[chat_id]['jobs']['exist'] = job_exist

        # Initial reply
        reply_text = (
            f"💰 Send {amount_btc:.8f} BTC to {address}\n"
            f"(Bitstamp rate: ${price_usd:.2f}/BTC)\n"
            "When sent, reply with your transaction ID."
        )
        await update.message.reply_text(reply_text)

    except Exception as e:
        logging.exception("Error in pay_command")
        await update.message.reply_text(
            f"❌ Oops—something went wrong: {e}"
        )

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = pending_payments.get(chat_id)
    if not data:
        return

    text = update.message.text.strip()
    # Step 1: receive TXID
    if data['txid'] is None:
        txid = text
        tx_details = fetch_tx_details(txid)
        if not tx_details:
            return await update.message.reply_text(
                "❌ TXID not found on-chain. Please check and try again."
            )
        tx_time = tx_details.get('time')
        if tx_time and (time.time() - tx_time) > 86400:
            return await update.message.reply_text(
                "❌ This transaction is older than 24 hours. Please provide a recent TXID."
            )

        data['txid'] = txid
        sheet.update_cell(data['row_index'], 5, txid)
        await update.message.reply_text(
            "🔍 TXID received. Monitoring on-chain…"
        )
        return

    # Step 2: collect order after confirmation
    if data.get('awaiting_details'):
        order, addr = (text.split(';', 1) + [''])[:2]
        sheet.update_cell(data['row_index'], 6, order.strip())
        sheet.update_cell(data['row_index'], 7, addr.strip())
        await update.message.reply_text(
            "✅ Order and shipping info saved. Thank you!"
        )
        # cleanup
        pending_payments.pop(chat_id, None)

# — BACKGROUND TASKS —
async def check_tx_existence(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.context
    data = pending_payments.get(chat_id)
    if not data:
        return ctx.job.schedule_removal()

    # Debug message each check
    await ctx.bot.send_message(chat_id, "🔎 Checking for transaction on-chain...")
    if fetch_tx_details(data['txid']):
        await ctx.bot.send_message(
            chat_id,
            "✅ Transaction found! Starting confirmation checks..."
        )
        ctx.job.schedule_removal()
        job_conf = ctx.application.job_queue.run_repeating(
            callback=check_tx_confirmation,
            interval=60.0,
            first=10.0,
            context=chat_id
        )
        pending_payments[chat_id]['jobs']['conf'] = job_conf

async def check_tx_confirmation(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.context
    data = pending_payments.get(chat_id)
    if not data:
        return ctx.job.schedule_removal()

    # Get and report confirmation count
    conf_count = get_confirmations(data['txid'])
    await ctx.bot.send_message(
        chat_id,
        f"🔄 Checking confirmations... current count: {conf_count}"
    )
    if conf_count >= 1:
        await ctx.bot.send_message(
            chat_id,
            "🎉 Payment confirmed! Please reply with your order information and shipping address separated by a semicolon (;)."
        )
        ctx.job.schedule_removal()
        data['awaiting_details'] = True

# — MAIN —
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("pay", pay_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
