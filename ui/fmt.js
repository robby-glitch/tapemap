"use strict";
/* Shared formatters for ui/console.html -- plain script, no modules, loaded
   via <script src="fmt.js"> before the page's own inline script. Only what
   console.html calls is kept: n() and esc(). console.html defines its own
   num() display wrapper around n().

   An absent value is a STATED absence, never a zero -- n() returns null so
   callers can say so. */
function n(v, d){ return (v===null||v===undefined||!isFinite(v)) ? null
                        : Number(v).toLocaleString("en-IN",
                            {minimumFractionDigits:d===undefined?0:d,
                             maximumFractionDigits:d===undefined?0:d}); }
function esc(s){ return String(s===null||s===undefined?"":s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
