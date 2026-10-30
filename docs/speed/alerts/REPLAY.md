# A131 replay: ZONE line + day type, and TOP / BOTTOM BAN SAKTA (3 of 4)

Built 2026-10-28 02:35 by `docs/speed/alerts/replay_alerts.py` (read-only, causal). Rows, not rates.
Points after = spot at the close + 15 / + 30 min minus spot at the close, in the alert's way (TOP / SELL = down).
DECODE (day type, ZONE chip) is recomputed by `server._decode_all` at each close with `band_rotation.ZONE3_FROM` moved
in-process only (live it starts 28 Oct). Band = faded.vwaps + hold2.sigmas on the GoCharting 5-min fut bars.

BAN SAKTA (Fable's review, 28 Oct): writers at the extreme strike = WHO OPENED writers + the day's biggest 10-min add
there; fut OI FLAT or COVER passes, FRESH fails; sigma only after 30 min; one per bar and side; NIFTY only; on a
§1o TREND against the call it needs 4/4; the first 3 a day go to Telegram, the rest to the window.

## Per day

| day | P marks (one per bar + side) | P at the extreme | BAN SAKTA lines | to Telegram | ZONE alerts |
|---|---|---|---|---|---|
| 2026-09-22 | 12 | 8 | 2 | 2 | not replayed |
| 2026-09-23 | 9 | 5 | 1 | 1 | not replayed |
| 2026-09-24 | 14 | 8 | 3 | 3 | not replayed |
| 2026-09-25 | 7 | 2 | 0 | 0 | not replayed |
| 2026-09-28 | 24 | 15 | 0 | 0 | not replayed |
| 2026-09-29 | 6 | 2 | 0 | 0 | not replayed |
| 2026-09-30 | 16 | 11 | 9 | 3 | not replayed |
| 2026-10-01 | 15 | 7 | 2 | 2 | 20 |
| 2026-10-05 | 6 | 4 | 4 | 3 | not replayed |
| 2026-10-06 | 5 | 3 | 0 | 0 | not replayed |
| 2026-10-07 | 5 | 4 | 1 | 1 | not replayed |
| 2026-10-08 | 5 | 3 | 0 | 0 | not replayed |
| 2026-10-09 | 8 | 4 | 0 | 0 | not replayed |
| 2026-10-12 | 3 | 3 | 1 | 1 | not replayed |
| 2026-10-16 | 2 | 2 | 1 | 1 | not replayed |
| 2026-10-19 | 5 | 4 | 1 | 1 | 13 |
| 2026-10-21 | 1 | 1 | 0 | 0 | 13 |
| 2026-10-22 | 7 | 5 | 1 | 1 | 12 |
| 2026-10-23 | 6 | 2 | 0 | 0 | 2 |
| 2026-10-26 | 1 | 0 | 0 | 0 | 7 |
| 2026-10-27 | 7 | 5 | 3 | 3 | 18 |

## ALERT 2 · every TOP / BOTTOM BAN SAKTA line (TG = sent to Telegram, window = past the day budget)

| day | P | | line | +15 | +30 |
|---|---|---|---|---|---|
| 2026-09-22 | 09:50 | TG | `09:55  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 23,473f · zone SELL armed 23,471s · +2.2σ · ✗ push nahi · put 23,450 +31.2L · aaj ka max nahi · fut OI flat +35 lots · din MIXED: saaf nahi` | −10 | +13 |
| 2026-09-22 | 10:45 | TG | `10:50  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 23,380f · zone BUY armed 23,397s · −2.1σ · call writers 23,350 +41.0L · aaj ka max · ✗ fut OI fresh +278 lots · din MIXED: saaf nahi` | −1 | +8 |
| 2026-09-23 | 10:40 | TG | `10:45  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 23,442f · zone SELL armed 23,443s · +2.2σ · ✗ push 10:38 +661 jawab nahi · pehle koi toot nahi · put 23,400 +8.4L · aaj ka max nahi · fut OI flat −229 lots · din MIXED: saaf nahi` | −2 | −23 |
| 2026-09-24 | 10:00 | TG | `10:05  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 23,224f · zone BUY trigger 23,242s · −2.1σ · ✗ push 09:52 −169 jawab nahi · pehle koi toot nahi · call 23,200 +7.5L · aaj ka max nahi · fut OI cover −555 lots · din MIXED: saaf nahi` | −16 | −7 |
| 2026-09-24 | 13:30 | TG | `13:35  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 23,158f · zone BUY trigger 23,175s · −2.9σ · ✗ push 13:26 −365 jawab nahi · pehle koi toot nahi · call 23,150 +7.8L · kharidar · fut OI flat +133 lots · din CHOP: palat ki ummeed` | −51 | −94 |
| 2026-09-24 | 14:30 | TG | `14:35  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 23,076f · zone BUY trigger 23,085s · −2σ · ✗ push nahi · call 23,050 +2.3L · fut OI fresh ulta +462 lots · din CHOP: palat ki ummeed` | +23 | +29 |
| 2026-09-30 | 09:55 | TG | `10:00  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,820f · zone BUY match · −2.6σ · ✗ push 09:52 −252 jawab nahi · pehle koi toot nahi · call 22,700 +1.4L · fut OI fresh ulta +1,171 lots · din PIN: palat ki ummeed` | +31 | +35 |
| 2026-09-30 | 10:20 | TG | `10:25  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,885f · zone SELL armed 22,880s · +2.6σ · ✗ push 10:14 +168 jawab nahi · pehle koi toot nahi · put 22,750 +3.8L · aaj ka max nahi · fut OI cover −584 lots · din PIN: palat ki ummeed` | +34 | +45 |
| 2026-09-30 | 10:25 | TG | `10:30  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,896f · zone SELL trigger 22,880s · +3σ · ✗ push 10:21 +176 jawab nahi · pehle koi toot nahi · put 22,800 +7.2L · kharidar · fut OI flat +29 lots · din PIN: palat ki ummeed` | +54 | +70 |
| 2026-09-30 | 11:00 | window | `11:05  NIFTY  BOTTOM BAN SAKTA ▲ 4/4 · P 22,800f · zone BUY trigger 22,839s · −2.5σ · push 10:34 toot −6.4L → 10:57 −279 jawab nahi · fut OI fresh ulta +601 lots · din PIN: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | −42 | −13 |
| 2026-09-30 | 11:20 | window | `11:25  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,781f · zone BUY armed 22,793s · −2.8σ · call writers 22,650 +4.8L · aaj ka max · ✗ fut OI fresh +484 lots · din CHOP: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | +23 | +35 |
| 2026-09-30 | 12:40 | window | `12:45  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,900f · zone SELL armed 22,887s · +2.5σ · ✗ push 12:37 +158 toot −4.5L · put 22,800 +6.0L · aaj ka max nahi · fut OI cover −459 lots · din CHOP: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | −18 | −5 |
| 2026-09-30 | 12:50 | window | `12:55  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,926f · zone SELL armed 22,902s · +2.2σ · put writers 22,800 +9.3L · aaj ka max · ✗ fut OI fresh +2,496 lots · din CHOP: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | +0 | +6 |
| 2026-09-30 | 13:00 | window | `13:05  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,920f · zone SELL armed · +2σ · ✗ push nahi · put 22,800 +3.0L · aaj ka max nahi · fut OI flat −57 lots · din CHOP: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | +9 | +10 |
| 2026-09-30 | 14:45 | window | `14:50  NIFTY  BOTTOM BAN SAKTA ▲ 4/4 · P 22,700f · zone BUY trigger 22,719s · −2.4σ · push 14:36 toot −4.2L → 14:40 −187 jawab nahi · fut OI fresh ulta +1,452 lots · din CHOP: palat ki ummeed · Telegram nahi: aaj ke 3 ho gaye` | −11 | −35 |
| 2026-10-01 | 10:10 | TG | `10:15  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,700f · zone SELL trigger 22,657s · +2.9σ · put writers 22,600 +7.3L · aaj ka max · ✗ fut OI fresh +459 lots · din MIXED: saaf nahi` | +15 | +8 |
| 2026-10-01 | 12:30 | TG | `12:35  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,550f · zone BUY armed 22,566s · −2.4σ · push 12:21 toot −4.4L → 12:28 −198 jawab nahi + call writers 22,450 +6.7L · aaj ka max · ✗ fut OI fresh +1,064 lots · din CHOP: palat ki ummeed` | −100 | −100 |
| 2026-10-05 | 10:30 | TG | `10:35  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,595f · zone BUY trigger 22,652s · −3σ · push 10:22 toot −27.5L → 10:26 −746 jawab nahi + call writers 22,450 +7.7L · aaj ka max · ✗ fut OI fresh +365 lots · din MIXED: saaf nahi` | −44 | −34 |
| 2026-10-05 | 11:00 | TG | `11:05  NIFTY  BOTTOM BAN SAKTA ▲ 4/4 · P 22,580f · zone BUY trigger 22,618s · −2.5σ · push 10:39 toot −10.3L → 10:56 −261 jawab nahi · fut OI fresh ulta +343 lots · din MIXED: saaf nahi` | −16 | +12 |
| 2026-10-05 | 12:00 | TG | `12:05  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,555f · zone BUY armed 22,561s · −2.2σ · call writers 22,450 +12.4L · aaj ka max · ✗ fut OI fresh +540 lots · din MIXED: saaf nahi` | −16 | +1 |
| 2026-10-05 | 12:10 | window | `12:15  NIFTY  BOTTOM BAN SAKTA ▲ 4/4 · P 22,515f · zone BUY armed 22,551s · −2.8σ · call writers 22,400 +15.2L · aaj ka max · fut OI flat +270 lots · din MIXED: saaf nahi · Telegram nahi: aaj ke 3 ho gaye` | +40 | +35 |
| 2026-10-07 | 13:15 | TG | `13:20  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,600f · zone BUY trigger 22,640s · −2.2σ · call writers 22,550 +7.7L · aaj ka max · ? fut OI · din CHOP: palat ki ummeed` | +8 | +20 |
| 2026-10-12 | 10:20 | TG | `10:25  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,525f · zone BUY armed · ✗ −1.4σ · push 09:52 toot −32.0L → 10:18 −161 jawab nahi · fut OI flat +200 lots · din MIXED: saaf nahi` | −18 | −55 |
| 2026-10-16 | 09:40 | TG | `09:45  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,915f · zone BUY match · ✗ −1.7σ · push 09:32 phans +6.3L → 09:36 −714 deewar tiki +11.9L + call writers 22,900 +14.0L · aaj ka max · fut OI fresh ulta +502 lots · din MIXED: saaf nahi` | ? | ? |
| 2026-10-19 | 11:45 | TG | `11:50  NIFTY  BOTTOM BAN SAKTA ▲ 3/4 · P 22,970f · zone BUY armed 22,975s · −2.2σ · ✗ push 11:39 −356 toot −30.9L · call 22,950 +14.0L · aaj ka max nahi · fut OI flat +210 lots · din CHOP: palat ki ummeed` | −50 | −64 |
| 2026-10-22 | 10:25 | TG | `10:30  NIFTY  TOP BAN SAKTA ▼ 4/4 · P 22,775f · zone SELL armed 22,750s · +2.3σ · put writers 22,750 +3.7L · aaj ka max · fut OI cover −1,055 lots · din CHOP: palat ki ummeed` | −2 | −23 |
| 2026-10-27 | 10:05 | TG | `10:10  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,810f · zone SELL trigger 22,776s · ✗ +1.8σ · put writers 22,800 +30.8L · aaj ka max · fut OI cover −863 lots · din MIXED: saaf nahi` | +75 | +13 |
| 2026-10-27 | 12:45 | TG | `12:50  NIFTY  TOP BAN SAKTA ▼ 4/4 · P 22,840f · zone SELL armed 22,820s · +2.8σ · push 12:40 toot −59.4L → 12:44 +170 jawab nahi + put writers 22,850 +22.6L · aaj ka max · fut OI cover −2,860 lots · din CHOP: palat ki ummeed` | +52 | +98 |
| 2026-10-27 | 15:25 | TG | `15:30  NIFTY  TOP BAN SAKTA ▼ 3/4 · P 22,815f · zone SELL trigger 22,778s · ✗ +1.7σ · push 14:59 toot −13.8L → 15:20 +442 deewar tiki +25.2L · fut OI cover −796 lots · din CHOP: palat ki ummeed · 3 baje ke baad` | ? | ? |

## P at the extreme that did NOT reach its bar (3 of 4, or 4 of 4 on a trend against it): not sent

| day | idx | P | swing | n / need | ? | zone | band | thakan | fut OI | din | +15 | +30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-22 | NIFTY | 09:30 @ 23,437f | BOTTOM | 2 / 3 | 2 | ✓ zone BUY armed 23,437s | ? σ | ? push ? · call 23,450 +43.4L · kharidar | ✓ fut OI flat −34 lots | MIXED | +18 | +25 |
| 2026-09-22 | NIFTY | 09:45 @ 23,470f | TOP | 2 / 3 | 0 | ✓ zone SELL armed 23,471s | ✗ +1.9σ | ✗ push nahi · put 23,450 +39.5L · aaj ka max nahi | ✓ fut OI flat +104 lots | MIXED | −7 | −3 |
| 2026-09-22 | NIFTY | 14:20 @ 23,405f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.2σ | ✗ push 14:18 +198 toot −13.3L · put 23,400 +62.2L · aaj ka max nahi | ✓ fut OI cover −3,340 lots | TREND ▼ | −5 | +1 |
| 2026-09-22 | NIFTY | 14:25 @ 23,420f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.5σ | ✗ push 14:18 +198 toot −13.3L · put 23,400 +24.2L · aaj ka max nahi | ✓ fut OI flat +61 lots | TREND ▼ | +25 | +39 |
| 2026-09-22 | NIFTY | 14:35 @ 23,414f | TOP | 0 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.4σ | ✗ push nahi · put 23,400 +12.3L · aaj ka max nahi | ✗ fut OI fresh +412 lots | MIXED | +6 | +29 |
| 2026-09-22 | NIFTY | 15:40 @ 23,416f | TOP | 0 / 3 | 2 | ✗ zone SELL nahi | ✗ +0.6σ | ? push ? · put likhai ? | ? fut OI | ? | ? | ? |
| 2026-09-23 | NIFTY | 10:25 @ 23,428f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.7σ | ✗ push nahi · put 23,400 +8.3L · aaj ka max nahi | ✓ fut OI flat −201 lots | MIXED | −14 | −16 |
| 2026-09-23 | NIFTY | 11:00 @ 23,445f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.9σ | ✗ push nahi · put 23,450 +2.5L | ✓ fut OI flat +28 lots | MIXED | −4 | −21 |
| 2026-09-23 | NIFTY | 11:35 @ 23,460f | TOP | 2 / 4 | 0 | ✗ zone SELL nahi | ✓ +2.2σ | ✗ push 11:32 +165 jawab nahi · pehle koi toot nahi · put 23,450 +3.3L · aaj ka max nahi | ✓ fut OI flat −30 lots | TREND ▲ | +10 | −9 |
| 2026-09-23 | NIFTY | 14:50 @ 23,440f | BOTTOM | 0 / 3 | 0 | ✗ zone BUY nahi | ✗ +0σ | ✗ push 14:48 −208 jawab nahi · pehle koi toot nahi · call 23,400 +2.6L | ✗ fut OI fresh +409 lots | TREND ▲ | −13 | +0 |
| 2026-09-24 | NIFTY | 09:45 @ 23,238f | BOTTOM | 1 / 3 | 0 | ✓ zone BUY armed 23,226s | ✗ −1.6σ | ✗ push 09:45 −348 jawab nahi · pehle koi toot nahi · call 23,250 +13.8L · aaj ka max nahi | ✗ fut OI fresh +1,055 lots | MIXED | −3 | −19 |
| 2026-09-24 | NIFTY | 09:50 @ 23,226f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY armed 23,226s | ✓ −2.1σ | ✗ push 09:45 −348 jawab nahi · pehle koi toot nahi · call 23,200 +11.8L · aaj ka max nahi | ✗ fut OI fresh +558 lots | MIXED | +21 | −9 |
| 2026-09-24 | NIFTY | 10:30 @ 23,220f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY trigger 23,244s | ✗ −1.8σ | ✗ push nahi · call 23,200 +1.5L | ✓ fut OI fresh ulta +389 lots | MIXED | +3 | +5 |
| 2026-09-24 | NIFTY | 14:55 @ 23,140f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.8σ | ✗ push nahi · put 23,100 +2.4L | ✓ fut OI cover −596 lots | CHOP | +14 | +35 |
| 2026-09-24 | NIFTY | 15:00 @ 23,140f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.8σ | ✗ push nahi · put 23,100 +6.2L · aaj ka max nahi | ✓ fut OI flat −99 lots | CHOP | +18 | ? |
| 2026-09-25 | NIFTY | 09:50 @ 23,088f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY armed 23,077s | ✗ −1σ | ✗ push nahi · call 23,050 +8.6L · aaj ka max nahi | ✓ fut OI flat −194 lots | MIXED | +54 | +46 |
| 2026-09-25 | NIFTY | 10:20 @ 23,148f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.4σ | ✗ push 10:17 +221 jawab nahi · pehle koi toot nahi · put 23,100 +9.9L · aaj ka max nahi | ✓ fut OI fresh ulta +406 lots | MIXED | +21 | +31 |
| 2026-09-28 | NIFTY | 09:45 @ 22,900f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY armed 22,897s | ✗ −1.3σ | ✗ push 09:35 −578 toot −12.1L · call 22,850 +21.0L · kharidar | ✓ fut OI cover −919 lots | MIXED | −1 | −22 |
| 2026-09-28 | NIFTY | 10:00 @ 22,910f | BOTTOM | 2 / 3 | 0 | ✗ zone BUY nahi | ✗ −0.9σ | ✓ push 09:35 toot −12.1L → 10:00 −168 jawab nahi | ✓ fut OI cover −947 lots | MIXED | −21 | −31 |
| 2026-09-28 | NIFTY | 10:20 @ 22,875f | BOTTOM | 0 / 3 | 0 | ✗ zone BUY nahi | ✗ −1.4σ | ✗ push 10:15 −251 jawab nahi · pehle koi toot nahi · call 22,850 +17.1L · aaj ka max nahi | ✗ fut OI fresh +241 lots | MIXED | −6 | −9 |
| 2026-09-28 | NIFTY | 10:45 @ 22,862f | BOTTOM | 1 / 4 | 0 | ✗ zone BUY nahi | ✗ −1.4σ | ✗ push nahi · call 22,800 +8.0L · aaj ka max nahi | ✓ fut OI cover −909 lots | TREND ▼ | +2 | −5 |
| 2026-09-28 | NIFTY | 11:05 @ 22,870f | BOTTOM | 1 / 4 | 0 | ✗ zone BUY nahi | ✗ −1.1σ | ✗ push 11:00 −252 jawab nahi · pehle koi toot nahi · call 22,800 +2.8L | ✓ fut OI cover −736 lots | TREND ▼ | −16 | +11 |
| 2026-09-28 | NIFTY | 11:25 @ 22,865f | BOTTOM | 1 / 4 | 0 | ✗ zone BUY nahi | ✗ −1.1σ | ✗ push nahi · call 22,800 +6.1L · aaj ka max nahi | ✓ fut OI cover −270 lots | TREND ▼ | +11 | −3 |
| 2026-09-28 | NIFTY | 11:35 @ 22,891f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.5σ | ✗ push 11:26 +236 jawab nahi · pehle koi toot nahi · put 22,850 +9.4L · aaj ka max nahi | ✓ fut OI flat −26 lots | TREND ▼ | +3 | +5 |
| 2026-09-28 | NIFTY | 11:45 @ 22,900f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.3σ | ✗ push nahi · put 22,850 +8.2L · aaj ka max nahi | ✓ fut OI cover −244 lots | TREND ▼ | +12 | +3 |
| 2026-09-28 | NIFTY | 11:50 @ 22,900f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.3σ | ✗ push nahi · put 22,850 +6.8L · aaj ka max nahi | ✓ fut OI cover −288 lots | TREND ▼ | +2 | −9 |
| 2026-09-28 | NIFTY | 12:00 @ 22,852f | BOTTOM | 1 / 4 | 0 | ✗ zone BUY nahi | ✗ −1.3σ | ✗ push 11:56 −211 jawab nahi · pehle koi toot nahi · call 22,800 +6.1L · aaj ka max nahi | ✓ fut OI cover −1,956 lots | TREND ▼ | +9 | +13 |
| 2026-09-28 | NIFTY | 13:10 @ 22,860f | BOTTOM | 0 / 4 | 0 | ✗ zone BUY nahi | ✗ −1σ | ✗ push 13:08 −195 toot −9.6L · call 22,800 +9.0L · aaj ka max nahi | ✗ fut OI fresh +635 lots | TREND ▼ | +27 | +17 |
| 2026-09-28 | NIFTY | 13:15 @ 22,868f | BOTTOM | 2 / 4 | 0 | ✗ zone BUY nahi | ✗ −0.9σ | ✓ push 13:08 toot −9.6L → 13:12 −216 deewar tiki +10.1L | ✓ fut OI fresh ulta +394 lots | TREND ▼ | +1 | +6 |
| 2026-09-28 | NIFTY | 13:30 @ 22,900f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.1σ | ✗ push nahi · put 22,850 +9.3L · aaj ka max nahi | ✓ fut OI flat +50 lots | TREND ▼ | −5 | +0 |
| 2026-09-28 | NIFTY | 13:45 @ 22,891f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.3σ | ✗ push nahi · put 22,850 +2.6L | ✓ fut OI flat −68 lots | TREND ▼ | +5 | +39 |
| 2026-09-28 | NIFTY | 14:20 @ 22,816f | BOTTOM | 3 / 4 | 0 | ✓ zone BUY armed 22,820s | ✗ −1.9σ | ✓ call writers 22,800 +31.8L · aaj ka max | ✓ fut OI cover −231 lots | TREND ▼ | −31 | +3 |
| 2026-09-29 | NIFTY | 14:20 @ 22,695f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.6σ | ✗ push 14:19 +171 jawab nahi · pehle koi toot nahi · put 22,700 +9.0L · aaj ka max nahi | ✓ fut OI cover −468 lots | MIXED | −20 | −24 |
| 2026-09-29 | NIFTY | 15:20 @ 22,705f | TOP | 2 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.8σ | ✓ push 15:08 toot −39.8L → 15:16 +632 jawab nahi | ✓ fut OI cover −1,631 lots | CHOP | ? | ? |
| 2026-09-30 | NIFTY | 10:00 @ 22,866f | TOP | 2 / 3 | 0 | ✓ zone SELL armed 22,865s | ✓ +2.6σ | ✗ push nahi · put 22,750 +5.8L · aaj ka max nahi | ✗ fut OI fresh +952 lots | PIN | −26 | +21 |
| 2026-09-30 | NIFTY | 15:25 @ 22,690f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY trigger 22,715s | ✗ −1.7σ | ✗ push 15:22 −213 jawab nahi · pehle koi toot nahi · call 22,600 −6.0L | ✓ fut OI fresh ulta +935 lots | CHOP | ? | ? |
| 2026-10-01 | NIFTY | 09:35 @ 22,675f | TOP | 1 / 3 | 1 | ✓ zone SELL armed | ? σ | ✗ push 09:30 +206 jawab nahi · pehle koi toot nahi · put 22,600 +1.3L | ✗ fut OI fresh +444 lots | MIXED | +23 | −21 |
| 2026-10-01 | NIFTY | 10:05 @ 22,700f | TOP | 2 / 3 | 0 | ✓ zone SELL armed 22,686s | ✓ +2.9σ | ✗ push 10:01 +198 jawab nahi · pehle koi toot nahi · put 22,600 +13.3L · kharidar | ✗ fut OI fresh +322 lots | MIXED | +24 | +4 |
| 2026-10-01 | NIFTY | 13:45 @ 22,370f | BOTTOM | 0 / 3 | 0 | ✗ zone BUY nahi | ✗ −1.5σ | ✗ push 13:41 −253 toot −3.6L · call 22,250 +2.8L | ✗ fut OI fresh +3,338 lots | CHOP | −61 | −10 |
| 2026-10-01 | NIFTY | 14:40 @ 22,490f | TOP | 0 / 3 | 0 | ✗ zone SELL nahi | ✗ +0σ | ✗ push 14:34 +502 jawab nahi · pehle koi toot nahi · put 22,400 +6.3L · aaj ka max nahi | ✗ fut OI fresh +2,687 lots | CHOP | −44 | −88 |
| 2026-10-01 | NIFTY | 14:55 @ 22,500f | TOP | 0 / 3 | 0 | ✗ zone SELL nahi | ✗ +0σ | ✗ push 14:54 +215 jawab nahi · pehle koi toot nahi · put 22,400 +10.7L · aaj ka max nahi | ✗ fut OI fresh +1,187 lots | CHOP | −45 | −24 |
| 2026-10-06 | NIFTY | 10:05 @ 22,760f | TOP | 2 / 3 | 0 | ✓ zone SELL trigger 22,730s | ✗ +1.8σ | ✗ push 09:55 +339 jawab nahi · pehle koi toot nahi · put 22,700 +1.1L | ✓ fut OI flat −217 lots | MIXED | −25 | −44 |
| 2026-10-06 | NIFTY | 11:50 @ 22,785f | TOP | 1 / 4 | 0 | ✗ zone SELL nahi | ✗ +1.6σ | ✗ push 11:45 +398 toot −12.5L · put 22,700 +29.0L · aaj ka max nahi | ✓ fut OI flat −215 lots | TREND ▲ | +3 | −12 |
| 2026-10-06 | NIFTY | 14:15 @ 22,815f | TOP | 1 / 4 | 0 | ✗ zone SELL nahi | ✗ +1.3σ | ✗ push nahi · put 22,750 +14.2L · aaj ka max nahi | ✓ fut OI fresh ulta +436 lots | TREND ▲ | +19 | +4 |
| 2026-10-07 | NIFTY | 10:30 @ 22,750f | TOP | 2 / 3 | 2 | ✓ zone SELL armed 22,730s | ✓ +2.9σ | ? push ? · put likhai ? | ? fut OI | CHOP | ? | ? |
| 2026-10-07 | NIFTY | 12:05 @ 22,775f | TOP | 2 / 3 | 2 | ✓ zone SELL armed 22,767s | ✓ +2.3σ | ? push ? · put likhai ? | ? fut OI | CHOP | ? | ? |
| 2026-10-07 | NIFTY | 13:10 @ 22,610f | BOTTOM | 2 / 3 | 2 | ✓ zone BUY armed 22,607s | ✓ −2σ | ? push 13:07 −334 toot −9.5L · call likhai ? | ? fut OI | CHOP | +18 | +24 |
| 2026-10-08 | NIFTY | 09:45 @ 22,500f | BOTTOM | 2 / 3 | 1 | ✓ zone BUY armed 22,503s | ? σ | ✗ push 09:43 −209 toot −3.8L · call 22,450 +11.5L · kharidar | ✓ fut OI flat −12 lots | MIXED | +14 | −5 |
| 2026-10-08 | NIFTY | 13:05 @ 22,320f | BOTTOM | 1 / 4 | 1 | ✗ zone BUY nahi | ? σ | ✗ push nahi · call 22,250 +1.5L | ✓ fut OI flat −89 lots | TREND ▼ | −19 | +0 |
| 2026-10-08 | NIFTY | 14:25 @ 22,280f | BOTTOM | 0 / 4 | 1 | ✗ zone BUY nahi | ? σ | ✗ push 14:21 −215 jawab nahi · pehle koi toot nahi · call 22,200 +6.0L · aaj ka max nahi | ✗ fut OI fresh +888 lots | TREND ▼ | +16 | −12 |
| 2026-10-09 | NIFTY | 09:30 @ 22,440f | TOP | 1 / 3 | 3 | ✓ zone SELL armed 22,454s | ? σ | ? push ? · put likhai ? | ? fut OI | MIXED | ? | ? |
| 2026-10-09 | NIFTY | 11:45 @ 22,545f | BOTTOM | 1 / 3 | 0 | ✗ zone BUY nahi | ✗ +0.6σ | ✗ push nahi · call 22,450 +2.2L | ✓ fut OI cover −576 lots | MIXED | −21 | −19 |
| 2026-10-09 | NIFTY | 13:00 @ 22,590f | TOP | 1 / 4 | 0 | ✗ zone SELL nahi | ✗ +1.2σ | ✗ push nahi · put 22,500 +14.4L · aaj ka max nahi | ✓ fut OI cover −359 lots | TREND ▲ | −12 | −19 |
| 2026-10-09 | NIFTY | 13:50 @ 22,620f | TOP | 2 / 4 | 0 | ✗ zone SELL nahi | ✗ +1.6σ | ✓ put writers 22,550 +9.1L · aaj ka max | ✓ fut OI flat −105 lots | TREND ▲ | ? | ? |
| 2026-10-12 | NIFTY | 11:20 @ 22,415f | BOTTOM | 1 / 4 | 2 | ✓ zone BUY match | ✗ −1.8σ | ? push ? · call likhai ? | ? fut OI | TREND ▼ | ? | ? |
| 2026-10-12 | NIFTY | 13:10 @ 22,485f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ −0.1σ | ✗ push 13:09 +194 jawab nahi · pehle koi toot nahi · put 22,400 −1.7L | ✓ fut OI flat −166 lots | TREND ▼ | −6 | +4 |
| 2026-10-16 | NIFTY | 10:20 @ 23,140f | TOP | 1 / 3 | 2 | ✓ zone SELL armed 23,158s | ✗ +1.6σ | ? push ? · put likhai ? | ? fut OI | MIXED | ? | ? |
| 2026-10-19 | NIFTY | 09:30 @ 22,995f | BOTTOM | 2 / 3 | 2 | ✓ zone BUY match | ? σ | ? push ? · call 23,000 +40.3L · kharidar | ✓ fut OI flat −201 lots | MIXED | +33 | −30 |
| 2026-10-19 | NIFTY | 11:40 @ 23,000f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY armed 22,975s | ✗ −1.6σ | ✓ call writers 23,000 +81.6L · aaj ka max | ✗ fut OI fresh +366 lots | CHOP | −23 | −58 |
| 2026-10-19 | NIFTY | 12:20 @ 22,935f | BOTTOM | 2 / 3 | 0 | ✓ zone BUY armed 22,937s | ✗ −1.9σ | ✗ push nahi · call 22,950 +47.4L · kharidar | ✓ fut OI flat +24 lots | CHOP | +14 | −9 |
| 2026-10-21 | NIFTY | 13:50 @ 22,695f | BOTTOM | 2 / 4 | 0 | ✓ zone BUY armed | ✗ −1.8σ | ✗ push 13:47 −290 jawab nahi · pehle koi toot nahi · call 22,650 +1.8L | ✓ fut OI flat −67 lots | TREND ▼ | −1 | −21 |
| 2026-10-22 | NIFTY | 10:40 @ 22,785f | TOP | 1 / 3 | 0 | ✓ zone SELL trigger 22,735s | ✗ +1.9σ | ✗ push 10:37 +428 jawab nahi · pehle koi toot nahi · put 22,750 +4.0L · aaj ka max nahi | ✗ fut OI fresh +337 lots | CHOP | −21 | −65 |
| 2026-10-22 | NIFTY | 11:15 @ 22,810f | TOP | 2 / 3 | 0 | ✓ zone SELL armed 22,809s | ✗ +1.9σ | ✗ push nahi · put 22,800 +6.7L · kharidar | ✓ fut OI flat +37 lots | CHOP | +52 | +157 |
| 2026-10-22 | NIFTY | 12:55 @ 22,770f | TOP | 2 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.3σ | ✓ put writers 22,750 +5.9L · aaj ka max | ✓ fut OI flat −64 lots | CHOP | +39 | +78 |
| 2026-10-22 | NIFTY | 14:45 @ 22,750f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.1σ | ✗ push 14:44 +205 jawab nahi · pehle koi toot nahi · put 22,700 +3.2L | ✓ fut OI cover −1,689 lots | CHOP | +19 | +0 |
| 2026-10-23 | NIFTY | 13:20 @ 22,455f | BOTTOM | 1 / 4 | 0 | ✗ zone BUY nahi | ✗ −1.1σ | ✗ push 13:11 −267 jawab nahi · pehle koi toot nahi · call 22,400 +3.3L · aaj ka max nahi | ✓ fut OI cover −1,007 lots | TREND ▼ | +114 | +97 |
| 2026-10-23 | NIFTY | 13:45 @ 22,660f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +0.6σ | ✓ put writers 22,600 +13.5L · aaj ka max | ✗ fut OI fresh +2,550 lots | TREND ▼ | −5 | −3 |
| 2026-10-27 | NIFTY | 10:25 @ 22,695f | BOTTOM | 1 / 3 | 0 | ✗ zone BUY nahi | ✗ −1.5σ | ✗ push 10:20 −221 toot −15.3L · call 22,700 +22.4L · aaj ka max nahi | ✓ fut OI cover −130 lots | MIXED | +29 | +44 |
| 2026-10-27 | NIFTY | 15:00 @ 22,800f | TOP | 1 / 3 | 0 | ✗ zone SELL nahi | ✗ +1.4σ | ✗ push 14:59 +241 toot −13.8L · put 22,750 +43.1L · kharidar | ✓ fut OI cover −111 lots | CHOP | −11 | ? |

## ALERT 1 · every ZONE SETUP line, with its day type

| day | line (as Telegram gets it) | +15 | +30 |
|---|---|---|---|
| 2026-10-01 | `09:30  BANKNIFTY  ZONE BUY · 3/4 · ✓ d2 54,722s|55,011f chhua 09:24 · ? thakan/roka — chart marks nahi · ✓ PE likh rahe · lead +37.7 09:25 · ✓ Δ −35 → +106 · E 54,846s|55,135f · stop 54,702s|54,991f · din MIXED: saaf nahi` | +46 | +94 |
| 2026-10-01 | `09:30  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,516s|22,619f chhua 09:24 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −31.9 · ✓ Δ −357 → +187 · E 22,541s|22,644f · stop 22,496s|22,599f · din MIXED: saaf nahi` | +19 | +32 |
| 2026-10-01 | `09:35  SENSEX  ZONE BUY · 3/4 · ✓ d2 72,251s|72,818f chhua 09:24 · ? thakan/roka — chart marks nahi (NIFTY) · ✓ PE likh rahe · lead +15.5 09:25 · ✓ Δ −357 → +187 (NIFTY) · E 72,402s|72,968f · stop 72,231s|72,798f · din MIXED: saaf nahi` | +56 | +194 |
| 2026-10-01 | `09:40  BANKNIFTY  ZONE SELL · 2/4 · ✓ u2 54,812s|55,111f chhua 09:27 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −31.2 · ✓ Δ +106 → −54 · E 54,822s|55,121f · stop 54,920s|55,219f · din MIXED: saaf nahi` | −21 | −63 |
| 2026-10-01 | `09:40  SENSEX  ZONE SELL · 2/4 · ✓ u2 72,421s|72,974f chhua 09:30 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ CE likh rahe · lead −6.6 · ✓ Δ +187 → −89 (NIFTY) · E 72,304s|72,857f · stop 72,441s|72,994f · din MIXED: saaf nahi` | +37 | −110 |
| 2026-10-01 | `10:00  BANKNIFTY  ZONE SELL · 1/4 · ✓ u2 54,940s|55,220f chhua 09:51 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −30.8 · ? Δ — flow 09:40 se · E 54,890s|55,170f · stop 54,960s|55,240f · din MIXED: saaf nahi` | +55 | −32 |
| 2026-10-01 | `10:00  SENSEX  ZONE SELL · 2/4 · ✓ u2 72,421s|72,973f chhua 09:39 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ CE likh rahe · lead −7.0 · ✓ Δ +187 → −25 → +14 → −66 (NIFTY) · E 72,338s|72,889f · stop 72,448s|73,000f · din MIXED: saaf nahi` | −12 | +28 |
| 2026-10-01 | `10:10  BANKNIFTY  ZONE SELL · 2/4 · ✓ u2 54,966s|55,246f chhua 10:00 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −30.7 · ✓ Δ +253 → −21 · E 54,900s|55,180f · stop 54,986s|55,266f · din MIXED: saaf nahi` | −30 | −127 |
| 2026-10-01 | `10:15  NIFTY  ZONE SELL · 3/4 · ✓ u2 22,579s|22,670f chhua 09:30 · ? thakan/roka — chart marks nahi · ✓ CE likh rahe · lead +31.9 09:30 · ✓ Δ +187 → −89 · E 22,565s|22,657f · stop 22,608s|22,699f · din MIXED: saaf nahi` | +15 | +8 |
| 2026-10-01 | `10:15  SENSEX  ZONE SELL · 2/4 · ✓ u2 72,474s|73,015f chhua 10:00 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ CE likh rahe · lead −32.5 · ✓ Δ +291 → +47 → −297 (NIFTY) · E 72,492s|73,033f · stop 72,519s|73,060f · din MIXED: saaf nahi` | +39 | −18 |
| 2026-10-01 | `10:45  BANKNIFTY  ZONE SELL · 2/4 · ✓ u2 55,018s|55,300f chhua 10:30 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −48.4 · ✓ Δ +370 → +135 → −63 · E 55,018s|55,300f · stop 55,069s|55,351f · din MIXED: saaf nahi` | +61 | +141 |
| 2026-10-01 | `10:45  NIFTY  ZONE SELL · 3/4 · ✓ u2 22,589s|22,686f chhua 10:30 · ? thakan/roka — chart marks nahi · ✓ CE likh rahe · lead +15.7 10:35 · ✓ Δ +200 → +9 → −39 · E 22,573s|22,669f · stop 22,612s|22,708f · din PIN: palat ki ummeed` | +2 | +19 |
| 2026-10-01 | `10:45  SENSEX  ZONE SELL · 2/4 · ✓ u2 72,488s|73,067f chhua 10:33 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ CE likh rahe · lead −4.5 · ✓ Δ +200 → +9 → −39 (NIFTY) · E 72,441s|73,020f · stop 72,510s|73,089f · din MIXED: saaf nahi` | +38 | +103 |
| 2026-10-01 | `11:40  SENSEX  ZONE BUY · 3/4 · ✓ d2 72,309s|72,846f chhua 11:24 · ? thakan/roka — chart marks nahi (NIFTY) · ✓ PE likh rahe · lead +17.4 11:25 · ✓ Δ −163 → −8 → −36 → +22 (NIFTY) · E 72,406s|72,943f · stop 72,289s|72,826f · din MIXED: saaf nahi` | −60 | −116 |
| 2026-10-01 | `12:15  SENSEX  ZONE BUY · 1/4 · ✓ d2 72,296s|72,843f chhua 12:06 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ PE likh rahe · lead +0.5 · ? Δ — flow 11:55 se (NIFTY) · E 72,274s|72,821f · stop 72,264s|72,812f · din CHOP: palat ki ummeed` | −159 | −251 |
| 2026-10-01 | `12:40  BANKNIFTY  ZONE BUY · 3/4 · ✓ d2 54,724s|54,988f chhua 12:21 · ? thakan/roka — chart marks nahi · ✓ PE likh rahe · lead +34.7 12:25 · ✓ Δ −249 → −32 → −2 → +77 · E 54,765s|55,029f · stop 54,668s|54,933f · din CHOP: palat ki ummeed` | −353 | −265 |
| 2026-10-01 | `13:05  BANKNIFTY  ZONE BUY · 3/4 · ✓ d2 54,677s|54,931f chhua 12:42 · ? thakan/roka — chart marks nahi · ✓ PE likh rahe · lead +13.4 12:55 · ✓ Δ −299 → −210 → −179 → +483 · E 54,408s|54,662f · stop 54,399s|54,652f · din CHOP: palat ki ummeed` | −72 | +5 |
| 2026-10-01 | `13:05  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,539s|22,621f chhua 12:06 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −75.0 · ✓ Δ −383 → −348 → −181 → +162 · E 22,373s|22,455f · stop 22,305s|22,386f · din CHOP: palat ki ummeed` | −37 | −25 |
| 2026-10-01 | `13:05  SENSEX  ZONE BUY · 3/4 · ✓ d2 72,327s|72,828f chhua 12:15 · ? thakan/roka — chart marks nahi (NIFTY) · ✓ PE likh rahe · lead +15.4 12:55 · ✓ Δ −383 → −348 → −181 → +162 (NIFTY) · E 71,696s|72,198f · stop 71,506s|72,007f · din CHOP: palat ki ummeed` | −116 | −52 |
| 2026-10-01 | `14:10  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 54,244s|54,525f chhua 13:42 · ? thakan/roka — chart marks nahi · ✓ PE likh rahe · lead +29.7 14:00 · ? Δ — flow 13:30 se · E 54,219s|54,500f · stop 54,055s|54,336f · din CHOP: palat ki ummeed` | −2 | +136 |
| 2026-10-19 | `09:30  SENSEX  ZONE SELL · 3/4 · ✓ u2 74,612s|74,646f chhua 09:24 · ? thakan/roka — chart marks nahi (NIFTY) · ✓ CE likh rahe · lead +31.7 09:25 · ✓ Δ +91 → −203 → −1,860 (NIFTY) · E 74,219s|74,254f · stop 74,632s|74,666f · din MIXED: saaf nahi` | −539 | −217 |
| 2026-10-19 | `09:35  NIFTY  ZONE BUY · 2/4 · ✓ d2 23,052s|23,051f chhua 09:24 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −51.5 · ✓ Δ −1,860 → +219 · E 23,063s|23,061f · stop 22,955s|22,954f · din MIXED: saaf nahi` | +33 | −30 |
| 2026-10-19 | `09:35  SENSEX  ZONE BUY · 2/4 · ✓ d2 74,356s|74,402f chhua 09:24 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ PE likh rahe · lead −80.5 · ✓ Δ −1,860 → +219 (NIFTY) · E 74,452s|74,498f · stop 74,187s|74,233f · din MIXED: saaf nahi` | +120 | −113 |
| 2026-10-19 | `09:40  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 55,553s|55,749f chhua 09:24 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −55.8 · ✓ Δ −569 → +119 · E 55,552s|55,747f · stop 55,347s|55,542f · din MIXED: saaf nahi` | −67 | −128 |
| 2026-10-19 | `09:55  SENSEX  ZONE SELL · 2/4 · ✓ u2 74,742s|74,771f chhua 09:36 · ? thakan/roka — chart marks nahi (NIFTY) · ✓ CE likh rahe · lead +54.6 09:40 · ? Δ — flow 09:25 se (NIFTY) · E 74,634s|74,663f · stop 74,762s|74,791f · din MIXED: saaf nahi` | +147 | +104 |
| 2026-10-19 | `10:25  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 55,428s|55,576f chhua 09:57 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −47.7 · ✓ Δ −152 → +24 · E 55,563s|55,712f · stop 55,408s|55,556f · din MIXED: saaf nahi` | −76 | +26 |
| 2026-10-19 | `11:50  SENSEX  ZONE BUY · 2/4 · ✓ d2 74,228s|74,284f chhua 11:36 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ PE likh rahe · lead −34.7 · ✓ Δ −502 → −263 → +16 (NIFTY) · E 74,229s|74,285f · stop 74,201s|74,257f · din CHOP: palat ki ummeed` | −172 | −228 |
| 2026-10-19 | `12:30  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,979s|22,988f chhua 11:39 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −34.2 · ✓ Δ −502 → −263 → +16 · E 22,951s|22,960f · stop 22,917s|22,926f · din CHOP: palat ki ummeed` | −16 | −25 |
| 2026-10-19 | `12:40  SENSEX  ZONE BUY · 2/4 · ✓ d2 74,168s|74,265f chhua 11:51 · ? thakan/roka — chart marks nahi (NIFTY) · ✗ PE likh rahe · lead −45.4 · ✓ Δ −479 → −455 → −184 → +91 (NIFTY) · E 74,053s|74,150f · stop 73,920s|74,017f · din CHOP: palat ki ummeed` | −85 | −74 |
| 2026-10-19 | `13:40  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 55,426s|55,555f chhua 13:24 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −81.5 · ✓ Δ −196 → −76 → −43 → +57 · E 55,461s|55,590f · stop 55,393s|55,523f · din CHOP: palat ki ummeed` | +10 | +17 |
| 2026-10-19 | `13:40  SENSEX  ZONE BUY · 2/4 · ✓ d2 73,808s|73,956f chhua 13:21 · ? thakan/roka — chart marks nahi (NIFTY) · ? PE likh rahe — could not check -- spot 73,837 is at the chain window's edge (ATM ±0 only) · ✓ Δ −931 → −79 → +113 (NIFTY) · E 73,812s|73,960f · stop 73,761s|73,910f · din CHOP: palat ki ummeed` | −21 | −13 |
| 2026-10-19 | `13:45  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,876s|22,897f chhua 13:21 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −24.9 · ✓ Δ −931 → −79 → +113 · E 22,894s|22,915f · stop 22,850s|22,871f · din CHOP: palat ki ummeed` | +10 | +10 |
| 2026-10-19 | `14:00  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 55,395s|55,529f chhua 13:45 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −83.2 · ✓ Δ −266 → +51 · E 55,474s|55,608f · stop 55,372s|55,505f · din CHOP: palat ki ummeed` | +8 | −8 |
| 2026-10-21 | `09:45  BANKNIFTY  ZONE SELL · 2/4 · ✓ u2 55,705s|55,801f chhua 09:24 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −100.0 · ✓ Δ +222 → −147 · E 55,779s|55,875f · stop 55,876s|55,971f · din MIXED: saaf nahi` | +230 | +404 |
| 2026-10-21 | `09:45  SENSEX  ZONE SELL · 2/4 · ✓ u2 74,649s|74,708f chhua 09:33 · ✓ THAKAN kharidar 23,092f 09:20 (NIFTY) · ✗ CE likh rahe · lead −25.8 · ? Δ — flow 09:20 se (NIFTY) · E 74,612s|74,672f · stop 74,722s|74,781f · din MIXED: saaf nahi` | +222 | +451 |
| 2026-10-21 | `09:50  NIFTY  ZONE SELL · 3/4 · ✓ u2 23,078s|23,090f chhua 09:24 · ✓ THAKAN kharidar 23,092f 09:20 · ✗ CE likh rahe · lead −36.1 · ✓ Δ +2,139 → +52 → +98 → −122 · E 23,076s|23,088f · stop 23,124s|23,136f · din MIXED: saaf nahi` | +70 | +124 |
| 2026-10-21 | `10:30  BANKNIFTY  ZONE BUY · 3/4 · ✓ d2 55,569s|55,656f chhua 10:00 · ? thakan/roka — chart marks nahi · ✓ PE likh rahe · lead +11.7 10:00 · ✓ Δ −710 → +62 · E 55,452s|55,539f · stop 55,264s|55,352f · din MIXED: saaf nahi` | +51 | +6 |
| 2026-10-21 | `10:30  NIFTY  ZONE BUY · 4/4 · ✓ d2 23,012s|23,033f chhua 09:54 · ✓ THAKAN bechne wale 23,030f 09:55 · ✓ PE likh rahe · lead +26.2 09:55 · ✓ Δ −405 → −318 → −211 → +151 · E 22,955s|22,976f · stop 22,937s|22,958f · din MIXED: saaf nahi` | +12 | +4 |
| 2026-10-21 | `10:30  SENSEX  ZONE BUY · 4/4 · ✓ d2 74,254s|74,346f chhua 10:03 · ✓ THAKAN bechne wale 23,030f 09:55 (NIFTY) · ✓ PE likh rahe · lead +33.6 10:05 · ✓ Δ −405 → −318 → −211 → +151 (NIFTY) · E 74,195s|74,286f · stop 74,040s|74,132f · din MIXED: saaf nahi` | +51 | +20 |
| 2026-10-21 | `12:10  SENSEX  ZONE BUY · 4/4 · ✓ d2 74,007s|74,111f chhua 11:18 · ✓ KHAREEDAR NE ROKA 22,965f 11:10, KHAREEDAR NE ROKA 22,905f 11:25 (NIFTY) · ✓ PE likh rahe · lead +35.7 11:20 · ✓ Δ −804 → +19 (NIFTY) · E 73,708s|73,812f · stop 73,654s|73,757f · din MIXED: saaf nahi` | −239 | −149 |
| 2026-10-21 | `12:30  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 55,232s|55,314f chhua 11:18 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −93.8 · ✓ Δ −300 → −84 → −109 → +69 · E 54,808s|54,891f · stop 54,674s|54,756f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −11 | +108 |
| 2026-10-21 | `12:30  SENSEX  ZONE BUY · 2/4 · ✓ d2 73,669s|73,760f chhua 12:09 · ✗ thakan/roka nahi (NIFTY) · ✓ PE likh rahe · lead +20.8 12:10 · ? Δ — flow 11:55 se (NIFTY) · E 73,470s|73,561f · stop 73,397s|73,489f · din MIXED: saaf nahi` | +26 | +133 |
| 2026-10-21 | `12:35  NIFTY  ZONE BUY · 4/4 · ✓ d2 22,918s|22,935f chhua 11:18 · ✓ KHAREEDAR NE ROKA 22,965f 11:10, KHAREEDAR NE ROKA 22,905f 11:25 · ✓ PE likh rahe · lead +21.4 11:20 · ✓ Δ −804 → +19 · E 22,757s|22,774f · stop 22,739s|22,757f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −18 | −30 |
| 2026-10-21 | `13:00  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,737s|22,753f chhua 12:36 · ✗ thakan/roka nahi · ✗ PE likh rahe · lead −18.3 · ✓ Δ −270 → −78 → +35 · E 22,779s|22,795f · stop 22,717s|22,733f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −65 | −41 |
| 2026-10-21 | `13:20  NIFTY  ZONE BUY · 1/4 · ✓ d2 22,711s|22,729f chhua 13:12 · ✗ thakan/roka nahi · ✗ PE likh rahe · lead −21.8 · ? Δ — flow 13:00 se · E 22,732s|22,750f · stop 22,691s|22,709f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −13 | −49 |
| 2026-10-21 | `14:05  NIFTY  ZONE BUY · 3/4 · ✓ d2 22,668s|22,693f chhua 13:45 · ✓ KHAREEDAR NE ROKA 22,695f 13:45 · ✗ PE likh rahe · lead −21.1 · ✓ Δ −320 → −64 → +112 · E 22,717s|22,743f · stop 22,642s|22,667f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −34 | −21 |
| 2026-10-22 | `09:30  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,572s|22,583f chhua 09:24 · ✗ thakan/roka nahi · ✗ PE likh rahe · lead −17.5 · ✓ Δ −491 → +334 · E 22,598s|22,608f · stop 22,552s|22,563f · din MIXED: saaf nahi` | +59 | +46 |
| 2026-10-22 | `09:40  BANKNIFTY  ZONE SELL · 3/4 · ✓ u2 54,729s|54,906f chhua 09:30 · ? thakan/roka — chart marks nahi · ✓ CE likh rahe · lead +43.1 09:40 · ✓ Δ +282 → −2 · E 54,524s|54,701f · stop 54,749s|54,926f · din MIXED: saaf nahi` | −85 | −54 |
| 2026-10-22 | `09:40  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,572s|22,582f chhua 09:33 · ✗ thakan/roka nahi · ✗ PE likh rahe · lead −14.2 · ✓ Δ −491 → +334 → +13 → +385 · E 22,593s|22,604f · stop 22,552s|22,562f · din PIN: palat ki ummeed` | +28 | −3 |
| 2026-10-22 | `09:40  SENSEX  ZONE SELL · 2/4 · ✓ u2 73,178s|73,273f chhua 09:30 · ✓ BECHNE WALE NE ROKA 22,630f 09:30, THAKAN kharidar 22,645f 09:30 (NIFTY) · ✗ CE likh rahe · lead −0.6 · ✗ Δ + → − nahi · abhi +385 (NIFTY) · E 73,033s|73,128f · stop 73,198s|73,293f · din PIN: palat ki ummeed` | −84 | +75 |
| 2026-10-22 | `09:45  BANKNIFTY  ZONE BUY · 1/4 · ✓ d2 54,559s|54,725f chhua 09:33 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −42.9 · ? Δ — flow 09:20 se · E 54,614s|54,780f · stop 54,539s|54,705f · din MIXED: saaf nahi` | +39 | +158 |
| 2026-10-22 | `09:45  SENSEX  ZONE BUY · 3/4 · ✓ d2 73,109s|73,195f chhua 09:24 · ✗ thakan/roka nahi (NIFTY) · ✓ PE likh rahe · lead +16.7 09:25 · ✓ Δ −491 → +334 (NIFTY) · E 73,204s|73,290f · stop 73,066s|73,151f · din PIN: palat ki ummeed` | −15 | +42 |
| 2026-10-22 | `09:55  SENSEX  ZONE SELL · 3/4 · ✓ u2 73,197s|73,285f chhua 09:39 · ✓ BECHNE WALE NE ROKA 22,630f 09:30, THAKAN kharidar 22,645f 09:30 (NIFTY) · ✗ CE likh rahe · lead −15.7 · ✓ Δ +385 → +319 → +350 → −74 (NIFTY) · E 73,312s|73,400f · stop 73,363s|73,450f · din CHOP: palat ki ummeed` | +159 | −187 |
| 2026-10-22 | `10:05  NIFTY  ZONE SELL · 4/4 · ✓ u2 22,615s|22,627f chhua 09:39 · ✓ BECHNE WALE NE ROKA 22,630f 09:30, THAKAN kharidar 22,645f 09:30 · ✓ CE likh rahe · lead +14.2 09:40 · ✓ Δ +385 → +319 → +350 → −74 · E 22,605s|22,617f · stop 22,675s|22,687f · din CHOP: palat ki ummeed` | −65 | −166 |
| 2026-10-22 | `10:45  BANKNIFTY  ZONE SELL · 3/4 · ✓ u2 54,789s|54,922f chhua 10:12 · ? thakan/roka — chart marks nahi · ✓ CE likh rahe · lead +36.0 10:15 · ✓ Δ +240 → +91 → −16 · E 54,983s|55,116f · stop 55,126s|55,259f · din CHOP: palat ki ummeed` | +29 | +13 |
| 2026-10-22 | `10:45  NIFTY  ZONE SELL · 3/4 · ✓ u2 22,655s|22,677f chhua 10:12 · ✓ BECHNE WALE NE ROKA 22,690f 10:15, THAKAN kharidar 22,709f 10:15 · ✗ CE likh rahe · lead −18.3 · ✓ Δ +2,477 → −4 · E 22,713s|22,735f · stop 22,773s|22,795f · din CHOP: palat ki ummeed` | −21 | −65 |
| 2026-10-22 | `10:45  SENSEX  ZONE SELL · 4/4 · ✓ u2 73,357s|73,472f chhua 10:15 · ✓ BECHNE WALE NE ROKA 22,690f 10:15, THAKAN kharidar 22,709f 10:15 (NIFTY) · ✓ CE likh rahe · lead +12.3 10:25 · ✓ Δ +2,477 → −4 (NIFTY) · E 73,515s|73,630f · stop 73,601s|73,715f · din CHOP: palat ki ummeed` | −56 | −206 |
| 2026-10-22 | `11:25  NIFTY  ZONE SELL · 2/4 · ✓ u2 22,785s|22,808f chhua 11:12 · ✓ THAKAN kharidar 22,813f 11:15 · ✗ CE likh rahe · lead −27.3 · ? Δ — flow 11:00 se · E 22,744s|22,767f · stop 22,805s|22,828f · din CHOP: palat ki ummeed` | +22 | +125 |
| 2026-10-23 | `09:45  SENSEX  ZONE BUY · 4/4 · ✓ d2 73,573s|73,782f chhua 09:24 · ✓ THAKAN bechne wale 22,738f 09:30 (NIFTY) · ✓ PE likh rahe · lead +37.0 09:25 · ✓ Δ −258 → +541 (NIFTY) · E 73,479s|73,688f · stop 73,464s|73,673f · din MIXED: saaf nahi` | −267 | −601 |
| 2026-10-23 | `10:25  SENSEX  ZONE BUY · 4/4 · ✓ d2 73,456s|73,659f chhua 09:42 · ✓ THAKAN bechne wale 22,738f 09:30 (NIFTY) · ✓ PE likh rahe · lead +23.4 09:45 · ✓ Δ −602 → −51 → +355 (NIFTY) · E 72,892s|73,095f · stop 72,821s|73,023f · din MIXED: saaf nahi` | −128 | −149 |
| 2026-10-26 | `09:30  NIFTY  ZONE BUY · 3/4 · ✓ d2 22,445f chhua 09:24 · ✓ KHAREEDAR NE ROKA 22,500f 09:15, THAKAN bechne wale 22,454f 09:20 · ✗ PE likh rahe · lead −20.5 · ✓ Δ −1,007 → −286 → +33 · E 22,534f · stop 22,425f · din MIXED: saaf nahi` | ? | ? |
| 2026-10-26 | `09:30  SENSEX  ZONE BUY · 3/4 · ✓ d2 72,738f chhua 09:24 · ✓ KHAREEDAR NE ROKA 22,500f 09:15, THAKAN bechne wale 22,454f 09:20 (NIFTY) · ✗ PE likh rahe · lead −9.1 · ✓ Δ −1,007 → −286 → +33 (NIFTY) · E 72,948f · stop 72,718f · din: padh nahi sake` | ? | ? |
| 2026-10-26 | `09:40  SENSEX  ZONE SELL · 2/4 · ✓ u2 72,678s|72,893f chhua 09:27 · ✗ thakan/roka nahi (NIFTY) · ✗ CE likh rahe · lead −26.8 · ✓ Δ +372 → −880 (NIFTY) · E 72,636s|72,851f · stop 72,736s|72,951f · din: padh nahi sake` | −356 | −813 |
| 2026-10-26 | `10:30  BANKNIFTY  ZONE SELL · 3/4 · ✓ u2 54,147s|54,272f chhua 09:51 · ? thakan/roka — chart marks nahi · ✓ CE likh rahe · lead +12.7 10:00 · ✓ Δ +86 → −12 → +52 → −88 · E 54,199s|54,323f · stop 54,395s|54,519f · din: padh nahi sake` | +108 | +102 |
| 2026-10-26 | `10:40  NIFTY  ZONE SELL · 3/4 · ✓ u2 22,479s|22,553f chhua 09:45 · ✓ THAKAN kharidar 22,556f 09:45, THAKAN kharidar 22,790f 10:05 · ✗ CE likh rahe · lead −53.6 · ✓ Δ +372 → −880 → −26 → −467 · E 22,601s|22,675f · stop 22,727s|22,801f · din MIXED: saaf nahi` | −33 | −14 |
| 2026-10-26 | `10:40  SENSEX  ZONE SELL · 3/4 · ✓ u2 72,678s|72,936f chhua 09:42 · ✓ THAKAN kharidar 22,556f 09:45, THAKAN kharidar 22,790f 10:05 (NIFTY) · ✗ CE likh rahe · lead −38.3 · ✓ Δ +372 → −880 → −26 → −467 (NIFTY) · E 73,121s|73,378f · stop 73,559s|73,816f · din: padh nahi sake` | −114 | −74 |
| 2026-10-26 | `14:20  BANKNIFTY  ZONE SELL · 1/4 · ✓ u2 54,328s|54,455f chhua 14:12 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −18.5 · ? Δ — flow 14:00 se · E 54,265s|54,392f · stop 54,348s|54,475f · din: padh nahi sake` | −54 | −84 |
| 2026-10-27 | `09:30  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,676s|22,682f chhua 09:24 · ✗ thakan/roka nahi · ✗ PE likh rahe · lead −25.5 · ✓ Δ −327 → +60 → +422 · E 22,746s|22,752f · stop 22,656s|22,662f · din MIXED: saaf nahi` | +14 | +1 |
| 2026-10-27 | `09:35  SENSEX  ZONE SELL · 3/4 · ✓ u2 73,522s|73,625f chhua 09:27 · ✓ THAKAN kharidar 22,760f 09:30 (NIFTY) · ✓ CE likh rahe · lead +78.2 09:30 · ✗ Δ + → − nahi · abhi +83 (NIFTY) · E 73,397s|73,500f · stop 73,542s|73,645f · din MIXED: saaf nahi` | −90 | −221 |
| 2026-10-27 | `10:00  BANKNIFTY  ZONE SELL · 2/4 · ✓ u2 54,392s|54,405f chhua 09:24 · ? thakan/roka — chart marks nahi · ✗ CE likh rahe · lead −4.2 · ✓ Δ +78 → −90 · E 54,537s|54,550f · stop 54,683s|54,695f · din MIXED: saaf nahi` | −26 | +82 |
| 2026-10-27 | `10:00  NIFTY  ZONE SELL · 3/4 · ✓ u2 22,704s|22,711f chhua 09:24 · ✓ THAKAN kharidar 22,760f 09:30 · ✓ CE likh rahe · lead +13.4 09:25 · ✗ Δ + → − nahi · abhi +94 · E 22,724s|22,731f · stop 22,774s|22,781f · din MIXED: saaf nahi` | −29 | +19 |
| 2026-10-27 | `10:00  SENSEX  ZONE SELL · 2/4 · ✓ u2 73,577s|73,659f chhua 09:51 · ✗ thakan/roka nahi (NIFTY) · ✓ CE likh rahe · lead +44.4 09:55 · ? Δ — flow 09:40 se (NIFTY) · E 73,463s|73,545f · stop 73,597s|73,679f · din MIXED: saaf nahi` | −109 | +42 |
| 2026-10-27 | `10:10  NIFTY  ZONE SELL · 1/4 · ✓ u2 22,774s|22,784f chhua 10:00 · ✗ thakan/roka nahi · ✗ CE likh rahe · lead −10.6 · ✗ Δ + → − nahi · abhi +149 · E 22,766s|22,776f · stop 22,808s|22,818f · din MIXED: saaf nahi` | +75 | +13 |
| 2026-10-27 | `10:10  SENSEX  ZONE SELL · 2/4 · ✓ u2 73,618s|73,689f chhua 10:00 · ✗ thakan/roka nahi (NIFTY) · ✓ CE likh rahe · lead +43.2 10:00 · ✗ Δ + → − nahi · abhi +149 (NIFTY) · E 73,549s|73,620f · stop 73,656s|73,727f · din MIXED: saaf nahi` | +218 | +17 |
| 2026-10-27 | `12:30  BANKNIFTY  ZONE BUY · 1/4 · ✓ d2 54,278s|54,288f chhua 12:15 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −9.3 · ✗ Δ − → + nahi · abhi −5 · E 54,287s|54,298f · stop 54,253s|54,264f · din MIXED: saaf nahi` | +123 | +52 |
| 2026-10-27 | `12:50  SENSEX  ZONE SELL · 2/4 · ✓ u2 73,711s|73,764f chhua 12:42 · ✓ BECHNE WALE NE ROKA 22,840f 12:40 (NIFTY) · ✗ CE likh rahe · lead +7.5 · ? Δ — flow 12:30 se (NIFTY) · E 73,664s|73,717f · stop 73,731s|73,784f · din CHOP: palat ki ummeed` | +151 | +303 |
| 2026-10-27 | `12:55  NIFTY  ZONE SELL · 2/4 · ✓ u2 22,807s|22,815f chhua 12:42 · ✓ BECHNE WALE NE ROKA 22,840f 12:40 · ✗ CE likh rahe · lead −13.5 · ? Δ — flow 12:30 se · E 22,778s|22,785f · stop 22,827s|22,835f · din CHOP: palat ki ummeed` | +45 | +71 |
| 2026-10-27 | `13:40  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 54,250s|54,257f chhua 13:03 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −32.3 · ✓ Δ −61 → −41 → −51 → +92 · E 54,113s|54,120f · stop 54,106s|54,114f · din TREND ▼: price discovery ho sakti hai · fade khatra` | +30 | −35 |
| 2026-10-27 | `13:40  NIFTY  ZONE BUY · 3/4 · ✓ d2 22,684s|22,678f chhua 13:30 · ✓ KHAREEDAR NE ROKA 22,696f 13:15, THAKAN bechne wale 22,685f 13:20 · ✗ PE likh rahe · lead −14.0 · ✓ Δ −426 → +143 → −36 → +110 · E 22,727s|22,721f · stop 22,664s|22,658f · din CHOP: palat ki ummeed` | +8 | −31 |
| 2026-10-27 | `13:40  SENSEX  ZONE BUY · 3/4 · ✓ d2 73,324s|73,342f chhua 13:21 · ✓ KHAREEDAR NE ROKA 22,696f 13:15, THAKAN bechne wale 22,685f 13:20 (NIFTY) · ✗ PE likh rahe · lead −38.1 · ✓ Δ −426 → +143 → −36 → +110 (NIFTY) · E 73,432s|73,450f · stop 73,297s|73,315f · din CHOP: palat ki ummeed` | +29 | −80 |
| 2026-10-27 | `13:55  BANKNIFTY  ZONE BUY · 1/4 · ✓ d2 54,097s|54,100f chhua 13:36 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −31.1 · ? Δ — flow 13:25 se · E 54,100s|54,103f · stop 54,060s|54,063f · din TREND ▼: price discovery ho sakti hai · fade khatra` | −65 | −125 |
| 2026-10-27 | `14:25  NIFTY  ZONE BUY · 2/4 · ✓ d2 22,665s|22,671f chhua 14:03 · ✓ KHAREEDAR NE ROKA 22,665f 14:00, KHAREEDAR NE ROKA 22,655f 14:05 · ✗ PE likh rahe · lead −17.8 · ? Δ — flow 13:50 se · E 22,667s|22,673f · stop 22,631s|22,637f · din CHOP: palat ki ummeed` | +83 | +105 |
| 2026-10-27 | `14:25  SENSEX  ZONE BUY · 2/4 · ✓ d2 73,278s|73,326f chhua 14:03 · ✓ KHAREEDAR NE ROKA 22,665f 14:00, KHAREEDAR NE ROKA 22,655f 14:05 (NIFTY) · ✗ PE likh rahe · lead −33.3 · ? Δ — flow 13:50 se (NIFTY) · E 73,265s|73,312f · stop 73,212s|73,259f · din CHOP: palat ki ummeed` | +228 | +336 |
| 2026-10-27 | `14:40  BANKNIFTY  ZONE BUY · 2/4 · ✓ d2 54,056s|54,068f chhua 13:57 · ? thakan/roka — chart marks nahi · ✗ PE likh rahe · lead −42.4 · ✓ Δ −91 → −14 → −76 → +32 · E 54,083s|54,095f · stop 53,958s|53,970f · din TREND ▼: price discovery ho sakti hai · fade khatra` | +11 | −20 |
| 2026-10-27 | `15:25  NIFTY  ZONE SELL · 2/4 · ✓ u2 22,800s|22,824f chhua 15:18 · ✓ BECHNE WALE NE ROKA 22,797f 15:10, BECHNE WALE NE ROKA 22,815f 15:20 · ✗ CE likh rahe · lead −25.9 · ? Δ — flow 15:05 se · E 22,754s|22,778f · stop 22,820s|22,844f · din CHOP: palat ki ummeed` | ? | ? |
