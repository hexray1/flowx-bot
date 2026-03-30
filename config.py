# ═══════════════════════════════════════════════════════════
# FLOWX BOT - ULTIMATE CONFIGURATION (FIXED)
# ═══════════════════════════════════════════════════════════

import os
from decimal import Decimal

# ─── BOT CORE ───
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "5350231648").split(",")]
ADMIN_ID = ADMIN_IDS[0]
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_TOKEN", "")

# ─── MONEY SYSTEM ───
POINTS_TO_USD = Decimal('0.01')      # 1 point = $0.01
MIN_WITHDRAWAL = 500                  # Minimum $5
MAX_WITHDRAWAL_DAILY = 5000          # Daily limit $50
VIP_PRICE_CENTS = 299                # $2.99
VIP_MULTIPLIER = 2.0                 # 2x earnings
VIP_DURATION_DAYS = 30

# ─── ECONOMY BALANCING ───
SPIN_COOLDOWN_HOURS = 3
DAILY_BONUS_BASE = 5
STREAK_MAX_BONUS = 15                # Day 7+ = 15 points
REFERRAL_REWARD = 50                 # Points per referral
TOOL_USE_REWARD = 2                  # Points per tool
GAME_WIN_REWARD = 20                 # Points per win

# ─── REWARD TIERS ───
SPIN_REWARDS = [
    (0.30, 1,   "💎 COMMON",    "Keep spinning!"),
    (0.25, 5,   "🎁 UNCOMMON",  "Nice!"),
    (0.20, 10,  "🔥 RARE",      "Great!"),
    (0.15, 25,  "💰 EPIC",      "Amazing!"),
    (0.08, 50,  "🚀 LEGENDARY", "Incredible!"),
    (0.02, 100, "👑 MYTHIC",    "JACKPOT!"),
]

REFERRAL_TIERS = {
    1: 50,
    5: 300,
    10: 700,
    25: 2000,
    50: 5000,
    100: 12000,
}

# ─── PAYMENT METHODS ───
PAYMENT_METHODS = {
    'upi':    {'min': 500,  'fee': 0,  'time': '24h'},
    'paypal': {'min': 1000, 'fee': 5,  'time': '48h'},
    'usdt':   {'min': 1000, 'fee': 2,  'time': '12h'},
    'btc':    {'min': 2000, 'fee': 5,  'time': '24h'},
    'bank':   {'min': 5000, 'fee': 10, 'time': '3-5 days'},
}

# ─── VIRAL SETTINGS ───
VIRAL_MESSAGE = """
🚀 *I just earned ${amount} with FlowX Bot!*

💰 Free daily spins
👥 Refer friends = $0.50 each
⚡ 30+ tools + games

👇 *Try FREE:*
{link}
"""

LEADERBOARD_PRIZES = {
    1: {'points': 1000, 'money': 10, 'badge': '👑 KING'},
    2: {'points': 500,  'money': 5,  'badge': '🥈 PRINCE'},
    3: {'points': 300,  'money': 3,  'badge': '🥉 LORD'},
}

# ─── ADS CONFIG ───
ADS = [
    {'id': 1, 'title': '🎬 Watch Video (30s)', 'points': 10, 'url': 'https://youtube.com'},
    {'id': 2, 'title': '📱 Install App',        'points': 50, 'url': 'https://play.google.com'},
    {'id': 3, 'title': '🌐 Visit Website',      'points': 5,  'url': 'https://google.com'},
    {'id': 4, 'title': '📋 Quick Survey',       'points': 100,'url': 'https://forms.google.com'},
]

# ─── TOOLS LIST ───
TOOLS = {
    'url':     {'name': '🔗 URL Shortener',       'emoji': '🔗', 'reward': 2},
    'qr':      {'name': '📸 QR Generator',        'emoji': '📸', 'reward': 2},
    'dl':      {'name': '⬇️ YT/IG Downloader',    'emoji': '⬇️', 'reward': 5},
    'calc':    {'name': '🔢 Calculator',           'emoji': '🔢', 'reward': 1},
    'unit':    {'name': '🔄 Unit Converter',       'emoji': '🔄', 'reward': 1},
    'weather': {'name': '☁️ Weather',              'emoji': '☁️', 'reward': 1},
    'pass':    {'name': '🔐 Password Gen',         'emoji': '🔐', 'reward': 1},
    'notes':   {'name': '📝 Notes',                'emoji': '📝', 'reward': 1},
    'traffic': {'name': '🌐 Site Analyzer',        'emoji': '🌐', 'reward': 3},
}

# ─── GAMES ───
GAMES = {
    'guess': {'name': '🎯 Guess Number', 'reward': 20, 'cost': 0},
    'dice':  {'name': '🎲 Lucky Dice',   'reward': 10, 'cost': 5},
    'coin':  {'name': '🪙 Coin Flip',    'reward': 15, 'cost': 5},
}

# ─── MESSAGES ───
MESSAGES = {
    'welcome_new': """
🚀 *Welcome {name} to FLOWX!* 🚀

💰 *The Bot That Pays You!*

🎁 *You Got: {points} Points* = ${money}

*Start Earning:*
🎰 /spin - Win up to 100 pts
👥 /refer - 50 pts per friend
⚡ /tools - Earn using utilities
💸 /withdraw - Cash out real money

🔥 *{referrals} people earned today!*
""",

    'welcome_back': """
⚡ *Welcome back, {name}!* ⚡

💰 Balance: {points} pts = ${money:.2f}
📈 Total Earned: {earned} pts

🎰 /spin | 👥 /refer | 💸 /withdraw
""",
}

# ─── TIMING ───
CLEANUP_INTERVAL = 86400
BACKUP_INTERVAL = 3600
STATS_INTERVAL = 300

# ─── FEATURE FLAGS ───
FEATURES = {
    'spin': True,
    'referral': True,
    'vip': True,
    'withdrawal': True,
    'games': True,
    'ads': True,
    'tools': True,
    'leaderboard': True,
    'streak': True,
}
