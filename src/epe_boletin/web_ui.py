"""Local, framework-free presentation assets, also included in portable builds."""

CSS = """
.email-notice{display:grid;gap:var(--s2)}.email-notice p{margin:0}.email-file{display:flex;align-items:center;flex-wrap:wrap;gap:var(--s3)}.email-file a{overflow-wrap:anywhere}.email-file form{margin:0}
:root{
 --paper:oklch(.985 .003 250);--surface:oklch(1 0 0);--surface-sunk:oklch(.965 .006 250);
 --ink:oklch(.26 .020 250);--ink-2:oklch(.47 .018 250);--ink-3:oklch(.53 .015 250);
 --line:oklch(.915 .006 250);--line-strong:oklch(.64 .010 250);
 --accent:oklch(.50 .15 255);--accent-ink:oklch(.40 .14 255);--accent-soft:oklch(.955 .030 255);--gold:var(--accent);
 --slate:oklch(.28 .030 255);--on-slate:oklch(.97 .006 250);
 --sig-alta:oklch(.48 .13 25);--sig-media:oklch(.48 .10 75);--sig-ok:oklch(.48 .11 150);--sig-info:oklch(.48 .11 240);
 --sig-soft-a:oklch(.95 .03 25);--sig-soft-m:oklch(.95 .03 75);--sig-soft-ok:oklch(.95 .03 150);--sig-soft-i:oklch(.95 .03 240);
 --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:64px;--page-gutter:clamp(16px,2vw,40px);--topbar-height:76px;
 --r-sm:3px;--r-md:6px;--r-lg:10px;--shadow-1:0 1px 2px oklch(.26 .020 250 / .06);--shadow-2:0 6px 20px oklch(.26 .020 250 / .10);
 --ui:"Archivo","Segoe UI",system-ui,sans-serif;--mono:"Space Mono",Consolas,"Courier New",monospace;
 --fs-display:1.3125rem;--fs-h2:.9375rem;--fs-metric:1.5rem;--fs-title:1.0625rem;--fs-body:.875rem;--fs-small:.8125rem;--fs-code:.75rem;--fs-eyebrow:.75rem;
 font-family:var(--ui);font-size:16px;color:var(--ink);background:var(--paper);scrollbar-color:var(--accent) var(--paper)
}
*{box-sizing:border-box}body{margin:0;font-size:var(--fs-body);line-height:1.55}::selection{background:var(--accent-soft);color:var(--ink)}
.shell{width:100%;min-width:0;padding:0 var(--page-gutter) var(--s5)}a{color:var(--accent);text-decoration:underline;text-underline-offset:2px;text-decoration-thickness:1px}a:hover{color:var(--accent-ink);text-decoration-thickness:2px}
button,input,select{font:inherit;min-width:0;max-width:100%;height:40px;padding:0 var(--s3);border:1px solid var(--line-strong);border-radius:var(--r-md);background:var(--surface);color:var(--ink);caret-color:var(--accent)}
input::placeholder{color:var(--ink-3);opacity:1}
button{cursor:pointer;font-weight:600;white-space:nowrap}button:hover{border-color:var(--accent);color:var(--accent-ink)}button:disabled{cursor:not-allowed;color:var(--ink-3)}
button.primary{background:var(--accent);border-color:var(--accent);color:var(--surface)}button.primary:hover{background:var(--accent-ink)}button.primary:disabled{background:var(--surface-sunk);border-color:var(--line-strong);color:var(--ink-3)}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,.row:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.topbar{position:sticky;top:0;z-index:5;background:var(--slate);color:var(--on-slate);min-height:76px;display:flex;align-items:center;gap:var(--s5);margin-inline:calc(0px - var(--page-gutter));padding-inline:var(--page-gutter)}.scrolled .topbar{box-shadow:var(--shadow-1)}
h1{font:700 var(--fs-display)/1.2 var(--ui);letter-spacing:-.01em;margin:0;white-space:nowrap}h2{font:600 var(--fs-h2)/1.2 var(--ui);margin:0}p{margin:0}
.run-pill{margin-left:auto;display:flex;align-items:center;gap:var(--s2);font-size:var(--fs-small);text-decoration:none;color:var(--on-slate);border:1px solid oklch(.60 .030 255);border-radius:99px;padding:var(--s1) var(--s3);white-space:nowrap}.run-pill:hover{color:var(--on-slate);text-decoration:underline}
.dot{width:8px;height:8px;border-radius:50%;background:oklch(.72 .13 150);flex:none}.run-pill.error .dot{background:oklch(.72 .15 20)}.run-pill.neutral .dot{background:var(--on-slate)}
.view-nav{display:flex;gap:var(--s4);align-items:stretch;align-self:stretch}.view-nav a{display:flex;align-items:center;padding-inline:var(--s2);color:var(--on-slate);text-decoration:none}.view-nav a:hover{background:oklch(.35 .030 255);color:var(--on-slate)}.view-nav a[aria-current=page]{box-shadow:inset 0 -2px 0 currentColor;font-weight:600}.help{height:44px;width:44px;display:grid;place-items:center;border:1px solid oklch(.60 .030 255);border-radius:var(--r-sm);font-family:var(--mono);text-decoration:none;color:var(--on-slate)}.help:hover{color:var(--on-slate)}
.context,.foot{font-size:var(--fs-small);color:var(--ink-3)}
.metrics{display:flex;align-items:stretch;background:var(--surface-sunk);max-height:64px;overflow:hidden;transition:max-height 160ms ease-out;margin-inline:calc(0px - var(--page-gutter));padding-inline:var(--page-gutter)}.scrolled .metrics{max-height:0}.metric{padding:0 var(--s5);border-right:1px solid var(--line);display:flex;align-items:center;text-decoration:none;color:var(--ink);gap:var(--s3);height:64px}.metric:first-child{padding-left:0}.metric:last-child{border:0}.metric b{font:700 var(--fs-metric)/1 var(--ui);font-variant-numeric:tabular-nums}.metric span{font-size:var(--fs-small);color:var(--ink-3);white-space:nowrap}.metric[aria-current=true]{background:var(--accent-soft);box-shadow:inset 0 -2px 0 var(--accent)}.metric[aria-disabled=true]{color:var(--ink-3)}
.filters{position:sticky;top:var(--topbar-height);z-index:4;background:var(--paper);border-bottom:1px solid var(--line);padding:var(--s3) 0}.filters fieldset{margin:0;padding:0;border:0;display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(190px,.65fr) minmax(190px,.65fr) minmax(250px,1fr) auto;gap:var(--s3);align-items:end}
.scrolled .filters{padding-top:var(--s2);padding-bottom:var(--s2)}.scrolled .filter-state{display:none}
.field{min-width:0;display:grid;gap:var(--s1)}.field>label,.field-label{font-size:var(--fs-eyebrow);font-weight:600;color:var(--ink-3)}.eyebrow{font-size:var(--fs-eyebrow);font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3)}input,select{width:100%}.date-control{display:flex;gap:var(--s2);align-items:center}.period-control{display:flex;align-items:center;min-width:0;flex:1;height:40px;padding-inline:var(--s2);background:var(--surface);border:1px solid var(--line-strong);border-radius:var(--r-md)}.period-date{display:flex;align-items:center;gap:var(--s1);min-width:0;flex:1}.period-date+ .period-date{border-left:1px solid var(--line);padding-left:var(--s2)}.period-date label{font-size:var(--fs-code);color:var(--ink-3);flex:none}.period-date input{border:0;height:36px;padding:0;min-width:0;font-size:var(--fs-small)}.icon-button{width:40px;padding:0;display:grid;place-items:center;flex:none;text-decoration:none;height:40px;border:1px solid var(--line-strong);border-radius:var(--r-md);color:var(--ink);background:var(--surface)}.icon-button[aria-disabled=true]{color:var(--ink-3);background:var(--paper)}
.period-field{position:relative}.range-picker{min-width:0;flex:1}.range-trigger{display:none;width:100%;height:40px;padding:2px var(--s2);align-items:center;text-align:left;gap:var(--s2);font-weight:400}.range-picker.enhanced .range-trigger{display:flex}.range-picker.enhanced .range-native{display:none}.range-segment{display:grid;min-width:0;flex:1;line-height:1.25}.range-segment+ .range-segment{border-left:1px solid var(--line);padding-left:var(--s2)}.range-segment small{font-size:var(--fs-code);color:var(--ink-3)}.range-segment span{font-size:var(--fs-small);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.range-trigger>.icon{margin-left:auto;color:var(--ink-2)}
.range-panel{position:absolute;top:calc(100% + var(--s2));left:0;z-index:2;width:min(680px,calc(100vw - var(--page-gutter) - var(--page-gutter)));max-height:calc(100dvh - 200px);overflow-y:auto;display:grid;gap:var(--s3);padding:var(--s4);background:var(--surface);border:1px solid var(--line-strong);border-radius:var(--r-lg);box-shadow:var(--shadow-2)}.range-panel[hidden],.range-backdrop[hidden]{display:none}.filters.range-active{z-index:8}.range-panel-header{display:grid;grid-template-columns:36px 1fr 36px;align-items:center;gap:var(--s2);text-align:center}.range-panel-header strong{font-size:var(--fs-body);font-weight:600}.range-month-nav{width:36px;height:36px;padding:0;display:grid;place-items:center;border-color:var(--line)}.range-months{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--s5)}.range-month{min-width:0}.range-month h3{margin:0 0 var(--s2);text-align:center;font-size:var(--fs-body);font-weight:600}.range-weekdays,.range-days{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));text-align:center}.range-weekdays span{font-size:var(--fs-code);font-weight:600;color:var(--ink-3)}.range-days{margin-top:var(--s1);grid-auto-rows:36px}.range-day{width:100%;height:36px;padding:0;border:0;border-radius:0;font-size:var(--fs-small);font-variant-numeric:tabular-nums}.range-day:hover:not(:disabled){background:var(--accent-soft);color:var(--accent-ink)}.range-day:disabled{background:transparent;color:var(--ink-3)}.range-day.is-between,.range-day.is-preview-edge{background:var(--accent-soft);color:var(--accent-ink)}.range-day.is-preview-edge{box-shadow:inset 0 0 0 1px var(--accent);border-radius:var(--r-md)}.range-day.is-edge,.range-day.is-edge:hover{background:var(--accent);color:var(--surface);border-radius:var(--r-md)}.range-day.is-today:not(.is-edge){text-decoration:underline;text-underline-offset:4px}.range-message{min-height:20px;font-size:var(--fs-small);color:var(--ink-2)}.range-footer{display:flex;justify-content:flex-end;align-items:center;gap:var(--s3);padding-top:var(--s3);border-top:1px solid var(--line)}.range-clear{border:0;color:var(--ink-2)}.range-backdrop{display:none}
.icon{width:14px;height:14px;stroke:currentColor;stroke-width:1.7;fill:none;vertical-align:-2px;flex:none}.search-wrap{position:relative;display:flex;align-items:center}.search-wrap>.icon{position:absolute;left:var(--s3)}.search-wrap input{padding-left:var(--s6);padding-right:var(--s6)}.clear-search{position:absolute;right:var(--s1);height:28px;width:28px;border:0;padding:0;background:transparent;display:grid;place-items:center}
.presets,.filter-state,.chips,.actions,.list-tools{display:flex;flex-wrap:wrap;align-items:center;gap:var(--s2)}.filter-state{flex-wrap:nowrap;min-height:40px;padding-top:var(--s2)}.presets{flex-wrap:nowrap;flex:none}.filter-chips{flex:1;flex-wrap:nowrap;min-width:0;overflow:auto;scrollbar-width:thin}.chip{display:inline-flex;align-items:center;gap:var(--s1);flex:none;font-size:var(--fs-code);padding:var(--s1) var(--s2);background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);text-decoration:none;color:var(--ink-2);white-space:nowrap;max-width:100%}.chip[aria-current=true],.chip.active{background:var(--accent-soft);color:var(--accent-ink);border-color:var(--accent)}.counter{font-size:var(--fs-small);font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap}.preset-menu{display:none;position:relative}.preset-menu>summary{min-height:36px;padding-inline:var(--s2);border:1px solid var(--line-strong);border-radius:var(--r-sm)}.preset-menu .presets{position:absolute;top:40px;left:0;z-index:7;flex-direction:column;align-items:stretch;padding:var(--s2);background:var(--surface);box-shadow:var(--shadow-2)}
.result-head{display:flex;justify-content:space-between;gap:var(--s4);align-items:center;padding:var(--s5) 0 var(--s3)}.actions{gap:var(--s3);font-size:var(--fs-small)}.list-tools{justify-content:space-between;padding:var(--s2) 0 var(--s3)}.list-tools button{height:36px;font-size:var(--fs-small)}.results-toolbar{display:flex;justify-content:space-between;align-items:center;gap:var(--s4);padding:var(--s5) 0 var(--s3)}.results-actions{display:flex;align-items:center;gap:var(--s3)}.density{display:flex;gap:0}.density button{height:36px;font-size:var(--fs-small)}.density button[aria-pressed=true]{color:var(--accent-ink);background:var(--accent-soft);border-color:var(--accent)}.export-view{display:inline-flex;align-items:center;gap:var(--s2);height:36px;padding:0 var(--s3);border:1px solid var(--line-strong);border-radius:var(--r-md);text-decoration:none;font-size:var(--fs-small);font-weight:600;white-space:nowrap}.export-view:hover{border-color:var(--accent);text-decoration:underline}
.column-head,.row{display:grid;grid-template-columns:28px clamp(94px,8vw,132px) minmax(0,1.25fr) minmax(0,1.75fr) clamp(158px,13vw,220px);gap:var(--s3) var(--s5);align-items:start;padding:var(--s3) var(--s4)}.column-head{position:sticky;top:var(--columns-top,172px);z-index:3;min-height:40px;background:var(--surface-sunk);border-bottom:1px solid var(--line);padding-block:var(--s2);align-items:center;color:var(--ink-3)}.column-label{font:var(--fs-code)/1.4 var(--mono)}.column-cell{min-width:0;display:flex;align-items:center;justify-content:space-between;gap:var(--s2)}.density button:first-child{border-radius:var(--r-sm) 0 0 var(--r-sm)}.density button:last-child{border-radius:0 var(--r-sm) var(--r-sm) 0}.row{background:var(--surface)}
.publication-list{list-style:none;margin:0;padding:0}.row{border-bottom:1px solid var(--line);transition:background 160ms ease-out;scroll-margin-top:var(--columns-top,252px);overflow-wrap:anywhere}.row>*{min-width:0}.row:hover{background:var(--surface)}.row:focus-within{outline:2px solid var(--accent);outline-offset:-2px}.row[data-unread]{box-shadow:inset 3px 0 0 var(--sig-info)}.row[data-selected]{background:var(--accent-soft);box-shadow:inset 3px 0 0 var(--accent)}
.pick{padding-top:var(--s1)}.pick input{height:18px;width:18px;margin:0;accent-color:var(--accent)}.date,.code{font-family:var(--mono);font-variant-numeric:tabular-nums}.date{font-size:var(--fs-small)}.code{font-size:var(--fs-code);color:var(--ink-3);overflow-wrap:anywhere}.type{margin-top:var(--s2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.title{font:600 var(--fs-title)/1.35 var(--ui);margin:var(--s1) 0}.title a{color:var(--ink);text-decoration:none}.title a:hover{color:var(--accent);text-decoration:underline}
.analysis{display:grid;align-content:start;gap:var(--s2)}.badge{justify-self:start;font-size:var(--fs-code);font-weight:600;text-transform:uppercase;letter-spacing:.06em;padding:3px var(--s2);border-radius:var(--r-sm);color:var(--ink-3);background:var(--surface-sunk)}.badge.direct_epesf{color:var(--sig-alta);background:var(--sig-soft-a)}.badge.potential_sector_impact{color:var(--sig-media);background:var(--sig-soft-m)}.badge.not_relevant{color:var(--sig-info);background:var(--sig-soft-i)}
.signal{font-size:var(--fs-code);color:var(--ink-2);background:var(--surface-sunk);border-radius:var(--r-sm);padding:2px var(--s2)}mark{background:var(--sig-soft-m);color:var(--ink)}.preview{color:var(--ink-2);font-size:var(--fs-body);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.links{display:grid;gap:var(--s1);font-size:var(--fs-small)}.links a{display:flex;gap:var(--s1);align-items:baseline}.pages{font:var(--fs-code) var(--mono)}.error-text{color:var(--sig-alta);font-size:var(--fs-small)}
details{margin:0}summary{cursor:pointer;font-size:var(--fs-small);font-weight:600;list-style:none;display:flex;align-items:center;gap:var(--s1);color:var(--accent)}summary::-webkit-details-marker{display:none}summary .icon{transition:transform 160ms ease-out}details[open]>summary .icon{transform:rotate(90deg)}
.detail-body{margin-top:var(--s3);border-left:3px solid var(--accent);padding:var(--s4);background:var(--surface);display:grid;gap:var(--s3);max-width:68ch;color:var(--ink-2)}.summary{display:grid;gap:var(--s2)}.attribution{font-size:var(--fs-code);color:var(--ink-3)}.detail-body p{white-space:pre-line}.summary-action{justify-self:start;font-size:var(--fs-small)}
.empty{display:grid;justify-items:center;gap:var(--s3);padding:var(--s7) var(--s4);text-align:center;border-bottom:1px solid var(--line)}.empty h3{font:600 var(--fs-title)/1.35 var(--ui);margin:0}.empty p{max-width:52ch;color:var(--ink-2)}.empty a{display:inline-block}.notice{margin-top:var(--s4);padding:var(--s3) var(--s4);background:var(--sig-soft-ok);color:var(--sig-ok);border-radius:var(--r-md)}.notice.error{background:var(--sig-soft-a);color:var(--sig-alta)}
.selection-form{margin:0}.selection-bar{position:fixed;z-index:6;bottom:var(--s4);left:50%;width:min(1272px,calc(100% - 48px));padding:var(--s3) var(--s4);background:var(--ink);color:var(--paper);display:flex;align-items:center;gap:var(--s4);border-radius:var(--r-md);box-shadow:var(--shadow-2);transform:translate(-50%,0);animation:selection-enter 160ms ease-out}.selection-bar[hidden]{display:none}.selection-bar strong{margin-right:auto;font-variant-numeric:tabular-nums}.selection-bar button{border-color:var(--paper);background:transparent;color:var(--paper)}.selection-bar .primary{background:var(--accent);border-color:var(--accent);color:var(--paper)}.selection-bar button:hover{background:var(--ink-2);color:var(--paper)}body:has(.selection-bar:not([hidden])){padding-bottom:96px}
.agency{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.code{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.publication-type{display:block;margin-top:var(--s1);color:var(--ink-3);font-size:var(--fs-code)}.title{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.analysis>.badge{text-transform:none;letter-spacing:0}.badge.not_relevant{color:var(--ink-3);background:var(--surface-sunk)}.analysis>details>summary{font-size:var(--fs-code);min-height:28px}.summary-action{height:32px;font-size:var(--fs-code)}.analysis>.context{font-size:var(--fs-code)}.row .preview{line-height:1.5;max-width:78ch}
.row{padding-block:var(--s4)}.row .preview{-webkit-line-clamp:3}.row .links{gap:var(--s2)}.badge{line-height:1.35}.compact{--fs-title:1rem}.compact .row{padding-block:var(--s2)}.compact .preview{-webkit-line-clamp:2}.compact .title{-webkit-line-clamp:1}.compact .analysis{gap:var(--s1)}.compact .links{gap:var(--s1)}
.column-head .pick{padding-top:0;display:flex;align-items:center}
.full-reference .code{white-space:normal;overflow-wrap:anywhere;overflow:visible}
.selection-bar{bottom:0;background:var(--slate);color:var(--on-slate);border-radius:var(--r-md) var(--r-md) 0 0}.selection-bar button{color:var(--on-slate);border-color:var(--on-slate)}.selection-bar button:hover{background:var(--accent-ink)}
.calendar-heading{display:grid;justify-items:center;gap:var(--s2);min-width:0}.month-picker{display:flex;gap:var(--s2);margin:0;max-width:100%}.month-picker select{width:200px}.calendar-nav{display:flex;flex-wrap:wrap;gap:var(--s3);align-items:center;justify-content:space-between;padding:var(--s5) 0 var(--s4)}.calendar-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:var(--s2)}.weekday{font-size:var(--fs-code);color:var(--ink-3);text-align:center}.calendar-day{min-height:96px;display:flex;flex-direction:column;gap:var(--s1);padding:var(--s3);border:1px solid var(--line);border-radius:var(--r-sm);text-decoration:none;color:var(--ink);background:var(--surface)}.calendar-day strong{font:var(--fs-small) var(--mono)}.calendar-day span{font-size:var(--fs-code)}.calendar-day.volume-1{background:var(--accent-soft)}.calendar-day.volume-2{background:oklch(.91 .045 255)}.calendar-day.volume-3{background:oklch(.86 .055 255)}.calendar-day.failed{border:2px solid var(--sig-alta)}.calendar-day.today strong{text-decoration:underline;text-underline-offset:4px}.calendar-day.unprocessed{background:var(--paper);color:var(--ink-3)}.calendar-legend{display:flex;flex-wrap:wrap;gap:var(--s4);padding-top:var(--s4);color:var(--ink-2);font-size:var(--fs-small)}
.issue-list{list-style:none;margin:0;padding:0}.issue{padding:var(--s4) 0;border-bottom:1px solid var(--line);display:grid;gap:var(--s2)}.issue .actions{justify-content:flex-start}.issue details{max-width:68ch}.issue details p{padding:var(--s3) 0;overflow-wrap:anywhere}
.keyboard-help{padding:var(--s3) 0;max-width:100%}.keyboard-help p{margin-top:var(--s2);color:var(--ink-2)}.shortcut-line{display:flex;align-items:center;flex-wrap:nowrap;gap:var(--s4);white-space:nowrap;overflow-x:auto;padding-bottom:var(--s1);scrollbar-width:thin}.shortcut-line span{flex:none}.shortcut-line kbd+kbd{margin-left:var(--s1)}.shortcut-note{font-size:var(--fs-code)}kbd{font:var(--fs-code) var(--mono);border:1px solid var(--line-strong);border-radius:var(--r-sm);padding:2px var(--s1);background:var(--surface)}
.foot{padding-top:var(--s5);font-size:var(--fs-code)}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.skip{position:absolute;left:var(--s5);top:-100px;z-index:10;background:var(--surface);padding:var(--s2)}.skip:focus{top:var(--s2)}
#progress{position:fixed;top:0;left:0;height:2px;width:100%;z-index:10;background:var(--accent);display:none}body.loading #progress{display:block;animation:progress 1s ease-out infinite}body.loading #results{opacity:.6}
::-webkit-scrollbar{width:12px;height:12px}::-webkit-scrollbar-track{background:var(--paper)}::-webkit-scrollbar-thumb{background:var(--accent);border:3px solid var(--paper);border-radius:var(--r-md)}
@keyframes selection-enter{from{transform:translate(-50%,100%)}to{transform:translate(-50%,0)}}@keyframes progress{from{clip-path:inset(0 80% 0 0)}to{clip-path:inset(0)}}
@media(max-width:1250px){.preset-inline{display:none}.preset-menu{display:block}}
@media(max-width:1150px){.filters fieldset{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) minmax(0,1fr) auto}.filters .search{grid-column:1/4;grid-row:2}.filters .apply{grid-column:4;grid-row:2}}
@media(max-width:1100px){.topbar{gap:var(--s3)}.column-head{grid-template-columns:28px minmax(0,1fr) minmax(0,1fr);gap:var(--s2) var(--s4);min-height:40px}.column-head>.column-cell:nth-child(2),.column-head>.column-cell:nth-child(5){display:none}.column-head>.column-cell:nth-child(3){grid-column:2}.column-head>.column-cell:nth-child(4){grid-column:3}.row{grid-template-columns:28px minmax(0,1fr) minmax(0,1fr);gap:var(--s3) var(--s4)}.row .pick{grid-column:1;grid-row:1/4}.row .date-type{grid-column:2;grid-row:1}.row .identification{grid-column:2;grid-row:2}.row .analysis{grid-column:3;grid-row:1/3}.row .links{grid-column:2/4;grid-row:3}.links{display:flex;flex-wrap:wrap;gap:var(--s3)}.detail-body{max-width:68ch}}
@media(max-width:900px){.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));max-height:128px}.scrolled .metrics{max-height:0}.metric:nth-child(3){border-right:0}.metric:nth-child(-n+3){border-bottom:1px solid var(--line)}.filters fieldset{grid-template-columns:repeat(2,minmax(0,1fr))}.filters .period-field,.filters .search,.filters .apply{grid-column:1/-1;grid-row:auto}.filters .apply{width:100%}}
@media(max-width:700px){.topbar{position:static;min-height:76px;flex-wrap:wrap;padding-block:var(--s2);gap:var(--s2) var(--s3)}.view-nav{height:44px;order:3;width:100%;justify-content:center}.run-pill{font-size:var(--fs-code);padding-inline:var(--s2)}.help{margin-left:auto}.filters{position:static}.scrolled .filters{padding:var(--s3) 0}.scrolled .filter-state{display:flex}.filter-state{flex-wrap:wrap}.filter-chips{flex-basis:70%}.metrics,.scrolled .metrics{grid-template-columns:repeat(2,minmax(0,1fr));max-height:none}.metric{height:56px;padding-inline:var(--s3);gap:var(--s1);border-right:1px solid var(--line);border-bottom:1px solid var(--line)}.metric:first-child{padding-left:var(--s3)}.metric:nth-child(even){border-right:0}.column-head{position:static;display:flex;align-items:center;height:auto;padding:var(--s2);gap:var(--s2)}.column-head>.column-cell:nth-child(4){display:none}.column-head>.column-cell:nth-child(3){display:flex}.row{grid-template-columns:28px minmax(0,1fr)}.row .pick{grid-column:1;grid-row:1/5}.row .date-type,.row .identification,.row .analysis,.row .links{grid-column:2;grid-row:auto}.results-toolbar{align-items:flex-start;flex-wrap:wrap}.results-actions{flex-wrap:wrap}.selection-bar{width:calc(100% - 32px);flex-wrap:wrap;gap:var(--s2);bottom:0}.selection-bar strong{width:100%}.selection-bar button{font-size:var(--fs-code)}.calendar-grid{gap:var(--s1)}.calendar-day{min-height:88px;padding:var(--s2)}.calendar-day span{font-size:var(--fs-code)}.calendar-day .calendar-total{display:none}.agency,.code{white-space:normal;overflow-wrap:anywhere}.calendar-nav{justify-content:center}}
@media(max-width:700px){.range-panel{position:fixed;top:50%;left:var(--page-gutter);width:calc(100vw - var(--page-gutter) - var(--page-gutter));max-height:calc(100dvh - var(--s6));transform:translateY(-50%);z-index:2;padding:var(--s3)}.range-months{grid-template-columns:1fr}.range-backdrop:not([hidden]){display:block;position:fixed;inset:0;z-index:1;background:oklch(.26 .020 250 / .28)}body.range-open{overflow:hidden}}
@media(max-width:520px){.date-control>.icon-button{display:none}.topbar h1{font-size:1.125rem}.run-pill{margin-left:0}}
@media(max-width:400px){.filters fieldset{grid-template-columns:1fr}.filters .period-field,.filters .search,.filters .apply{grid-column:1}.period-control{height:auto;display:grid;grid-template-columns:1fr}.period-date{min-height:40px}.period-date+ .period-date{border-left:0;border-top:1px solid var(--line);padding-left:0}.calendar-day{padding:var(--s1);min-height:80px}.calendar-day span{overflow-wrap:anywhere}.selection-bar button{padding-inline:var(--s2)}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
"""

SCRIPT = r"""
(() => {
 const $ = (s) => document.querySelector(s);
 const rows = [...document.querySelectorAll('.row')];
 const form = $('#filters');
 const search = $('#q');
 const key = 'epesf-selection:' + ($('#selection-form input[name=date]')?.value || '');
 const storage = {get:(k) => {try{return localStorage.getItem(k)}catch{return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch{}}};
 let emailBusy=false;
 let selected;
 try {selected = new Set(JSON.parse(sessionStorage.getItem(key) || '[]'));} catch {selected = new Set();}
 function updateSelection(){
   const checked = rows.filter(r => r.querySelector('input[name=selected]:checked'));
   rows.forEach(r => r.toggleAttribute('data-selected', !!r.querySelector('input[name=selected]:checked')));
   $('#selection-count').textContent = `${checked.length} seleccionada${checked.length === 1 ? '' : 's'}`;
   $('#selection-bar').hidden = !checked.length;
   const available=rows.filter(r=>r.querySelector('input[name=selected]:not(:disabled)'));
   const all=$('#select-all');if(all){all.checked=!!available.length && checked.length===available.length;all.indeterminate=checked.length>0 && checked.length<available.length;all.disabled=!available.length;}
   document.querySelectorAll('[data-email]').forEach(b => {b.disabled = emailBusy || !checked.length;b.title = checked.length ? 'Generar correo con seleccionadas' : 'Seleccioná al menos una publicación con resumen completo';});
   try{sessionStorage.setItem(key,JSON.stringify(checked.map(r=>r.dataset.id)));}catch{}
 }
 rows.forEach(r=>{
   const box = r.querySelector('input[name=selected]');
   if(box && !box.disabled){box.checked=selected.has(r.dataset.id);box.addEventListener('change',updateSelection);}
 });
 if($('#selection-bar')) updateSelection();
 $('#select-all')?.addEventListener('change',e=>{
   rows.forEach(r=>{const box=r.querySelector('input[name=selected]:not(:disabled)');if(box)box.checked=e.target.checked;});updateSelection();
 });
 document.querySelectorAll('[data-select]').forEach(b => b.addEventListener('click',()=>{
   rows.forEach(r=>{const box=r.querySelector('input[name=selected]:not(:disabled)');if(box)box.checked=b.dataset.select==='all';});updateSelection();
 }));
 $('#export-selected')?.addEventListener('click',()=>{
   const url = new URL($('#export-view').href);
   rows.forEach(r=>{const box=r.querySelector('input[name=selected]:checked');if(box)url.searchParams.append('selected',box.value);});
   window.location.assign(url);
 });
 function setDensity(value){document.body.classList.toggle('compact',value==='compact');document.querySelectorAll('[data-density]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.density===value)));storage.set('epesf-density',value);}
 setDensity(storage.get('epesf-density') || 'comfortable');
 document.querySelectorAll('[data-density]').forEach(b=>b.addEventListener('click',()=>setDensity(b.dataset.density)));
 const previous = storage.get('epesf-last-visit');
 rows.forEach(r=>{if(previous && Date.parse(r.dataset.created) > Date.parse(previous))r.setAttribute('data-unread','');});
 storage.set('epesf-last-visit',new Date().toISOString());
 function offsets(){document.body.classList.toggle('scrolled',window.scrollY>32);const topbarHeight=$('.topbar').getBoundingClientRect().height;document.documentElement.style.setProperty('--topbar-height',`${topbarHeight}px`);document.documentElement.style.setProperty('--columns-top',`${topbarHeight + (form && getComputedStyle(form).position==='sticky' ? form.getBoundingClientRect().height : 0)}px`);}
 window.addEventListener('scroll',offsets,{passive:true});window.addEventListener('resize',offsets);new ResizeObserver(offsets).observe($('.topbar'));if(form)new ResizeObserver(offsets).observe(form);offsets();
 function loading(){document.body.classList.add('loading');$('#results')?.setAttribute('aria-busy','true');const apply=form?.querySelector('.apply');if(apply)apply.disabled=true;}
 form?.addEventListener('submit',loading);
 $('.month-picker')?.addEventListener('submit',loading);
 $('[data-month-submit]')?.addEventListener('change',e=>e.target.form.requestSubmit());
 document.querySelectorAll('[data-auto-submit]').forEach(c=>c.addEventListener('change',()=>{
   if(c.id==='date'||c.id==='to'){
     const from=$('#date'),to=$('#to');
     if(c.id==='date' && from.value && (!to.value || from.value>to.value))to.value=from.value;
     if(c.id==='to' && to.value && (!from.value || to.value<from.value))from.value=to.value;
     if(from.value || to.value)form.elements.view.value='day';
   }
   form.requestSubmit();
 }));
 const picker=$('#range-picker');
 if(picker){
   const trigger=$('#range-trigger'),panel=$('#range-panel'),backdrop=picker.querySelector('.range-backdrop');
   const months=panel.querySelector('.range-months'),message=panel.querySelector('.range-message');
   const from=$('#date'),to=$('#to'),apply=panel.querySelector('.range-apply'),clear=panel.querySelector('.range-clear');
   const maxDay=picker.dataset.max;
   const parseDay=value=>{const [year,month,day]=value.split('-').map(Number);return new Date(year,month-1,day);};
   const isoDay=value=>`${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`;
   const monthStart=value=>new Date(value.getFullYear(),value.getMonth(),1);
   const addMonths=(value,count)=>new Date(value.getFullYear(),value.getMonth()+count,1);
   const monthText=new Intl.DateTimeFormat('es-AR',{month:'long'});
   const dayText=new Intl.DateTimeFormat('es-AR',{day:'numeric',month:'long',year:'numeric'});
   const visibleMonths=()=>window.matchMedia('(max-width:700px)').matches?1:2;
   let firstMonth=monthStart(parseDay(from.value || maxDay));
   let draftFrom='',draftTo='',hoverDay='';
   function clampMonth(){const last=addMonths(monthStart(parseDay(maxDay)),1-visibleMonths());if(firstMonth>last)firstMonth=last;}
   function paintDays(){
     const previewEnd=draftTo || (draftFrom && hoverDay>=draftFrom ? hoverDay : '');
     months.querySelectorAll('.range-day').forEach(button=>{
       const day=button.dataset.day;
       const edge=day===draftFrom || day===draftTo;
       button.classList.toggle('is-edge',!!edge);
       button.classList.toggle('is-between',!!draftFrom && !!previewEnd && day>draftFrom && day<previewEnd);
       button.classList.toggle('is-preview-edge',!draftTo && !!hoverDay && day===hoverDay && day!==draftFrom);
       button.classList.toggle('is-today',day===maxDay);
       button.setAttribute('aria-pressed',String(!!edge));
       button.setAttribute('aria-label',dayText.format(parseDay(day))+(day===draftFrom?' · inicio':'')+(day===draftTo?' · fin':''));
     });
     message.textContent=!draftFrom?'Elegí la fecha de inicio.':!draftTo?'Elegí la fecha de fin o aplicá un solo día.':`${dayText.format(parseDay(draftFrom))} – ${dayText.format(parseDay(draftTo))}`;
     apply.disabled=!draftFrom;clear.disabled=!draftFrom && !draftTo;
   }
   function renderMonths(){
     clampMonth();months.replaceChildren();
     for(let index=0;index<visibleMonths();index++){
       const month=addMonths(firstMonth,index),section=document.createElement('section');section.className='range-month';
       const title=document.createElement('h3');const name=monthText.format(month);title.textContent=name[0].toUpperCase()+name.slice(1)+' '+month.getFullYear();section.append(title);
       const weekdays=document.createElement('div');weekdays.className='range-weekdays';
       ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'].forEach(label=>{const span=document.createElement('span');span.textContent=label;weekdays.append(span);});section.append(weekdays);
       const days=document.createElement('div');days.className='range-days';
       for(let blank=0;blank<month.getDay();blank++){const spacer=document.createElement('span');spacer.setAttribute('aria-hidden','true');days.append(spacer);}
       const count=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
       for(let number=1;number<=count;number++){
         const day=new Date(month.getFullYear(),month.getMonth(),number),key=isoDay(day);
         const button=document.createElement('button');button.type='button';button.className='range-day';button.textContent=String(number);button.dataset.day=key;button.disabled=key>maxDay;
         button.addEventListener('click',()=>{
           if(!draftFrom || draftTo){draftFrom=key;draftTo='';}
           else if(key<draftFrom){draftTo=draftFrom;draftFrom=key;}
           else draftTo=key;
           hoverDay='';paintDays();
         });
         button.addEventListener('mouseenter',()=>{if(draftFrom && !draftTo){hoverDay=key;paintDays();}});
         days.append(button);
       }
       days.addEventListener('mouseleave',()=>{if(hoverDay){hoverDay='';paintDays();}});
       section.append(days);months.append(section);
     }
     panel.querySelector('[data-month-step="1"]').disabled=addMonths(firstMonth,1)>addMonths(monthStart(parseDay(maxDay)),1-visibleMonths());
     paintDays();
   }
   function closeRange(returnFocus=true){panel.hidden=true;backdrop.hidden=true;trigger.setAttribute('aria-expanded','false');form.classList.remove('range-active');document.body.classList.remove('range-open');if(returnFocus)trigger.focus();}
   function openRange(){
     draftFrom=from.value;draftTo=to.value;hoverDay='';
     firstMonth=monthStart(parseDay(draftFrom || maxDay));
     panel.hidden=false;backdrop.hidden=false;trigger.setAttribute('aria-expanded','true');form.classList.add('range-active');document.body.classList.add('range-open');
     renderMonths();
     const focusDay=months.querySelector(`[data-day="${draftFrom || maxDay}"]`);
     (focusDay || panel.querySelector('[data-month-step="-1"]')).focus();
   }
   picker.classList.add('enhanced');
   trigger.addEventListener('click',()=>panel.hidden?openRange():closeRange());
   backdrop.addEventListener('click',closeRange);
   document.addEventListener('pointerdown',event=>{if(!panel.hidden && !picker.contains(event.target))closeRange(false);});
   document.addEventListener('keydown',event=>{if(event.key==='Escape' && !panel.hidden){event.preventDefault();closeRange();}});
   panel.querySelectorAll('[data-month-step]').forEach(button=>button.addEventListener('click',()=>{firstMonth=addMonths(firstMonth,Number(button.dataset.monthStep));renderMonths();}));
   months.addEventListener('keydown',event=>{
     const button=event.target.closest('.range-day');if(!button)return;
     const move={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key];if(!move)return;
     event.preventDefault();event.stopPropagation();const target=parseDay(button.dataset.day);target.setDate(target.getDate()+move);const key=isoDay(target);if(key>maxDay)return;
     const targetMonth=monthStart(target);
     if(targetMonth<firstMonth)firstMonth=targetMonth;
     else if(targetMonth>addMonths(firstMonth,visibleMonths()-1))firstMonth=addMonths(targetMonth,1-visibleMonths());
     renderMonths();months.querySelector(`[data-day="${key}"]`)?.focus();
   });
   clear.addEventListener('click',()=>{draftFrom='';draftTo='';hoverDay='';paintDays();});
   apply.addEventListener('click',()=>{if(!draftFrom)return;from.value=draftFrom;to.value=draftTo || draftFrom;form.elements.view.value='day';form.requestSubmit();});
   window.addEventListener('resize',()=>{if(!panel.hidden){firstMonth=monthStart(parseDay(draftFrom || maxDay));renderMonths();}});
 }
 $('#clear-search')?.addEventListener('click',()=>{search.value='';form.requestSubmit();});
 window.addEventListener('pageshow',()=>{document.body.classList.remove('loading');$('#results')?.removeAttribute('aria-busy');const apply=form?.querySelector('.apply');if(apply)apply.disabled=false;});
 function emailFailure(message,files=[]){
   const notice=$('#action-notice');notice.classList.add('error');notice.setAttribute('role','alert');notice.replaceChildren();
   const text=document.createElement('p');text.textContent=message;notice.append(text);
   files.forEach(file=>{
     const actions=document.createElement('div');actions.className='actions';
     const link=document.createElement('a');link.href=file.url;link.download=file.name;link.textContent='Descargar '+file.name;
     const button=document.createElement('button');button.type='button';button.textContent='Volver a abrir';
     button.addEventListener('click',()=>retryEmail([file],button));actions.append(link,button);notice.append(actions);
   });
   notice.hidden=false;notice.scrollIntoView({block:'center'});
 }
 async function watchEmailOpen(token,files){
   try{
     for(let attempt=0;attempt<15;attempt++){
       const response=await fetch('/email-open-status?token='+encodeURIComponent(token),{signal:AbortSignal.timeout(8000)});
       if(!response.ok)throw new Error('No se pudo confirmar la apertura de la aplicación de correo.');
       const state=await response.json();
       if(state.status==='complete'){const notice=$('#action-notice');notice.classList.remove('error');notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');notice.textContent='Borrador listo — se abrió en tu cliente de correo. No se envió nada automáticamente.';notice.hidden=false;return;}
       if(state.status==='error')throw new Error(state.error || 'No se pudo abrir la aplicación de correo.');
       await new Promise(resolve=>setTimeout(resolve,2000));
     }
     throw new Error('La apertura de la aplicación de correo sigue pendiente.');
   }catch(error){emailFailure('El correo quedó guardado. '+(error.name==='TimeoutError' || error.name==='TypeError'?'No se pudo confirmar su apertura.':error.message),files);}
 }
 async function retryEmail(files,button){
   button.disabled=true;
   try{
     const body=new URLSearchParams();files.forEach(file=>body.append('eml',file.name));
     const response=await fetch('/open-email',{method:'POST',body,signal:AbortSignal.timeout(8000)});
     const result=await response.json();if(!response.ok)throw new Error(result.error || 'No se pudo abrir la aplicación de correo.');
     $('#action-notice').hidden=true;await watchEmailOpen(result.token,files);
   }catch(error){emailFailure('El correo quedó guardado. '+(error.name==='TimeoutError' || error.name==='TypeError'?'No se pudo conectar con el servicio local.':error.message),files);}
   finally{button.disabled=false;}
 }
 $('#selection-form')?.addEventListener('submit',async e=>{
   e.preventDefault();if(emailBusy)return;
   const submitted=[...e.target.querySelectorAll('input[name=selected]:checked')];
   const body=new URLSearchParams(new FormData(e.target));
   const buttons=[...document.querySelectorAll('[data-email]')], labels=buttons.map(b=>b.innerHTML);
   emailBusy=true;buttons.forEach(b=>{b.disabled=true;b.textContent='Preparando…';});
   $('#action-notice').hidden=true;
   try{
     const response=await fetch('/prepare-email',{method:'POST',body,headers:{Accept:'application/json'},signal:AbortSignal.timeout(30000)});
     const result=await response.json();
     if(!response.ok || !result.generated)throw new Error(result.error || 'No se pudo generar el correo. Reintentá.');
     submitted.forEach(box=>{box.checked=false;});updateSelection();
     document.querySelectorAll('.email-notice').forEach(notice=>notice.remove());
     const url=new URL(window.location.href);['email','items','files','eml','email_error'].forEach(key=>url.searchParams.delete(key));window.history.replaceState(null,'',url);
     if(result.error)emailFailure('El correo quedó guardado. '+result.error,result.files);
     else if(result.token)void watchEmailOpen(result.token,result.files);
   }catch(error){
     emailFailure(error.name==='TimeoutError'?'El servicio tardó demasiado. Revisá la conexión local y reintentá.':error.name==='TypeError'?'No se pudo conectar con el servicio local. Reintentá.':error.message);
   }finally{
     emailBusy=false;buttons.forEach((b,i)=>{b.innerHTML=labels[i];});updateSelection();
   }
 });
 document.querySelectorAll('.email-open-form').forEach(f=>f.addEventListener('submit',async e=>{
   e.preventDefault();const name=new FormData(f).get('eml');await retryEmail([{name,url:'/email?name='+encodeURIComponent(name)}],f.querySelector('button'));
 }));
 document.querySelectorAll('.title a').forEach(a=>a.addEventListener('click',e=>{const row=a.closest('.row');const d=row.querySelector('details');if(d){e.preventDefault();d.open=!d.open;row.focus({preventScroll:true});}}));
 const help = $('#keyboard-help');
 $('#help-toggle').addEventListener('click',e=>{e.preventDefault();help.open=!help.open;if(help.open)help.scrollIntoView({block:'center'});});
 let rowIndex=-1;
 document.addEventListener('keydown',e=>{
   if(e.ctrlKey||e.metaKey||e.altKey)return;
   const editing=e.target.matches('input,select,textarea,[contenteditable=true]');
   if(e.key==='Escape' && e.target===search){e.preventDefault();search.value='';form.requestSubmit();return;}
   if(editing)return;
   if(e.key==='/' && search){e.preventDefault();search.focus();return;}
   if(e.key==='?'){e.preventDefault();help.open=!help.open;if(help.open)help.scrollIntoView({block:'center'});return;}
   if(e.key==='ArrowLeft'||e.key==='ArrowRight'){if(!$('#range-panel')?.hidden)return;const a=$(e.key==='ArrowLeft'?'#previous-day':'#next-day');if(a?.href && a.getAttribute('aria-disabled')!=='true'){e.preventDefault();window.location.assign(a.href);}return;}
   const focused=e.target.closest('.row');if(focused)rowIndex=rows.indexOf(focused);
   if((e.key==='j'||e.key==='k') && rows.length){e.preventDefault();rowIndex=Math.max(0,Math.min(rows.length-1,rowIndex+(e.key==='j'?1:-1)));rows[rowIndex].focus();return;}
   if(e.key==='x' && focused){const box=focused.querySelector('input[name=selected]:not(:disabled)');if(box){e.preventDefault();box.checked=!box.checked;updateSelection();}}
   if(e.key==='Enter' && e.target.matches('.row')){const d=e.target.querySelector('details');if(d){e.preventDefault();d.open=!d.open;}}
 });
 const actionNotice = $('#action-notice');
 document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',async()=>{
   const original=b.textContent;b.disabled=true;b.textContent=b.dataset.action==='summary'?'Generando…':'Consultando…';b.setAttribute('aria-busy','true');actionNotice.hidden=true;
   try{
     const body=new URLSearchParams({date:b.dataset.day || '',id:b.dataset.id || ''});
     const response=await fetch('/'+b.dataset.action,{method:'POST',body});const result=await response.json();
     if(!response.ok)throw new Error(result.error || 'No se pudo completar la acción. Reintentá.');
     try{sessionStorage.setItem('epesf-scroll',String(window.scrollY));}catch{}
     const url=new URL(window.location.href);url.searchParams.set('action_done',b.dataset.action);window.location.replace(url);
   }catch(error){actionNotice.textContent=error.message;actionNotice.hidden=false;actionNotice.scrollIntoView({block:'center'});}
   finally{b.disabled=false;b.textContent=original;b.removeAttribute('aria-busy');}
 }));
 try{const y=sessionStorage.getItem('epesf-scroll');if(y){window.scrollTo(0,Number(y));sessionStorage.removeItem('epesf-scroll');}}catch{}
})();
"""
