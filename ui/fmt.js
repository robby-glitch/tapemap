"use strict";
/* Shared formatters for ui/desk.html and ui/console.html -- plain script,
   no modules, loaded via <script src="fmt.js"> before each page's own
   inline script. Lifted verbatim from desk.html (the more-developed of the
   two divergent copies) so this extraction is behaviour-preserving.

   THE ONE CHOSEN CONVENTION: negative rupees put the minus sign BEFORE the
   currency symbol -- "-₹10.0k", never "₹-10.0k". This was already desk.html's
   convention (see the comment this replaces); console.html renders no rupee
   figures today, so nothing there changes, but any future rupee readout on
   either screen now has exactly one way to sign a loss. */

/* An absent value is a STATED absence, never a zero -- n() returns null so
   callers can say so; num() is the display wrapper with a fallback dash. */
function n(v, d){ return (v===null||v===undefined||!isFinite(v)) ? null
                        : Number(v).toLocaleString("en-IN",
                            {minimumFractionDigits:d===undefined?0:d,
                             maximumFractionDigits:d===undefined?0:d}); }
function num(v, d, dash){ var s = n(v,d); return s===null ? (dash===undefined?"—":dash) : s; }
function rs(v, d){
  if(v===null||v===undefined||!isFinite(v)) return "—";
  return (v<0?"-₹":"₹") + n(Math.abs(v), d===undefined?2:d);
}
function pct(v, d){ return (v===null||v===undefined||!isFinite(v)) ? "—"
                          : (v*100).toFixed(d===undefined?2:d)+"%"; }
function esc(s){ return String(s===null||s===undefined?"":s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function shortRs(v){
  if(v===null||v===undefined||!isFinite(v)) return "—";
  var a = Math.abs(v), s = v<0?"-₹":"₹";
  if(a>=1e7) return s+(a/1e7).toFixed(2)+"cr";
  if(a>=1e5) return s+(a/1e5).toFixed(2)+"L";
  if(a>=1e3) return s+(a/1e3).toFixed(1)+"k";
  return s+a.toFixed(0);
}
