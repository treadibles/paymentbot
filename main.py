import logging
import random
import requests
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# — CONFIGURATION —
TELEGRAM_TOKEN = "7295095936:AAHfwxMhrghzd_t424LHG7QnUxtQAbdJyrg"
# Predefined BTC addresses (first 3 only for brevity)
ADDRESSES = [
    "bc1q3natm8yay26erppsfk3vjk4xamuadv9wzlgcvc",
    "bc1qapagmrg4p0ata43wu8as733j59de23jttja3p7",
    "bc1qwyj225y92mlk092m9mffuglg7xwhydlh7xsxzs",
    "bc1qjnfr7erkr9s2f50u8lf5teen9x3dyam0gdlc80",
    "bc1qgsgd5kwpeyenljcg9k58l6u3yel5a7f4xpvt7a",
    "bc1qdnuk3rdm7jug83jcd5v0m6ag4k30tmtxgdn866",
    "bc1q32lahy9gqmt8upwj9ck9y6a742tfavgpdjqp8w",
    "bc1qjuhrre9gu8yt88pa5v3kv2uymem6uuv49t4l4c",
    "bc1qm3ujdy3f2dcfx5wqn3xhlrnh4znun97n45ayqf",
    "bc1qk53kk38dk28sj5l8fwzmkmtfzwzk7hyn569e2n",
    "bc1qlv245tnj25yj2vgk8lq3ydufp69tevcyy8yeag",
    "bc1qvrq4nz3xywazx8qeepx3g8d7lafrkxmjpv20vr",
    "bc1qmf9v2aeuyzns4a0079nj87xejpyp69lj2gk542",
    "bc1q9mnplyyv02940jv2wdhkqn0rc2kg2ul86gxv8f",
    "bc1qu7lusqsee0yza5xqc6s40j8ds88dr57m0sheh2",
    "bc1qztysdjtcknn7kef4k0h80lh7ftrmnjqwxazr6z",
    "bc1qn0vc8mnlmu5usd2vz4nt9swzg9aehas32hx4ad",
    "bc1qxju8n42dfjpv4wrmnpn66jm26844kexe77r68x",
    "bc1qfn588xzen4rdrvdltnya0ntlvh4r4t6a9a9c6f",
    "bc1q8cvw8f7y9dv3qmvn0s3apwftnvme4w752r22m3",
    "bc1qc4fu93vfs2lx5gd57pu6xmmujj6d64dmt8xld2",
    "bc1q67kjwdrzsrrh6pecr0fgmfwfp0druryzz9pqhd",
    "bc1qa8m6wqxchu33c3tk6lwxzg8ass0tat5fg02m8n",
    "bc1qt3gh648j6x2r5fwh2esyrvu4zu7sp2uftaxhzu",
    "bc1qpk0ghevffx74d9nakkclp6h40h582exrl3dn7a",
    "bc1qtz8q0zw2qstfdwuvhaghmlj309sw44930u5z20",
    "bc1qchxjqwa0l7nrn5dxs0t8w9ysdm33fnhuapn0s2",
    "bc1qk799lknj0kk3ckldx6tfhggkcssk6vh2hjtx42",
    "bc1qpagupc20hwchnz9nlet9hpku20t6wtatfxs9dr",
    "bc1qlaurkcwk2hgqk6uym3yv677um7w268n3r4n9hv",
    "bc1q2485ppwqfm5xxqk2nktvnecz3gas55wa39c7tr",
    "bc1q5ewul9xttzeus0nus8gmvd8vj6w78nxmh8fwwh",
    "bc1qeaq3j6atm4msv5q64mgcfj4x69yv3jpvj8usr6",
    "bc1q7tsf55gnz6swd97d2zup8hycuk6h9f9rsr6wlj",
    "bc1qz2fvhde9h5vutj2kj30w3ajxncmv4q8ss0zery",
    "bc1q0720egr790zk3nhl43thd3uy886s7et4vdwrvr",
    "bc1qtkuvqqlfqvssjj0atac30dfamcytm2unqg6c0k",
    "bc1qupvhgu4v22as0elwzupxmk4dgd0k9m7jl9vgqm",
    "bc1qpclgm3dhutmg8clhgv6ed68e7y5ktfjngsct5h",
    "bc1qaawdw47mkj3gzq2w3783fxd7tw0f74ul4v0f8a",
    "bc1qmeyycdxf2fywaykzeys779jawgsa4lr9znmq25",
    "bc1qvyqlxtjvnetdat366mu9ehpah0xtzlc0ush4a9",
    "bc1q5zlc05pazkwcetf8qen5leepvwf9shjvxuu69d",
    "bc1q8yeezdcz4kymd04ryselkax894smv47aprzvg3",
    "bc1qkcng7ga0x99pcr3t36rfyxzafn5dg5x4pcaj0m",
    "bc1qd4mu7zrngat5ya8ptem4ll02dht97j4h8c6chj",
    "bc1q286rzc3gsxw5t95nqpezgf0n42zzms6d9tgnzj",
    "bc1q3f8j9jyyykk37v20j8gm37d8n94ztvuzjqe3p2",
    "bc1qmm5mh7eff40mpl2509kvuwmdwqu2jdc6874aw2",
    "bc1q2yaw7e7xuefknl23nhg8fzaad6sx0kjh94k5t2",
    "bc1qvujefze6t6ty3v6nsg3dxtn2l5n7yl476zff0h",
    "bc1q2c8r8ngp7thlkwz0apv75c2uufeh5c08pxqtsz",
    "bc1qsfmvxyfp88esk8737pw6vasga3fmpsru8j92z6",
    "bc1qvyrgquw2m3kvg9skktz435nrmtd2lmpzww5jzc",
    "bc1qf9vke0mpahv8003e8aw7zwlyvemtprz43746gv",
    "bc1qw8ffal978kk4kysvt8ljp2y4wrt9z7e56jg6wk",
    "bc1qzkasnz9ehcp5479jjqss82rszuv9m3t6ck7u20",
    "bc1qkq3z2lv3k2tuchcc25tsuleqfppwjv3hyuksnl",
    "bc1qxqzf2drzz3ph74mlxzwc464qe9v4020xk6e92h",
    "bc1qpqw3k8nvngwlgpen3z42y0s889zmw8hxw2c4vg",
    "bc1qlly5xa5vdn008yds3ljrvtwdk5c7gwp7atyf2l",
    "bc1qn5u4sy60j5g899g8c0e4ak7rjmd8any339um2e",
    "bc1qr3wrqfd90ywr9wxrrrspwjlrvnmd0rwdnjpx0a",
    "bc1q2k75rrlznen2xug9x0yzwgga02q0ayrfzpvnnh",
    "bc1qgtfh9m4h4y86eqd7a5sz8xl9x5vjkgt64r52ja",
    "bc1qzzgutxllejc2zs4drvmn0qj6fhup2akt6jv2ax",
    "bc1q3x6es7pr204yr4cnlu622wdlx82hvfaewm7xff",
    "bc1qa8ewh3n6pnyjhpa2r332eku3ljkkyn67hlvp5f",
    "bc1q9t6usq4r4zxns7qfuh5gw2328e7spyqk3nqp9q",
    "bc1q5s9htwjm09lw4g73gpz6xurxjt6ksgmr2l756p",
    "bc1qd2zdmpegx9anlvn495p7zt7vr58tyf7zu45nqq",
    "bc1q0yzlra0n6ls0juq4g7vc24ztmcu7t0xkezyqt2",
    "bc1qykce8xczp8te6f7yrxl3n2r7ndwu2qezm0ad0w",
    "bc1qrzljxuypv26zxryt022439g9zf5vp2qhdtmjpv",
    "bc1qdr8cmascmjz07p2z2arc2yx4e49p92vczyrgf0",
    "bc1q870ell3lexd3yp36f0wywx3u2lu496p4eet98z",
    "bc1qa62wak2vcj46x09jfsap5f2dxqnmsdyg8tnl0g",
    "bc1q95wtuwlafz3vwhckufsds7luvgf5dtccp0n632",
    "bc1qpl2qkgy3p89r38s0zc730zjfpkf6ge9tdjkfc8",
    "bc1qye6pe52lpsmk66c30lu7wwj3l79ma73745ukfq",
    "bc1q7y4q5c5370jdje968adsrlhp8luhjn2xdhn390",
    "bc1qczz3gaz507zn82qpq2eww9rvgnwad3n8fxn5mf",
    "bc1q6avf0m3tukwjz97vletm88u445vv3789uthnmc",
    "bc1qzm83n6lcxq5tajtzycgpag3vcvea23va85xmyf",
    "bc1q0alpuyn7ea8fyyexp2d2m2d5gfew9m7rmnm3ta",
    "bc1q83lhkjyml0d57rlhsr442g96twt869vs824m9c",
    "bc1qmwxlzca4uv7gex42rksrh7pxktftgvmtyufequ",
    "bc1qkrjzsf4qf88ex3prxl09zc3nmqvp0v77gurr09",
    "bc1qj9d2a5hq0uvy4nx5cz9amsf8rndrpgyvkslp45",
    "bc1qy35srh39s5n9mdh9m7eg28nmz656fuatkzjs6n",
    "bc1qwm4vrsee9lh09kkvh03fhgvmpwzeae07w9u495",
    "bc1q79weucwul5s7wf4uz72r22vla690dt92qwdmqq",
    "bc1q6fa27z2f3dzqspe70q32mm5yjullcuxtdrh8v7",
    "bc1qs5xul69x7ev8ds6cfhtg22up8gtsuxvew7smnp",
    "bc1qcx6awk4ger727eyh907jpdxdpxz6yxjkwdrrf6",
    "bc1quvg4fgngytqg98xc4j2hhknsfhce0xv2d6ecjf",
    "bc1qky2nra86un56mss0s9qxt0ju3frk0udpmf443u",
    "bc1q8xr6agflnw9gkr38agzf78nzh4pr3f6g7gw5cm",
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
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logging.exception("Error fetching TX details for %s", txid)
    return None

# — HANDLERS —
async def start_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! To start, send: /pay @your_username <amount_in_usd>"
    )

async def pay_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Mitigation #7: rate-limit one pending payment per user
    if chat_id in pending_payments:
        return await update.message.reply_text(
            "⚠️ You already have a pending payment. Please wait for it to complete before starting a new one."
        )

    if len(ctx.args) != 2:
        return await update.message.reply_text(
            "Usage: /pay @your_username <amount_in_usd>"
        )
    username, amount_str = ctx.args
    if not username.startswith('@'):
        return await update.message.reply_text(
            "First argument must be your @username."
        )
    try:
        usd_amount = float(amount_str)
    except ValueError:
        return await update.message.reply_text(
            "Amount must be a number."
        )

    address = random.choice(ADDRESSES)
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

    await update.message.reply_text(
        f"💰 Send {amount_btc:.8f} BTC to {address}\n"
        f"(Bitstamp rate: ${price_usd:.2f}/BTC)\n"
        "When sent, reply with your transaction ID."
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
        # Mitigation #8: reject reused TXIDs
        used_txids = sheet.col_values(5)[1:]
        if txid in used_txids:
            return await update.message.reply_text(
                "❌ This TXID has already been used. Please provide a new one."
            )
        tx_details = fetch_tx_details(txid)
        if not tx_details:
            return await update.message.reply_text(
                "❌ TXID not found on-chain. Please check and try again."
            )
        # Mitigation #1 & #3: verify expected address and amount
        expected_sats = int(round(data['amount_btc'] * 1e8))
        actual_sats = sum(
            out.get('value', 0) for out in tx_details.get('out', [])
            if out.get('addr') == data['address']
        )
        if actual_sats < expected_sats:
            return await update.message.reply_text(
                "❌ Transaction output does not match the expected amount."
            )

        data['txid'] = txid
        sheet.update_cell(data['row_index'], 5, txid)
        await update.message.reply_text(
            "🔍 TXID received. Monitoring on-chain…"
        )

        # Schedule on-chain existence checks
        async def exist_job(context):
            try:
                txd = fetch_tx_details(data['txid'])
                if txd:
                    await context.bot.send_message(
                        chat_id,
                        "✅ Transaction detected! Waiting for 1 confirmation…"
                    )
                    context.job.schedule_removal()
                    # Schedule confirmation checks
                    async def confirm_job(context):
                        try:
                            txd2 = fetch_tx_details(data['txid'])
                            if txd2 and txd2.get('block_height'):
                                await context.bot.send_message(
                                    chat_id,
                                    "🎉 Payment confirmed! Please reply with your order information and shipping address separated by a semicolon (;)."
                                )
                                context.job.schedule_removal()
                                data['awaiting_details'] = True
                        except Exception:
                            logging.exception(
                                "Error during confirmation check for %s",
                                data['txid']
                            )
                            await context.bot.send_message(
                                chat_id,
                                "❌ Failed to check confirmation due to an error."
                            )
                    job_conf = ctx.application.job_queue.run_repeating(
                        confirm_job,
                        interval=180.0,
                        first=60.0
                    )
                    data['jobs']['conf'] = job_conf
            except Exception:
                logging.exception(
                    "Error in existence check for %s",
                    data['txid']
                )
        job_exist = ctx.application.job_queue.run_repeating(
            exist_job,
            interval=300.0,
            first=30.0
        )
        data['jobs']['exist'] = job_exist
        return

    # Step 2: collect order after confirmation
    if data.get('awaiting_details'):
        parts = text.split(';', 1)
        order = parts[0].strip()
        addr = parts[1].strip() if len(parts) > 1 else ''
        sheet.update_cell(data['row_index'], 6, order)
        sheet.update_cell(data['row_index'], 7, addr)
        await update.message.reply_text(
            "✅ Order and shipping info saved. Thank you!"
        )
        pending_payments.pop(chat_id, None)

# — MAIN —
```python
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("pay", pay_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
```
