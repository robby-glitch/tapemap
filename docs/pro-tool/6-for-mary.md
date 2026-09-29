# For Mary: what the tool will do, in one page

**Your question: does a trader who made a trade fold on one thing?** No. He asks three things, at different places, and knows in advance what would change his mind:
1. **Is the trade wrong?** Price was *accepted* past my give-up level: real business traded there, for a normal stretch, and it didn't come back. Then I'm out. No waiting for OI, and no candles.
2. **Are my defenders gone?** Once my give-up has trailed past my entry, I give the trade rope. I fold when the flow is accepted past the give-up **and** the writers behind me have really left, or when that acceptance holds two more buckets. I never let a winner go back through my entry.
3. **Is it done?** The tool never tells you to bank. It shows the wall ahead in numbers, your peak and what you've given back. You bank.

**And the line your rule needs:** "not behind me" comes in two kinds. **Quiet** means nobody is pushing: you hold and know your out. **Against** means someone turned on you at your level: that is the fold. At 14:12 today nothing was against you. VPIN was with you, and the other three were only quiet. The put went from 164.8 to 210.6 by 14:20. That is one trade, not proof.

## Your day on the new screen

| when | what you see |
|---|---|
| **09:00–09:15** | Contract and flags (expiry, roll). Yesterday's high/low/close for this contract. The biggest walls each side. Which feeds are alive. |
| **The open** | Who the gap trapped, and the first fight. Every read from its first minute. It never says "blind", only what it can and can't check yet. |
| **Flat** | NEXT FIGHT above and below, and what would confirm each. |
| **Before you enter** | IF YOU WERE IN: what the screen would say, your give-up and the premium there, the wall ahead and the premium there. Buy or sell, with its two numbers. No GO or NO. |
| **In the trade** | **HOLD**, then what is behind you and what is against you. Line 2 says exactly what takes you out, before it happens. Four rows: zone, flow, OI, VPIN. |
| **Expiry afternoon** | Your give-up follows your best price. The premium is split into in-the-money and time, so you can see a 0DTE option bleeding. |
| **If the tool goes blind** | **CAN'T CHECK since 11:42, and why.** Never a HOLD it can't see. |
| **The exit** | **FOLD**, with its reason and time, one sound, once. It stays until you press I'M OUT. |
| **After the close** | Your trade's word history, counts and never rates. Your trigger_log is untouched. |

Your give-up only ever tightens. Selling is read by the same engine, turned round, in a seller's own words.

## Removed

- The 3-minute close line, the trend vote, the 15-minute quiet clock, and **the latch that froze a wrong FOLD all day today**.
- GO / WAIT / NO, and the Room ratio.
- Spot as "ATM". Every strike is judged on the options' own forward. Spot was 24–46 points off today.
- "Expiry day" and "expiry eve" as buy/sell votes. They would have told you to sell on your +97 % put and on the +264 % expiry put.
- Nine tabs you don't use. What is left: DESK, WAR, RECORD, your Trade tab and the chart panel.

**Kept by your order:** the Dhan fallback, the tape pieces, the Trade tab's chart, PaperDesk's routes, the 09:25 zone anchor, §1d and trigger_log.

## What you sign, and when

- **One signature**, for rev 6.
- **First you commit the amendment file** (`6-amendment.md`). That fixes its text.
- **Then the gates run on every recorded day, including tomorrow and Wednesday**, which no design has seen. That is Wednesday after the close at the earliest.
- **You sign only if the gates pass.** The signature goes into research-findings §1i. The signed files are never edited.
- **Rev 6 takes force the first session its screen is live**, not the night you sign.

## What goes live first

1. **Tonight, your hands only:**
   - copy trigger_log somewhere safe;
   - commit its untracking, then tonight's bug fixes and the extension work.

   Until you do, a careless git command by any agent could overwrite 2,005 rows with an old copy of 402.
2. **Plumbing, after the close (no rule changes):**
   - tests can never write into your data;
   - the dead-contract OI goes blind in expiry week;
   - Wednesday's roll: the Trade tab stops drawing September's levels on the October chart. **Please restart after Tuesday's close**;
   - every recorded row says which contract it is;
   - the chart panel checks the contract against Upstox and stops drawing Friday's marks on Monday;
   - the panel goes LIGHT and stops snapping shut.
3. **This week:** the new engine runs **silently alongside**. Its words appear in RECORD after 15:30, never during the session unless you ask.
4. **After you sign:** the new screen.

**Tomorrow (expiry) and Wednesday (the roll), honestly:** the old window is still the one running. Its FOLD can stick all day, as it did today, and nothing can change it without your signature. On expiry day the September future's flow carries roll trades too.

**What this can't promise:**
- Eight trades on five days show the shape, not the odds. Your next 30 sessions decide.
- A quick stop-out on a busy open that comes straight back (the whipsaw) has no fix yet. Everything tried tonight made it worse.
