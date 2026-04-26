import os
import time
import requests
import numpy as np
from datetime import datetime

# ═══════════════════════════════════════════

# CONFIGURATION — Remplace par tes vraies valeurs

# ═══════════════════════════════════════════

TELEGRAM_TOKEN = os.environ.get(“TELEGRAM_TOKEN”, “TON_TOKEN_ICI”)
TELEGRAM_CHAT_ID = os.environ.get(“TELEGRAM_CHAT_ID”, “TON_CHAT_ID_ICI”)

# Paires à scanner

PAIRS = [
“BTCUSDT”, “ETHUSDT”, “BNBUSDT”, “SOLUSDT”, “XRPUSDT”,
“ADAUSDT”, “DOGEUSDT”, “AVAXUSDT”, “LINKUSDT”, “DOTUSDT”,
“LTCUSDT”, “ATOMUSDT”, “NEARUSDT”, “UNIUSDT”, “MATICUSDT”
]

# Paramètres stratégie

BB_PERIOD   = 20
BB_MULT     = 2.0
RSI_PERIOD  = 14
RSI_LEVEL   = 50
SCAN_INTERVAL = 300  # Scan toutes les 5 minutes

# ═══════════════════════════════════════════

# FONCTIONS UTILITAIRES

# ═══════════════════════════════════════════

def send_telegram(message):
“”“Envoie un message sur Telegram”””
url = f”https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage”
data = {
“chat_id”: TELEGRAM_CHAT_ID,
“text”: message,
“parse_mode”: “HTML”
}
try:
res = requests.post(url, data=data, timeout=10)
return res.status_code == 200
except Exception as e:
print(f”Erreur Telegram: {e}”)
return False

def get_candles(symbol, interval, limit=100):
“”“Récupère les bougies depuis Binance”””
url = f”https://api.binance.com/api/v3/klines”
params = {“symbol”: symbol, “interval”: interval, “limit”: limit}
try:
res = requests.get(url, params=params, timeout=10)
data = res.json()
closes = [float(c[4]) for c in data]
highs  = [float(c[2]) for c in data]
lows   = [float(c[3]) for c in data]
return closes, highs, lows
except Exception as e:
print(f”Erreur Binance {symbol}: {e}”)
return None, None, None

def calc_bb(closes, period=20, mult=2.0):
“”“Calcule les Bandes de Bollinger”””
if len(closes) < period:
return None, None, None
closes_arr = np.array(closes[-period:])
mean = np.mean(closes_arr)
std  = np.std(closes_arr)
return mean + mult * std, mean, mean - mult * std

def calc_rsi(closes, period=14):
“”“Calcule le RSI”””
if len(closes) < period + 1:
return None
closes_arr = np.array(closes)
deltas = np.diff(closes_arr)
gains  = np.where(deltas > 0, deltas, 0)
losses = np.where(deltas < 0, -deltas, 0)
avg_gain = np.mean(gains[-period:])
avg_loss = np.mean(losses[-period:])
if avg_loss == 0:
return 100
rs = avg_gain / avg_loss
return 100 - (100 / (1 + rs))

def detect_rsi_double_cross(closes_5m, period=14, level=50):
“”“Détecte la double cassure du RSI au niveau 50”””
rsi_values = []
for i in range(period + 1, len(closes_5m)):
rsi = calc_rsi(closes_5m[:i], period)
if rsi is not None:
rsi_values.append(rsi)

```
if len(rsi_values) < 4:
    return False, None

crosses = []
for i in range(1, len(rsi_values)):
    if rsi_values[i-1] <= level < rsi_values[i]:
        crosses.append("up")
    elif rsi_values[i-1] >= level > rsi_values[i]:
        crosses.append("down")

if len(crosses) >= 2:
    last2 = crosses[-2:]
    if last2[0] == last2[1] == "up":
        return True, "buy"
    if last2[0] == last2[1] == "down":
        return True, "sell"

return False, None
```

def calc_fibonacci(highs, lows, direction):
“”“Calcule les niveaux Fibonacci”””
recent_high = max(highs[-20:])
recent_low  = min(lows[-20:])
fib_range   = recent_high - recent_low

```
levels = {
    "0":    recent_low,
    "23.6": recent_low + fib_range * 0.236,
    "38.2": recent_low + fib_range * 0.382,
    "50.0": recent_low + fib_range * 0.500,
    "61.8": recent_low + fib_range * 0.618,
    "161.8": recent_low + fib_range * 1.618,
}
return levels
```

def is_near_fib236(price, fib_levels, tolerance=0.005):
“”“Vérifie si le prix est proche du niveau 23.6%”””
fib_236 = fib_levels[“23.6”]
return abs(price - fib_236) / price < tolerance

def format_price(price):
if price > 1000:
return f”{price:,.2f}”
elif price > 1:
return f”{price:.4f}”
else:
return f”{price:.6f}”

# ═══════════════════════════════════════════

# ANALYSE PRINCIPALE

# ═══════════════════════════════════════════

def analyze_pair(symbol):
“”“Analyse complète d’une paire selon ta stratégie”””
pair_name = symbol.replace(“USDT”, “/USDT”)

```
# Données H1 pour BB
closes_h1, highs_h1, lows_h1 = get_candles(symbol, "1h", 100)
if not closes_h1:
    return None

# Données 5min pour RSI
closes_5m, _, _ = get_candles(symbol, "5m", 50)
if not closes_5m:
    return None

current_price = closes_h1[-1]
prev_price    = closes_h1[-2] if len(closes_h1) > 1 else current_price
change_24h    = ((current_price - closes_h1[-24]) / closes_h1[-24] * 100) if len(closes_h1) >= 24 else 0

# Calcul BB sur H1
bb_upper, bb_mid, bb_lower = calc_bb(closes_h1, BB_PERIOD, BB_MULT)
if bb_upper is None:
    return None

# Détection sortie BB
bb_breakout_buy  = closes_h1[-1] > bb_upper  # Bougie clôture au-dessus BB haute
bb_breakout_sell = closes_h1[-1] < bb_lower  # Bougie clôture en-dessous BB basse

# RSI double cassure sur 5min
rsi_crossed, rsi_direction = detect_rsi_double_cross(closes_5m, RSI_PERIOD, RSI_LEVEL)
current_rsi = calc_rsi(closes_5m, RSI_PERIOD)

# Niveaux Fibonacci
direction = "buy" if bb_breakout_buy else "sell" if bb_breakout_sell else None
fib_levels = calc_fibonacci(highs_h1, lows_h1, direction)

# Retest 23.6% (entrée optimale)
near_236 = is_near_fib236(current_price, fib_levels)
optimal_entry = near_236 and current_rsi is not None and (
    (current_rsi > RSI_LEVEL and current_price > bb_mid) or
    (current_rsi < RSI_LEVEL and current_price < bb_mid)
)

# Détermination du signal
signal = None
strength = 0

if bb_breakout_buy and rsi_crossed and rsi_direction == "buy":
    signal = "BUY"
    strength = 5
elif bb_breakout_sell and rsi_crossed and rsi_direction == "sell":
    signal = "SELL"
    strength = 5
elif optimal_entry and current_price > bb_mid:
    signal = "OPTIMAL_BUY"
    strength = 4
elif optimal_entry and current_price < bb_mid:
    signal = "OPTIMAL_SELL"
    strength = 4
elif bb_breakout_buy or (rsi_crossed and rsi_direction == "buy"):
    signal = "WATCH_BUY"
    strength = 2
elif bb_breakout_sell or (rsi_crossed and rsi_direction == "sell"):
    signal = "WATCH_SELL"
    strength = 2

return {
    "pair": pair_name,
    "price": current_price,
    "change_24h": change_24h,
    "signal": signal,
    "strength": strength,
    "bb_upper": bb_upper,
    "bb_mid": bb_mid,
    "bb_lower": bb_lower,
    "rsi": current_rsi,
    "rsi_crossed": rsi_crossed,
    "rsi_direction": rsi_direction,
    "fib_levels": fib_levels,
    "near_fib236": near_236,
}
```

def build_message(result):
“”“Construit le message Telegram”””
p = result[“pair”]
price = format_price(result[“price”])
change = result[“change_24h”]
rsi = result[“rsi”]
fib = result[“fib_levels”]
signal = result[“signal”]

```
change_emoji = "📈" if change >= 0 else "📉"
change_str = f"{'+' if change >= 0 else ''}{change:.2f}%"

tp1 = format_price(fib["38.2"])
tp2 = format_price(fib["161.8"])
sl  = format_price(fib["0"])
entry = format_price(fib["23.6"])

if signal == "BUY":
    msg = f"""🟢 <b>SIGNAL ACHAT — {p}</b>
```

💰 Prix: <b>{price}</b> {change_emoji} {change_str}
📊 RSI 5min: <b>{rsi:.1f}</b> (double cassure ↑50 ✅)
📈 BB H1: <b>Sortie haute ✅</b>

🎯 <b>NIVEAUX:</b>
├ Entrée optimale: {entry} (Fib 23.6%)
├ TP1: {tp1} (Fib 38.2%)
├ TP2: {tp2} (Fib 161.8%)
└ SL: {sl} (Fib 0%)

⏰ {datetime.now().strftime(’%H:%M:%S’)}”””

```
elif signal == "SELL":
    msg = f"""🔴 <b>SIGNAL VENTE — {p}</b>
```

💰 Prix: <b>{price}</b> {change_emoji} {change_str}
📊 RSI 5min: <b>{rsi:.1f}</b> (double cassure ↓50 ✅)
📉 BB H1: <b>Sortie basse ✅</b>

🎯 <b>NIVEAUX:</b>
├ Entrée optimale: {entry} (Fib 23.6%)
├ TP1: {tp1} (Fib 38.2%)
├ TP2: {tp2} (Fib 161.8%)
└ SL: {sl} (Fib 0%)

⏰ {datetime.now().strftime(’%H:%M:%S’)}”””

```
elif signal == "OPTIMAL_BUY":
    msg = f"""⭐ <b>ENTRÉE OPTIMALE ACHAT — {p}</b>
```

💰 Prix: <b>{price}</b> — Au niveau Fib 23.6% !
📊 RSI 5min: <b>{rsi:.1f}</b>
🎯 C’est le meilleur moment pour entrer !

├ TP1: {tp1} (Fib 38.2%)
├ TP2: {tp2} (Fib 161.8%)
└ SL: {sl} (Fib 0%)

⏰ {datetime.now().strftime(’%H:%M:%S’)}”””

```
elif signal == "OPTIMAL_SELL":
    msg = f"""⭐ <b>ENTRÉE OPTIMALE VENTE — {p}</b>
```

💰 Prix: <b>{price}</b> — Au niveau Fib 23.6% !
📊 RSI 5min: <b>{rsi:.1f}</b>
🎯 C’est le meilleur moment pour entrer !

├ TP1: {tp1} (Fib 38.2%)
├ TP2: {tp2} (Fib 161.8%)
└ SL: {sl} (Fib 0%)

⏰ {datetime.now().strftime(’%H:%M:%S’)}”””

```
else:
    return None

return msg
```

# ═══════════════════════════════════════════

# BOUCLE PRINCIPALE

# ═══════════════════════════════════════════

def main():
print(“🤖 Trading Bot démarré !”)
print(f”📊 Surveillance de {len(PAIRS)} paires”)
print(f”⏱ Scan toutes les {SCAN_INTERVAL//60} minutes\n”)

```
send_telegram(f"""🤖 <b>Trading Bot démarré !</b>
```

📊 Surveillance de {len(PAIRS)} paires
⏱ Scan toutes les {SCAN_INTERVAL//60} minutes
📈 Stratégie: BB H1 + RSI 5min double cassure 50 + Fibonacci

Paires: {’, ’.join([p.replace(‘USDT’, ‘/USDT’) for p in PAIRS])}”””)

```
already_alerted = {}  # Évite les doublons d'alertes

while True:
    print(f"\n🔍 Scan en cours — {datetime.now().strftime('%H:%M:%S')}")

    for symbol in PAIRS:
        try:
            result = analyze_pair(symbol)
            if not result:
                continue

            signal = result["signal"]
            pair   = result["pair"]

            # Ignore les signaux WATCH et None
            if not signal or "WATCH" in signal:
                print(f"  ⬜ {pair}: {signal or 'Pas de signal'}")
                continue

            # Évite d'envoyer 2x la même alerte
            last_alert = already_alerted.get(pair)
            if last_alert == signal:
                print(f"  ⏭ {pair}: {signal} (déjà alerté)")
                continue

            # Envoie l'alerte
            msg = build_message(result)
            if msg:
                sent = send_telegram(msg)
                if sent:
                    already_alerted[pair] = signal
                    print(f"  ✅ {pair}: {signal} — Alerte envoyée !")
                else:
                    print(f"  ❌ {pair}: Erreur envoi Telegram")

            time.sleep(0.5)  # Évite le rate limiting Binance

        except Exception as e:
            print(f"  ❌ Erreur {symbol}: {e}")

    print(f"✅ Scan terminé — Prochain dans {SCAN_INTERVAL//60} min")
    time.sleep(SCAN_INTERVAL)
```

if **name** == “**main**”:
main()
