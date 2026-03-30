#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════
# FLOWX BOT - ULTIMATE MONEY MACHINE 💀 (FIXED & COMPLETE)
# ═══════════════════════════════════════════════════════════════════

import logging
import asyncio
import sys
import io
import math
import random
import string
import datetime
import requests
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('flowx.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import config
from database import (
    get_db, create_user, get_user, update_points,
    get_leaderboard, get_stats, init_database
)
from utils.keyboards import (
    main_menu, earn_menu, tools_menu, games_menu,
    withdraw_menu, payment_methods, vip_menu,
    referral_share, ads_menu, leaderboard_tabs,
    admin_menu, back_button
)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─── HELPERS ───────────────────────────────────────────────────────

def is_vip(user: dict) -> bool:
    """Check if user has active VIP"""
    if not user or not user.get('vip_until'):
        return False
    try:
        return datetime.datetime.now() < datetime.datetime.fromisoformat(user['vip_until'])
    except Exception:
        return False

def is_admin(telegram_id: int) -> bool:
    return telegram_id in config.ADMIN_IDS

def safe_edit(query, text, **kwargs):
    """Edit message safely - ignore 'message not modified' errors"""
    try:
        return query.edit_message_text(text, **kwargs)
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"safe_edit error: {e}")

# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    db_user = get_user(user.id)

    if not db_user:
        ref_code = args[0] if args else None
        referred_by = None

        if ref_code:
            with get_db() as conn:
                ref_row = conn.execute(
                    "SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code,)
                ).fetchone()
                if ref_row and ref_row['telegram_id'] != user.id:
                    referred_by = ref_row['telegram_id']

        new_code, status = create_user(
            user.id, user.username, user.first_name,
            user.last_name, referred_by
        )

        if status == "exists":
            db_user = get_user(user.id)
        else:
            db_user = get_user(user.id)
            if referred_by:
                try:
                    await context.bot.send_message(
                        referred_by,
                        f"🎉 *{user.first_name}* joined using your link!\n"
                        f"💰 +50 points credited!\n"
                        f"🏆 Check /leaderboard",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

        welcome = config.MESSAGES['welcome_new'].format(
            name=user.first_name,
            points=10 if referred_by else 0,
            money=float(Decimal(10 if referred_by else 0) * config.POINTS_TO_USD),
            referrals=random.randint(50, 200)
        )
    else:
        welcome = config.MESSAGES['welcome_back'].format(
            name=user.first_name,
            points=db_user['points'],
            money=float(Decimal(db_user['points']) * config.POINTS_TO_USD),
            earned=db_user['total_earned']
        )

    await update.message.reply_text(
        welcome,
        parse_mode='Markdown',
        reply_markup=main_menu(is_vip(db_user) if db_user else False)
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📚 *FLOWX BOT GUIDE* 📚

*💰 EARNING METHODS:*
• /spin - Free daily spin (3h cooldown)
• /refer - 50 points per friend
• /ads - Watch ads for points
• /games - Play & win points
• /tools - Use utilities, earn points

*💸 CASHOUT:*
• /withdraw - Minimum 500 pts ($5)
• Methods: UPI, PayPal, Crypto, Bank

*⭐ VIP BENEFITS:*
• 2x earnings on everything
• No spin cooldown
• Priority withdrawals (12h)
• Exclusive contests

*🛠️ COMMANDS:*
/start - Main menu
/stats - Your statistics
/leaderboard - Top earners
/refer - Referral link
/spin - Lucky spin
/withdraw - Cash out
/admin - Admin panel (admins only)

*Need help?* Contact @admin
    """
    await update.message.reply_text(text, parse_mode='Markdown')


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_obj = update.effective_user
    user = get_user(user_obj.id)
    if not user:
        return await update.message.reply_text("Use /start first!")

    with get_db() as conn:
        rank = conn.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE points > ?", (user['points'],)
        ).fetchone()[0]
        refs = conn.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user['telegram_id'],)
        ).fetchone()[0]

    vip_status = (
        f"✅ ACTIVE until {user['vip_until'][:10]}"
        if is_vip(user)
        else "❌ Not active — Upgrade for 2x!"
    )

    text = f"""
📊 *YOUR COMPLETE STATS* 📊

💰 *BALANCE*
Points: {user['points']:,}
Value: ${float(Decimal(user['points']) * config.POINTS_TO_USD):.2f}

📈 *EARNINGS*
Total Earned: {user['total_earned']:,}
Total Spent:  {user['total_spent']:,}
Net Profit:   {user['total_earned'] - user['total_spent']:,}

🏆 *RANKING*
Global Rank: #{rank:,}
Referrals: {refs}

🎯 *ACTIVITY*
Total Spins:  {user['total_spins']}
Games Played: {user['total_games']}
Tools Used:   {user['total_tools']}
Games Won:    {user['games_won']}

🔥 *STREAK*
Current: {user['streak']} days

⭐ *VIP STATUS*
{vip_status}
    """
    await update.message.reply_text(
        text, parse_mode='Markdown',
        reply_markup=main_menu(is_vip(user))
    )


async def cmd_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow /spin command directly"""
    user = get_user(update.effective_user.id)
    if not user:
        return await update.message.reply_text("Use /start first!")
    msg = await update.message.reply_text("🎰 Loading spin...", parse_mode='Markdown')
    await _do_spin(context, user, msg)


async def cmd_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return await update.message.reply_text("Use /start first!")
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    await update.message.reply_text(
        f"🔗 *Your referral link:*\n`{link}`\n\n💰 Earn 50 pts per friend!",
        parse_mode='Markdown',
        reply_markup=referral_share(link)
    )


async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return await update.message.reply_text("Use /start first!")
    await _show_withdraw_menu_msg(update.message, user)


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    top = get_leaderboard(10)
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "🏆 *GLOBAL LEADERBOARD* 🏆\n\n"
    for i, row in enumerate(top):
        name = row.get('first_name') or row.get('username') or "Anonymous"
        text += f"{medals[i]} *{name}* — {row['points']:,} pts\n"
    if user:
        with get_db() as conn:
            rank = conn.execute(
                "SELECT COUNT(*) + 1 FROM users WHERE points > ?", (user['points'],)
            ).fetchone()[0]
        text += f"\n📊 *Your Position:* #{rank:,}\n"
        text += f"💰 *Your Points:* {user['points']:,}\n"
    text += "\n🎁 *Top 3 get bonus prizes every Sunday!*"
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=leaderboard_tabs())


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    stats = get_stats()
    text = f"""
🔐 *ADMIN PANEL*

👥 Total Users: {stats['total_users']:,}
📅 Today New:   {stats['today_users']:,}
💰 Total Points:{stats['total_points']:,}
🏦 Total Earned:{stats['total_earned']:,}
⭐ VIP Users:   {stats['vip_users']:,}
🎰 Spins Today: {stats['spins_today']:,}
⏳ Pending WD:  {stats['pending_count']} ({stats['pending_points']:,} pts)
    """
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=admin_menu())


# ═══════════════════════════════════════════════════════════════════
# SPIN CORE
# ═══════════════════════════════════════════════════════════════════

async def _do_spin(context, user, msg):
    """Core spin logic usable from both callback and command"""
    # Cooldown check
    if user['last_spin'] and not is_vip(user):
        last = datetime.datetime.fromisoformat(user['last_spin'])
        diff = (datetime.datetime.now() - last).total_seconds()
        if diff < config.SPIN_COOLDOWN_HOURS * 3600:
            wait = config.SPIN_COOLDOWN_HOURS * 3600 - diff
            h, m = int(wait // 3600), int((wait % 3600) // 60)
            text = (
                f"⏳ *SPIN COOLDOWN* ⏳\n\n"
                f"Next spin in: *{h}h {m}m*\n\n"
                f"⚡ VIP = No cooldown!"
            )
            try:
                await msg.edit_text(text, parse_mode='Markdown',
                                    reply_markup=main_menu(is_vip(user)))
            except Exception:
                pass
            return

    # Animation
    for i, emoji in enumerate(["🎰","🎲","🎯","💎","🔥","⭐","💰"]):
        await asyncio.sleep(0.35)
        bar = '█' * (i + 1) + '░' * (6 - i)
        pct = int((i + 1) / 7 * 100)
        try:
            await msg.edit_text(
                f"{emoji} *SPINNING...* {emoji}\n{bar} {pct}%",
                parse_mode='Markdown'
            )
        except Exception:
            pass

    # Pick reward
    mult = config.VIP_MULTIPLIER if is_vip(user) else 1.0
    rand = random.random()
    cumsum = 0
    points, tier = 1, 0
    for i, (prob, pts, title, _) in enumerate(config.SPIN_REWARDS):
        cumsum += prob
        if rand <= cumsum:
            points = int(pts * mult)
            tier = i
            break

    success, new_balance = update_points(
        user['telegram_id'], points, f"Spin: +{points} pts", 'spin_win'
    )

    with get_db() as conn:
        conn.execute(
            "INSERT INTO spin_history (user_id, points_won, multiplier, is_jackpot) VALUES (?,?,?,?)",
            (user['telegram_id'], points, mult, 1 if tier >= 5 else 0)
        )
        conn.execute(
            "UPDATE users SET total_spins = total_spins + 1, last_spin = ? WHERE telegram_id = ?",
            (datetime.datetime.now().isoformat(), user['telegram_id'])
        )

    titles = ["💎 COMMON","🎁 UNCOMMON","🔥 RARE","💰 EPIC","🚀 LEGENDARY","👑 MYTHIC"]
    emojis = ["💎","🎁","🔥","💰","🚀","👑"]
    usd = float(Decimal(points) * config.POINTS_TO_USD)
    total_usd = float(Decimal(new_balance) * config.POINTS_TO_USD)

    result = (
        f"🎉 *{titles[tier]}!* 🎉\n\n"
        f"{emojis[tier]} *+{points} POINTS* {emojis[tier]}\n"
        f"💵 Value: ${usd:.2f}\n\n"
        f"📊 Balance: {new_balance:,} pts (${total_usd:.2f})\n\n"
        f"{'⭐ *VIP 2x BONUS ACTIVE!*' if is_vip(user) else ''}\n"
        f"🔄 Next spin: {'Anytime (VIP)!' if is_vip(user) else f'{config.SPIN_COOLDOWN_HOURS}h'}"
    )
    try:
        await msg.edit_text(result, parse_mode='Markdown',
                            reply_markup=main_menu(is_vip(user)))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# TOOL PROCESSORS
# ═══════════════════════════════════════════════════════════════════

async def process_url_shortener(url: str) -> str:
    try:
        r = requests.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=5)
        if r.status_code == 200:
            return f"🔗 Shortened URL:\n`{r.text.strip()}`"
    except Exception:
        pass
    return "❌ Could not shorten URL. Try again."


async def process_qr_code(text: str):
    try:
        import qrcode
        qr = qrcode.make(text)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception:
        return None


def process_calculator(expr: str) -> str:
    try:
        allowed = set('0123456789+-*/.() ')
        if not all(c in allowed for c in expr):
            return "❌ Invalid characters. Use: 0-9 + - * / ( )"
        result = eval(expr, {"__builtins__": {}}, {})
        return f"🔢 Result: `{expr} = {result}`"
    except ZeroDivisionError:
        return "❌ Division by zero!"
    except Exception:
        return "❌ Invalid expression."


def process_unit_converter(text: str) -> str:
    """Convert: '10 km to miles' format"""
    try:
        parts = text.lower().split()
        if len(parts) < 4 or parts[2] != 'to':
            return "❌ Format: `10 km to miles`"
        value = float(parts[0])
        from_unit = parts[1]
        to_unit = parts[3]

        conversions = {
            ('km', 'miles'): 0.621371, ('miles', 'km'): 1.60934,
            ('kg', 'lbs'): 2.20462,   ('lbs', 'kg'): 0.453592,
            ('m', 'ft'): 3.28084,     ('ft', 'm'): 0.3048,
            ('c', 'f'): None,         ('f', 'c'): None,
            ('l', 'gal'): 0.264172,   ('gal', 'l'): 3.78541,
            ('cm', 'inch'): 0.393701, ('inch', 'cm'): 2.54,
        }

        if (from_unit, to_unit) == ('c', 'f'):
            result = value * 9/5 + 32
        elif (from_unit, to_unit) == ('f', 'c'):
            result = (value - 32) * 5/9
        elif (from_unit, to_unit) in conversions:
            result = value * conversions[(from_unit, to_unit)]
        else:
            return f"❌ Unknown conversion: {from_unit} → {to_unit}"

        return f"🔄 `{value} {from_unit} = {result:.4f} {to_unit}`"
    except ValueError:
        return "❌ Format: `10 km to miles`"


def process_password_gen(length_str: str) -> str:
    try:
        length = int(length_str.strip())
        length = max(6, min(length, 50))
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd = ''.join(random.choices(chars, k=length))
        return f"🔐 Generated Password ({length} chars):\n`{pwd}`\n\n⚠️ Save it securely!"
    except ValueError:
        return "❌ Send a number between 6 and 50."


def process_weather(city: str) -> str:
    try:
        r = requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=5,
            headers={'User-Agent': 'FlowXBot/1.0'}
        )
        if r.status_code == 200:
            return f"☁️ *Weather for {city}:*\n`{r.text.strip()}`"
    except Exception:
        pass
    return f"❌ Could not fetch weather for '{city}'. Check the city name."


def process_site_analyzer(url: str) -> str:
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        r = requests.head(url, timeout=5, allow_redirects=True)
        server = r.headers.get('Server', 'Unknown')
        content_type = r.headers.get('Content-Type', 'Unknown')
        return (
            f"🌐 *Site Analysis:*\n\n"
            f"URL: `{url}`\n"
            f"Status: `{r.status_code}`\n"
            f"Server: `{server}`\n"
            f"Content-Type: `{content_type}`\n"
            f"Final URL: `{r.url}`"
        )
    except Exception as e:
        return f"❌ Could not analyze site: {e}"


# ═══════════════════════════════════════════════════════════════════
# MESSAGE HANDLER — handles tool input & game guesses
# ═══════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    if not user:
        return await update.message.reply_text("Use /start first!")

    # ─── GAME: Guess Number ───
    if context.user_data.get('state') == 'guessing':
        target = context.user_data.get('game_number')
        tries  = context.user_data.get('game_tries', 0)
        max_t  = context.user_data.get('game_max', 7)

        try:
            guess = int(text)
        except ValueError:
            return await update.message.reply_text("🎯 Send a number between 1 and 100!")

        tries += 1
        context.user_data['game_tries'] = tries

        if guess == target:
            context.user_data.pop('state', None)
            pts = max(5, config.GAME_WIN_REWARD - (tries - 1) * 2)
            if is_vip(user):
                pts = int(pts * config.VIP_MULTIPLIER)
            update_points(user_id, pts, f"Guess game win in {tries} tries", 'game_win')
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET total_games = total_games + 1, games_won = games_won + 1 WHERE telegram_id = ?",
                    (user_id,)
                )
            return await update.message.reply_text(
                f"🎉 *CORRECT!* The number was *{target}*!\n"
                f"✅ Tries: {tries}/{max_t}\n"
                f"💰 +{pts} points!\n"
                f"{'⭐ VIP 2x applied!' if is_vip(user) else ''}",
                parse_mode='Markdown',
                reply_markup=main_menu(is_vip(user))
            )
        elif tries >= max_t:
            context.user_data.pop('state', None)
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET total_games = total_games + 1 WHERE telegram_id = ?",
                    (user_id,)
                )
            return await update.message.reply_text(
                f"💀 *GAME OVER!*\nThe number was *{target}*.\n"
                f"Better luck next time!\n\nTry /games again!",
                parse_mode='Markdown',
                reply_markup=main_menu(is_vip(user))
            )
        else:
            hint = "📈 Higher!" if guess < target else "📉 Lower!"
            remaining = max_t - tries
            return await update.message.reply_text(
                f"{hint}\nAttempts left: *{remaining}*",
                parse_mode='Markdown'
            )

    # ─── WITHDRAWAL DETAILS ───
    if context.user_data.get('state') == 'withdraw_details':
        amount  = context.user_data.get('withdraw_amount')
        method  = context.user_data.get('withdraw_method')

        if not amount or not method:
            context.user_data.pop('state', None)
            return await update.message.reply_text("Session expired. Use /withdraw again.")

        usd      = Decimal(amount) * config.POINTS_TO_USD
        fee_pct  = config.PAYMENT_METHODS.get(method, {}).get('fee', 0)
        fee      = usd * Decimal(fee_pct) / 100
        net      = usd - fee

        # Deduct points & create withdrawal
        success, new_bal = update_points(user_id, -amount, f"Withdrawal via {method}", 'withdrawal')
        if not success:
            context.user_data.pop('state', None)
            return await update.message.reply_text("❌ Insufficient balance!")

        with get_db() as conn:
            conn.execute('''
                INSERT INTO withdrawals
                    (user_id, points, usd_amount, fee, net_amount, method, payment_details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, float(usd), float(fee), float(net), method, text))

        context.user_data.pop('state', None)
        wait_time = config.PAYMENT_METHODS.get(method, {}).get('time', '24h')

        # Notify admins
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"💸 *NEW WITHDRAWAL REQUEST*\n\n"
                    f"User: {update.effective_user.first_name} ({user_id})\n"
                    f"Amount: {amount} pts = ${float(usd):.2f}\n"
                    f"Net: ${float(net):.2f}\n"
                    f"Method: {method}\n"
                    f"Details: `{text}`",
                    parse_mode='Markdown'
                )
            except Exception:
                pass

        return await update.message.reply_text(
            f"✅ *WITHDRAWAL REQUESTED!*\n\n"
            f"💰 {amount} pts = ${float(usd):.2f}\n"
            f"💵 Net (after {fee_pct}% fee): ${float(net):.2f}\n"
            f"📱 Method: {method.upper()}\n"
            f"⏰ Processing: {wait_time}\n\n"
            f"New Balance: {new_bal:,} pts",
            parse_mode='Markdown',
            reply_markup=main_menu(is_vip(user))
        )

    # ─── TOOL INPUT ───
    if context.user_data.get('state') == 'tool_input':
        tool = context.user_data.get('current_tool')
        context.user_data.pop('state', None)

        tool_info = config.TOOLS.get(tool, {})
        reward = tool_info.get('reward', 1)

        result_text = None
        photo_buf = None

        if tool == 'url':
            result_text = await process_url_shortener(text)
        elif tool == 'qr':
            photo_buf = await process_qr_code(text)
            result_text = "📸 QR Code generated!" if photo_buf else "❌ QR generation failed."
        elif tool == 'calc':
            result_text = process_calculator(text)
        elif tool == 'unit':
            result_text = process_unit_converter(text)
        elif tool == 'weather':
            result_text = process_weather(text)
        elif tool == 'pass':
            result_text = process_password_gen(text)
        elif tool == 'notes':
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO notes (user_id, content) VALUES (?, ?)", (user_id, text)
                )
            result_text = f"📝 Note saved!\n\n`{text[:200]}`"
        elif tool == 'traffic':
            result_text = process_site_analyzer(text)
        else:
            result_text = "⚙️ Tool processed!"

        # Award points
        update_points(user_id, reward, f"Tool use: {tool}", 'tool_use')
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET total_tools = total_tools + 1 WHERE telegram_id = ?",
                (user_id,)
            )

        footer = f"\n\n💰 *+{reward} points earned!*"

        if photo_buf:
            await update.message.reply_photo(
                photo=photo_buf,
                caption=result_text + footer,
                parse_mode='Markdown',
                reply_markup=back_button('tools')
            )
        else:
            await update.message.reply_text(
                (result_text or "Done!") + footer,
                parse_mode='Markdown',
                reply_markup=back_button('tools')
            )
        return

    # ─── ADMIN BROADCAST INPUT ───
    if context.user_data.get('state') == 'broadcast' and is_admin(user_id):
        context.user_data.pop('state', None)
        with get_db() as conn:
            all_users = conn.execute("SELECT telegram_id FROM users WHERE banned = 0").fetchall()

        sent, failed = 0, 0
        for row in all_users:
            try:
                await context.bot.send_message(row['telegram_id'], text, parse_mode='Markdown')
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        return await update.message.reply_text(
            f"📣 *Broadcast complete!*\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode='Markdown'
        )


# ═══════════════════════════════════════════════════════════════════
# CALLBACK ROUTER
# ═══════════════════════════════════════════════════════════════════

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = get_user(query.from_user.id)

    if not user:
        return await query.edit_message_text(
            "Please use /start first!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Start", callback_data="do_start")
            ]])
        )

    # ── NAVIGATION ──
    if data == 'main_menu':
        return await query.edit_message_text(
            "⚡ *MAIN MENU* ⚡\n\nSelect an option:",
            parse_mode='Markdown',
            reply_markup=main_menu(is_vip(user))
        )

    if data == 'cancel':
        context.user_data.clear()
        return await query.edit_message_text(
            "❌ Cancelled.\n\nBack to main menu:",
            reply_markup=main_menu(is_vip(user))
        )

    # ── EARN ──
    if data == 'earn_menu':
        return await query.edit_message_text(
            "💰 *EARN MONEY* 💰\n\nChoose method:",
            parse_mode='Markdown',
            reply_markup=earn_menu()
        )

    if data == 'spin':
        msg = await query.edit_message_text("🎰 *Starting spin...*", parse_mode='Markdown')
        return await _do_spin(context, user, msg)

    if data == 'refer':
        return await _show_refer(query, context, user)

    if data == 'ads':
        return await query.edit_message_text(
            "📺 *WATCH ADS & EARN* 📺\n\nClick ad → Watch → Come back → Claim!",
            parse_mode='Markdown',
            reply_markup=ads_menu(config.ADS)
        )

    if data == 'ad_verify':
        update_points(query.from_user.id, 5, "Ad watch claim", 'ad_watch')
        return await query.edit_message_text(
            "✅ *+5 points claimed!*\nWatch more ads to earn more!",
            parse_mode='Markdown',
            reply_markup=earn_menu()
        )

    # ── STATS ──
    if data == 'my_stats':
        return await _show_stats_callback(query, user)

    # ── LEADERBOARD ──
    if data in ('leaderboard', 'lb_rich'):
        return await _show_leaderboard(query, user, sort='points')

    if data == 'lb_refs':
        return await _show_leaderboard(query, user, sort='total_refs')

    if data == 'lb_spins':
        return await _show_leaderboard(query, user, sort='total_spins')

    if data == 'lb_games':
        return await _show_leaderboard(query, user, sort='games_won')

    # ── GAMES ──
    if data == 'games':
        return await query.edit_message_text(
            "🎮 *PLAY GAMES* 🎮\n\nWin points playing games!",
            parse_mode='Markdown',
            reply_markup=games_menu()
        )

    if data == 'game_guess':
        context.user_data['game_number'] = random.randint(1, 100)
        context.user_data['game_tries'] = 0
        context.user_data['game_max'] = 7
        context.user_data['state'] = 'guessing'
        return await query.edit_message_text(
            "🎯 *GUESS THE NUMBER* 🎯\n\n"
            "I'm thinking of a number *1–100*\n"
            "You have *7 attempts*\n\n"
            "🎁 *Win = up to 20 points!*\n\n"
            "*Type your guess:*",
            parse_mode='Markdown',
            reply_markup=back_button('games')
        )

    if data == 'game_dice':
        return await _play_dice(query, context, user)

    if data == 'game_coin':
        return await _play_coin(query, context, user)

    if data == 'game_mega':
        return await _play_mega(query, context, user)

    if data == 'game_leaderboard':
        return await _show_leaderboard(query, user, sort='games_won')

    # ── TOOLS ──
    if data == 'tools':
        return await query.edit_message_text(
            "🛠️ *UTILITY TOOLS* 🛠️\n\nUse tools = Earn points!",
            parse_mode='Markdown',
            reply_markup=tools_menu()
        )

    if data.startswith('tool_'):
        tool = data.split('_', 1)[1]
        prompts = {
            'url':     "🔗 *URL Shortener*\nSend the URL to shorten:",
            'qr':      "📸 *QR Generator*\nSend text/URL for QR code:",
            'dl':      "⬇️ *YT Downloader*\nSend YouTube link:\n(Note: downloads may be limited)",
            'calc':    "🔢 *Calculator*\nSend expression:\nExample: `5 + 3 * 2 / (1 + 1)`",
            'unit':    "🔄 *Unit Converter*\nFormat: `10 km to miles`",
            'weather': "☁️ *Weather*\nSend city name:\nExample: `Mumbai`",
            'pass':    "🔐 *Password Generator*\nSend desired length (6–50):",
            'notes':   "📝 *Notes*\nType your note:",
            'traffic': "🌐 *Site Analyzer*\nSend website URL:",
        }
        tool_info = config.TOOLS.get(tool, {})
        context.user_data['current_tool'] = tool
        context.user_data['state'] = 'tool_input'
        return await query.edit_message_text(
            f"{prompts.get(tool, 'Send input:')}\n\n💰 Reward: +{tool_info.get('reward', 1)} points",
            parse_mode='Markdown',
            reply_markup=back_button('tools')
        )

    # ── WITHDRAW ──
    if data == 'withdraw':
        return await _show_withdraw_menu_cb(query, user)

    if data == 'wd_history':
        return await _show_wd_history(query, user)

    if data.startswith('wd_') and data != 'wd_history' and data != 'wd_vip_fast':
        try:
            amount = int(data.split('_')[1])
        except (ValueError, IndexError):
            return
        context.user_data['withdraw_amount'] = amount
        usd = float(Decimal(amount) * config.POINTS_TO_USD)
        return await query.edit_message_text(
            f"💸 *SELECT PAYMENT METHOD*\n\n"
            f"Amount: {amount:,} pts = ${usd:.2f}\n\n"
            f"Choose payment method:",
            parse_mode='Markdown',
            reply_markup=payment_methods(amount)
        )

    if data.startswith('pay_'):
        parts = data.split('_')
        if len(parts) < 3:
            return
        method = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            return
        context.user_data['withdraw_method'] = method
        context.user_data['withdraw_amount'] = amount
        context.user_data['state'] = 'withdraw_details'

        usd = Decimal(amount) * config.POINTS_TO_USD
        fee_pct = config.PAYMENT_METHODS.get(method, {}).get('fee', 0)
        fee = usd * Decimal(fee_pct) / 100
        net = usd - fee
        wait_time = config.PAYMENT_METHODS.get(method, {}).get('time', '24h')

        method_labels = {
            'upi': '📱 UPI (India)', 'paypal': '💳 PayPal',
            'usdt': '₿ USDT', 'btc': '₿ Bitcoin', 'bank': '🏦 Bank'
        }
        return await query.edit_message_text(
            f"🏧 *CONFIRM WITHDRAWAL*\n\n"
            f"Amount: {amount:,} pts\n"
            f"Gross: ${float(usd):.2f}\n"
            f"Fee ({fee_pct}%): -${float(fee):.2f}\n"
            f"✅ *Net: ${float(net):.2f}*\n\n"
            f"Method: {method_labels.get(method, method)}\n"
            f"Time: {wait_time}\n\n"
            f"*Send your payment details:*\n"
            f"(UPI ID / PayPal email / Wallet address)",
            parse_mode='Markdown',
            reply_markup=back_button('withdraw')
        )

    # ── VIP ──
    if data == 'vip_upgrade':
        return await query.edit_message_text(
            "⭐ *UPGRADE TO VIP* ⭐\n\n"
            "✅ 2x Earnings (spin, refer, games)\n"
            "✅ No spin cooldown\n"
            "✅ Priority withdrawals (12h)\n"
            "✅ Exclusive VIP contests\n"
            "✅ Special leaderboard badge\n\n"
            "💰 *Pricing:*\n"
            "• 1 Month: $2.99\n"
            "• 3 Months: $7.99 (Save 11%)\n"
            "• 1 Year: $24.99 (Save 30%)\n\n"
            "⚡ Break-even: Just 300 extra points!",
            parse_mode='Markdown',
            reply_markup=vip_menu()
        )

    if data == 'vip_info':
        return await query.edit_message_text(
            "⭐ *VIP BENEFITS DETAIL* ⭐\n\n"
            "🎰 Spin: Win 2x more (up to 200 pts)\n"
            "👥 Referrals: 100 pts per friend\n"
            "🎮 Games: 2x win reward\n"
            "🛠️ Tools: 2x tool reward\n"
            "⏰ Spin Cooldown: REMOVED\n"
            "💸 Withdrawal: 12h (vs 48h)\n"
            "🏆 Leaderboard: ⭐ badge\n"
            "🎁 Monthly VIP-only contests",
            parse_mode='Markdown',
            reply_markup=vip_menu()
        )

    if data.startswith('buy_vip_'):
        try:
            months = int(data.split('_')[2])
        except (ValueError, IndexError):
            return
        prices = {1: '$2.99', 3: '$7.99', 12: '$24.99'}
        return await query.edit_message_text(
            f"💎 *VIP {months} Month{'s' if months > 1 else ''}* — {prices.get(months, '?')}\n\n"
            f"To purchase VIP, contact @admin with payment proof.\n"
            f"We'll activate within 1 hour.\n\n"
            f"Payment methods: UPI / PayPal / Crypto",
            parse_mode='Markdown',
            reply_markup=back_button('vip_upgrade')
        )

    # ── DAILY BONUS ──
    if data == 'daily_bonus':
        return await _handle_daily_bonus(query, context, user)

    # ── REFERRAL ──
    if data == 'ref_stats':
        return await _show_ref_stats(query, user)

    # ── ADMIN ──
    if data.startswith('admin_') and is_admin(query.from_user.id):
        return await _handle_admin_cb(query, context, user, data)


# ═══════════════════════════════════════════════════════════════════
# FEATURE HELPERS
# ═══════════════════════════════════════════════════════════════════

async def _show_refer(query, context, user):
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    with get_db() as conn:
        refs = conn.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user['telegram_id'],)
        ).fetchone()[0]
    text = (
        f"📢 *INVITE & EARN* 📢\n\n"
        f"💰 You Earn: *50 pts per friend*\n"
        f"👥 Your Referrals: {refs}\n"
        f"📊 Your Points: {user['points']:,}\n\n"
        f"🔗 *Your Link:*\n`{link}`\n\n"
        f"1️⃣ Share link\n"
        f"2️⃣ Friend joins\n"
        f"3️⃣ You get 50 pts instantly!\n\n"
        f"🏆 Top referrers win $100 weekly!"
    )
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=referral_share(link))


async def _show_stats_callback(query, user):
    with get_db() as conn:
        rank = conn.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE points > ?", (user['points'],)
        ).fetchone()[0]
        refs = conn.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user['telegram_id'],)
        ).fetchone()[0]

    vip_status = (
        f"✅ ACTIVE until {user['vip_until'][:10]}"
        if is_vip(user)
        else "❌ Not active"
    )
    text = (
        f"📊 *YOUR STATS*\n\n"
        f"💰 Points: {user['points']:,} (${float(Decimal(user['points'])*config.POINTS_TO_USD):.2f})\n"
        f"📈 Earned: {user['total_earned']:,} | Spent: {user['total_spent']:,}\n"
        f"🏆 Rank: #{rank:,} | Referrals: {refs}\n"
        f"🎰 Spins: {user['total_spins']} | Games: {user['total_games']}\n"
        f"🛠️ Tools: {user['total_tools']} | Wins: {user['games_won']}\n"
        f"⭐ VIP: {vip_status}"
    )
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu(is_vip(user)))


async def _show_leaderboard(query, user, sort='points'):
    sort_cols = {
        'points': ('points', '💰 Top Earners'),
        'total_refs': ('total_refs', '👥 Top Referrers'),
        'total_spins': ('total_spins', '🎰 Top Spinners'),
        'games_won': ('games_won', '🎮 Top Players'),
    }
    col, title = sort_cols.get(sort, ('points', '💰 Top Earners'))
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    with get_db() as conn:
        top = conn.execute(
            f"SELECT telegram_id, first_name, username, points, total_refs, total_spins, games_won "
            f"FROM users WHERE banned=0 ORDER BY {col} DESC LIMIT 10"
        ).fetchall()
        rank = conn.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE points > ?", (user['points'],)
        ).fetchone()[0]

    text = f"🏆 *{title}* 🏆\n\n"
    for i, row in enumerate(top):
        name = row['first_name'] or row['username'] or "Anonymous"
        val = row[col]
        text += f"{medals[i]} *{name}* — {val:,}\n"
    text += f"\n📊 Your Rank: #{rank:,} | Points: {user['points']:,}"
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=leaderboard_tabs())


async def _show_withdraw_menu_cb(query, user):
    with get_db() as conn:
        pending = conn.execute(
            "SELECT COALESCE(SUM(points),0) FROM withdrawals WHERE user_id=? AND status='pending'",
            (user['telegram_id'],)
        ).fetchone()[0]

    available = user['points'] - pending
    if available < config.MIN_WITHDRAWAL:
        needed = config.MIN_WITHDRAWAL - available
        return await query.edit_message_text(
            f"❌ *INSUFFICIENT BALANCE*\n\n"
            f"Available: {available:,} pts (${float(Decimal(available)*config.POINTS_TO_USD):.2f})\n"
            f"Minimum: {config.MIN_WITHDRAWAL:,} pts ($5.00)\n"
            f"Need: {needed:,} more pts\n\n"
            f"Earn more:\n🎰 /spin | 👥 /refer | 📺 /ads",
            parse_mode='Markdown',
            reply_markup=earn_menu()
        )
    await query.edit_message_text(
        f"🏧 *WITHDRAW MONEY*\n\n"
        f"💰 Available: {available:,} pts (${float(Decimal(available)*config.POINTS_TO_USD):.2f})\n"
        f"⏳ Pending: {pending:,} pts\n\n"
        f"*Select amount:*",
        parse_mode='Markdown',
        reply_markup=withdraw_menu(available, is_vip(user))
    )


async def _show_withdraw_menu_msg(message, user):
    with get_db() as conn:
        pending = conn.execute(
            "SELECT COALESCE(SUM(points),0) FROM withdrawals WHERE user_id=? AND status='pending'",
            (user['telegram_id'],)
        ).fetchone()[0]
    available = user['points'] - pending
    if available < config.MIN_WITHDRAWAL:
        needed = config.MIN_WITHDRAWAL - available
        return await message.reply_text(
            f"❌ *INSUFFICIENT BALANCE*\n\n"
            f"Available: {available:,} pts\nNeed {needed:,} more.",
            parse_mode='Markdown',
            reply_markup=earn_menu()
        )
    await message.reply_text(
        f"🏧 *WITHDRAW MONEY*\n\nAvailable: {available:,} pts\n\nSelect amount:",
        parse_mode='Markdown',
        reply_markup=withdraw_menu(available, is_vip(user))
    )


async def _show_wd_history(query, user):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT points, method, status, requested_at FROM withdrawals "
            "WHERE user_id=? ORDER BY requested_at DESC LIMIT 10",
            (user['telegram_id'],)
        ).fetchall()
    if not rows:
        return await query.edit_message_text(
            "📋 *No withdrawal history yet.*",
            parse_mode='Markdown',
            reply_markup=back_button('withdraw')
        )
    text = "📋 *WITHDRAWAL HISTORY*\n\n"
    status_icons = {'pending':'⏳','processing':'🔄','completed':'✅','rejected':'❌'}
    for row in rows:
        icon = status_icons.get(row['status'], '❓')
        usd = float(Decimal(row['points']) * config.POINTS_TO_USD)
        date = row['requested_at'][:10]
        text += f"{icon} {row['points']} pts (${usd:.2f}) via {row['method'].upper()} — {date}\n"
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=back_button('withdraw'))


async def _handle_daily_bonus(query, context, user):
    now = datetime.datetime.now()
    last = user.get('last_bonus')

    if last:
        try:
            last_dt = datetime.datetime.fromisoformat(last)
            if (now - last_dt).total_seconds() < 86400:
                next_dt = last_dt + datetime.timedelta(days=1)
                diff = (next_dt - now).total_seconds()
                h, m = int(diff // 3600), int((diff % 3600) // 60)
                return await query.edit_message_text(
                    f"⏰ *DAILY BONUS CLAIMED* ⏰\n\nNext bonus in: *{h}h {m}m*",
                    parse_mode='Markdown',
                    reply_markup=main_menu(is_vip(user))
                )
        except Exception:
            pass

    streak = (user.get('streak') or 0) + 1
    bonus = min(config.DAILY_BONUS_BASE + (streak - 1), config.STREAK_MAX_BONUS)
    if is_vip(user):
        bonus = int(bonus * config.VIP_MULTIPLIER)

    update_points(user['telegram_id'], bonus, f"Daily bonus streak {streak}", 'daily_bonus')
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET streak=?, last_bonus=? WHERE telegram_id=?",
            (streak, now.isoformat(), user['telegram_id'])
        )

    await query.edit_message_text(
        f"🎁 *DAILY BONUS!* 🎁\n\n"
        f"💰 +{bonus} points!\n"
        f"🔥 Streak: {streak} days\n"
        f"{'⭐ VIP 2x applied!' if is_vip(user) else ''}\n\n"
        f"Come back tomorrow for more!",
        parse_mode='Markdown',
        reply_markup=main_menu(is_vip(user))
    )


async def _show_ref_stats(query, user):
    with get_db() as conn:
        refs = conn.execute(
            "SELECT u.first_name, u.username, re.points_earned, re.created_at "
            "FROM referral_earnings re JOIN users u ON u.telegram_id = re.referred_id "
            "WHERE re.referrer_id = ? ORDER BY re.created_at DESC LIMIT 10",
            (user['telegram_id'],)
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM referral_earnings WHERE referrer_id=?",
            (user['telegram_id'],)
        ).fetchone()[0]

    text = f"👥 *YOUR REFERRALS* ({total} total)\n\n"
    for row in refs:
        name = row['first_name'] or row['username'] or 'Anonymous'
        date = row['created_at'][:10]
        text += f"👤 {name} — +{row['points_earned']} pts — {date}\n"
    if not refs:
        text += "No referrals yet.\n\nShare your link to earn 50 pts per friend!"

    me = await query.get_bot().get_me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    await query.edit_message_text(
        text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        ])
    )


async def _play_dice(query, context, user):
    player = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1 WHERE telegram_id = ?",
            (user['telegram_id'],)
        )

    if player > bot_roll:
        pts = config.GAMES['dice']['reward']
        if is_vip(user): pts = int(pts * config.VIP_MULTIPLIER)
        update_points(user['telegram_id'], pts, "Dice win", 'game_win')
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET games_won = games_won + 1 WHERE telegram_id = ?",
                (user['telegram_id'],)
            )
        result = f"🎲 You: *{player}* vs Bot: *{bot_roll}*\n\n🎉 *YOU WIN! +{pts} pts!*"
    elif player < bot_roll:
        result = f"🎲 You: *{player}* vs Bot: *{bot_roll}*\n\n💀 *Bot wins. Better luck next time!*"
    else:
        result = f"🎲 You: *{player}* vs Bot: *{bot_roll}*\n\n🤝 *TIE! No points.*"

    await query.edit_message_text(
        result, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Play Again", callback_data="game_dice")],
            [InlineKeyboardButton("🔙 Games", callback_data="games")],
        ])
    )


async def _play_coin(query, context, user):
    result_flip = random.choice(['heads', 'tails'])
    user_choice = random.choice(['heads', 'tails'])  # auto-random for simplicity

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1 WHERE telegram_id = ?",
            (user['telegram_id'],)
        )

    if result_flip == user_choice:
        pts = config.GAMES['coin']['reward']
        if is_vip(user): pts = int(pts * config.VIP_MULTIPLIER)
        update_points(user['telegram_id'], pts, "Coin flip win", 'game_win')
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET games_won = games_won + 1 WHERE telegram_id = ?",
                (user['telegram_id'],)
            )
        text = f"🪙 *{result_flip.upper()}!*\n\nYour pick: {user_choice}\n🎉 *+{pts} pts!*"
    else:
        text = f"🪙 *{result_flip.upper()}!*\n\nYour pick: {user_choice}\n💀 *Better luck next time!*"

    await query.edit_message_text(
        text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🪙 Flip Again", callback_data="game_coin")],
            [InlineKeyboardButton("🔙 Games", callback_data="games")],
        ])
    )


async def _play_mega(query, context, user):
    """Mega spin - rare big win game"""
    rand = random.random()
    if rand < 0.05:
        pts = 100
        result = "👑 *JACKPOT! +100 pts!*"
    elif rand < 0.15:
        pts = 50
        result = "🚀 *MEGA WIN! +50 pts!*"
    elif rand < 0.35:
        pts = 25
        result = "💰 *BIG WIN! +25 pts!*"
    else:
        pts = 0
        result = "💀 *No win. Try again!*"

    if pts > 0:
        if is_vip(user): pts = int(pts * config.VIP_MULTIPLIER)
        update_points(user['telegram_id'], pts, "Mega spin", 'game_win')
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET total_games=total_games+1, games_won=games_won+1 WHERE telegram_id=?",
                (user['telegram_id'],)
            )
    else:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET total_games = total_games + 1 WHERE telegram_id = ?",
                (user['telegram_id'],)
            )

    await query.edit_message_text(
        f"🎰 *MEGA SPIN*\n\n{result}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Spin Again", callback_data="game_mega")],
            [InlineKeyboardButton("🔙 Games", callback_data="games")],
        ])
    )


async def _handle_admin_cb(query, context, user, data):
    if data == 'admin_stats':
        stats = get_stats()
        text = (
            f"📊 *BOT STATISTICS*\n\n"
            f"👥 Total Users: {stats['total_users']:,}\n"
            f"📅 Today New: {stats['today_users']:,}\n"
            f"✅ Active Today: {stats['active_today']:,}\n"
            f"💰 Total Points: {stats['total_points']:,}\n"
            f"📈 Total Earned: {stats['total_earned']:,}\n"
            f"⭐ VIP Users: {stats['vip_users']:,}\n"
            f"🎰 Spins Today: {stats['spins_today']:,}\n"
            f"⏳ Pending WDs: {stats['pending_count']} ({stats['pending_points']:,} pts)"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=admin_menu())

    elif data == 'admin_wd':
        with get_db() as conn:
            rows = conn.execute(
                "SELECT w.id, w.user_id, w.points, w.net_amount, w.method, w.payment_details, "
                "u.first_name FROM withdrawals w JOIN users u ON u.telegram_id = w.user_id "
                "WHERE w.status='pending' ORDER BY w.requested_at LIMIT 10"
            ).fetchall()
        if not rows:
            return await query.edit_message_text(
                "✅ No pending withdrawals!", reply_markup=admin_menu()
            )
        text = "💰 *PENDING WITHDRAWALS*\n\n"
        for row in rows:
            text += (
                f"ID#{row['id']} | {row['first_name']} | {row['points']} pts | "
                f"${row['net_amount']:.2f} | {row['method']} | `{row['payment_details']}`\n"
            )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=admin_menu())

    elif data == 'admin_broadcast':
        context.user_data['state'] = 'broadcast'
        await query.edit_message_text(
            "📣 *BROADCAST*\n\nSend the message to broadcast to all users:\n(Supports Markdown)",
            parse_mode='Markdown',
            reply_markup=back_button('admin_stats')
        )

    elif data == 'admin_users':
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            banned = conn.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
            vip = conn.execute("SELECT COUNT(*) FROM users WHERE vip_until > datetime('now')").fetchone()[0]
        await query.edit_message_text(
            f"👥 *USER MANAGEMENT*\n\nTotal: {total:,}\nBanned: {banned}\nVIP: {vip}",
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    init_database()

    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not set! Set BOT_TOKEN env variable.")
        sys.exit(1)

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("spin",        cmd_spin))
    app.add_handler(CommandHandler("refer",       cmd_refer))
    app.add_handler(CommandHandler("withdraw",    cmd_withdraw))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("admin",       cmd_admin))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_router))

    # Messages (tool input, game guesses, broadcast)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    logger.info("🚀 FlowX Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
