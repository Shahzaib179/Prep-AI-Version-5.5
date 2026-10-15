"""The Prep.AI stylesheet: one set of design tokens (CSS variables) and the component styles that use them.

Only stable hooks are used: Streamlit's data-testid attributes, the ``st-key-<key>`` class Streamlit adds to keyed elements, and our own ``pp-*`` classes.
Every colour comes from a variable, so the same CSS serves the light brand theme and the user's own colour themes (theme.build_css sets the variables).
"""
from __future__ import annotations

FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');"

COMPONENT_CSS = r"""
html, body, .stApp, [data-testid="stAppViewContainer"], button, input, textarea, select { font-family: Inter, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
.stApp { background: var(--p-bg); color: var(--p-text); }
[data-testid="stHeader"] { background: transparent; }
footer, #MainMenu { visibility: hidden; }
.block-container { padding: 1rem 2rem 4rem; max-width: 1320px; }
h1, h2, h3, h4 { color: var(--p-text); letter-spacing: -0.01em; }
h1 { font-weight: 800; font-size: 1.9rem; } h2 { font-weight: 700; font-size: 1.45rem; } h3 { font-weight: 700; font-size: 1.15rem; }
p, li, label, .stMarkdown { color: var(--p-text); }
[data-testid="stCaptionContainer"], .small-muted { color: var(--p-muted) !important; }
a { color: var(--p-primary); }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: var(--p-card); border-right: 1px solid var(--p-border); }
[data-testid="stSidebar"] > div:first-child { padding-top: .4rem; }
[data-testid="stSidebarContent"] { padding: 0 .9rem 1rem; }
.pp-brand { display: flex; align-items: center; gap: .6rem; font-weight: 800; font-size: 1.3rem; color: var(--p-text); padding: .5rem .2rem .6rem; line-height: 1.1; }
.pp-brand img.pp-logo { height: 40px; width: auto; flex: none; display: block; }
.pp-brand .pp-wm em { color: var(--p-primary); font-style: normal; }
.pp-login-logo { display: block; margin: 0 auto .4rem; height: 96px; width: auto; }
/* The sidebar header (brand, goal card) is ONE markdown block built from normal-flow elements: nothing is positioned, nothing relies on a neighbour's margin.
   Streamlit's markdown wrappers can collapse or pull back the margin of their last child, which is what slid the "MAIN" label and first nav item under the goal card. */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { overflow: visible; margin-bottom: 0 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > :last-child { margin-bottom: 0; }
.pp-goal { display: flow-root; box-sizing: border-box; width: 100%; background: linear-gradient(135deg, var(--p-primary), var(--p-primary-dark)); color: #fff; border-radius: 16px; padding: .85rem 1rem .9rem; margin: 0 0 .5rem; box-shadow: 0 6px 16px var(--p-primary-soft2); overflow-wrap: anywhere; }
.pp-goal .g-label { display: block; letter-spacing: .12em; font-weight: 700; font-size: .66rem; opacity: .85; text-transform: uppercase; line-height: 1.3; }
.pp-goal .g-big { display: block; font-size: 1.25rem; font-weight: 800; line-height: 1.25; margin: .2rem 0 .25rem; }
.pp-goal .g-small { display: block; font-size: .78rem; line-height: 1.4; opacity: .92; }
.pp-goal .g-bar { display: block; height: 6px; border-radius: 99px; background: rgba(255,255,255,.28); margin-top: .55rem; overflow: hidden; }
.pp-goal .g-bar i { display: block; height: 100%; border-radius: 99px; background: #fff; }
.st-key-sb_edit_goal button { min-height: 2rem; padding: .2rem .6rem; font-size: .82rem; }
.st-key-sb_edit_goal { margin-bottom: .4rem; }
.pp-navlabel { display: block; font-size: .68rem; letter-spacing: .12em; font-weight: 700; color: var(--p-muted); text-transform: uppercase; line-height: 1.3; margin: 0; padding: .95rem .75rem .35rem; }
/* Sidebar items: one fixed icon column, then the label, every row left aligned. Streamlit centres button content (several nested wrappers each centre it),
   so EVERY descendant of the button is forced to start-align, and auto margins push the content to the left edge even if a wrapper keeps its own centring. */
[class*="st-key-nav_"], [class*="st-key-navon_"] { width: 100% !important; }
[class*="st-key-nav_"] [data-testid="stButton"], [class*="st-key-navon_"] [data-testid="stButton"] { width: 100% !important; display: flex !important; justify-content: flex-start !important; }
[class*="st-key-nav_"] button, [class*="st-key-navon_"] button { width: 100% !important; display: flex !important; flex-direction: row !important; align-items: center !important; justify-content: flex-start !important; text-align: left !important; gap: .8rem !important;
  background: transparent !important; border: 0 !important; box-shadow: none !important; color: var(--p-text) !important; font-weight: 500; padding: .5rem .75rem !important; border-radius: 12px; min-height: 2.5rem; }
[class*="st-key-nav_"] button *, [class*="st-key-navon_"] button * { justify-content: flex-start !important; text-align: left !important; }
[class*="st-key-nav_"] button > *, [class*="st-key-navon_"] button > * { margin: 0 !important; }
[class*="st-key-nav_"] button > :last-child, [class*="st-key-navon_"] button > :last-child { margin-right: auto !important; }
[class*="st-key-nav_"] button div, [class*="st-key-navon_"] button div { display: flex !important; align-items: center !important; width: auto !important; max-width: none !important; flex: 0 1 auto !important; }
[class*="st-key-nav_"] button p, [class*="st-key-navon_"] button p { display: flex !important; align-items: center !important; gap: .8rem !important; width: auto !important; margin: 0 !important; font-size: .95rem; line-height: 1.25; white-space: nowrap; }
[class*="st-key-nav_"] button [data-testid="stIconMaterial"], [class*="st-key-navon_"] button [data-testid="stIconMaterial"],
[class*="st-key-nav_"] button span[class*="material"], [class*="st-key-navon_"] button span[class*="material"] { flex: 0 0 1.5rem !important; width: 1.5rem !important; min-width: 1.5rem !important; display: inline-flex !important; justify-content: center !important; align-items: center !important; font-size: 1.4rem !important; margin: 0 !important; }
[class*="st-key-nav_"] button:hover { background: var(--p-primary-soft) !important; color: var(--p-primary) !important; }
[class*="st-key-navon_"] button { background: var(--p-primary-soft) !important; color: var(--p-primary) !important; font-weight: 700; }
[class*="st-key-nav_"] [data-testid="stElementContainer"], [class*="st-key-navon_"] [data-testid="stElementContainer"] { margin: 0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .1rem; }
[data-testid="stSidebar"] hr { margin: .6rem 0; border-color: var(--p-border); }

/* ---------- top bar and headings ---------- */
.pp-topbar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; background: var(--p-card); border: 1px solid var(--p-border); border-radius: 16px; padding: .55rem .9rem; margin: 0 0 1.1rem; }
.pp-crumb { color: var(--p-muted); font-size: .92rem; } .pp-crumb b { color: var(--p-text); }
.pp-chips { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.pp-chip { background: var(--p-bg); border: 1px solid var(--p-border); border-radius: 999px; padding: .22rem .7rem; font-size: .82rem; font-weight: 600; color: var(--p-text); white-space: nowrap; }
.pp-user { display: inline-flex; align-items: center; gap: .55rem; font-weight: 600; font-size: .9rem; margin-left: .3rem; }
.pp-user small { display: block; font-weight: 400; color: var(--p-muted); font-size: .72rem; line-height: 1.1; }
.pp-avatar { width: 34px; height: 34px; border-radius: 50%; display: inline-grid; place-items: center; background: var(--p-primary); color: #fff; font-weight: 800; }
.prep-hero { background: var(--p-card); border: 1px solid var(--p-border); border-left: 5px solid var(--p-primary); border-radius: 16px; padding: 1rem 1.3rem; margin-bottom: 1.1rem; color: var(--p-text); }
.prep-hero h1 { margin: 0; font-size: 1.55rem; color: var(--p-text); } .prep-hero p { margin: .25rem 0 0; color: var(--p-muted); }
.stApp .prep-hero, .stApp .prep-hero * { color: inherit; } .stApp .prep-hero h1 { color: var(--p-text); } .stApp .prep-hero p { color: var(--p-muted); }
.pp-greet h1 { font-size: 1.9rem; margin: .2rem 0 .1rem; } .pp-greet p { color: var(--p-primary); font-style: italic; margin: 0 0 1rem; font-weight: 500; }

/* ---------- cards, containers ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--p-card); border-color: var(--p-border) !important; border-radius: 18px; box-shadow: 0 1px 2px rgba(24,43,73,.04), 0 6px 18px rgba(24,43,73,.04); }
div[data-testid="stForm"] { border-radius: 18px; border-color: var(--p-border); background: var(--p-card); }
[data-testid="stExpander"] details { background: var(--p-card); border: 1px solid var(--p-border); border-radius: 14px; }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stMetric"] { background: var(--p-card); border: 1px solid var(--p-border); border-radius: 16px; padding: .7rem .9rem; }
[data-testid="stMetricValue"] { font-weight: 800; color: var(--p-text); } [data-testid="stMetricLabel"] { color: var(--p-muted); }
.pp-label { font-size: .72rem; letter-spacing: .1em; font-weight: 700; color: var(--p-muted); text-transform: uppercase; margin: .15rem 0 .5rem; }
.pp-empty { color: var(--p-muted); background: var(--p-bg); border: 1px dashed var(--p-border); border-radius: 12px; padding: .85rem 1rem; font-size: .92rem; margin: .2rem 0 .6rem; }
.pp-badge { display: inline-block; font-size: .72rem; font-weight: 700; padding: .12rem .55rem; border-radius: 999px; background: var(--p-bg); border: 1px solid var(--p-border); color: var(--p-muted); white-space: nowrap; }
.pp-badge.ok { background: var(--p-ok-soft); color: var(--p-ok); border-color: transparent; } .pp-badge.warn { background: var(--p-warn-soft); color: var(--p-warn); border-color: transparent; } .pp-badge.err { background: var(--p-err-soft); color: var(--p-err); border-color: transparent; }
.pp-row { display: flex; justify-content: space-between; align-items: center; gap: .8rem; padding: .55rem 0; border-bottom: 1px solid var(--p-border); font-weight: 600; font-size: .92rem; }
.pp-row:last-child { border-bottom: 0; } .pp-row small { display: block; font-weight: 400; color: var(--p-muted); font-size: .78rem; }

/* ---------- dashboard ---------- */
.pp-line { background: linear-gradient(135deg, var(--p-primary), var(--p-primary-dark)); color: #fff; border-radius: 16px; padding: 1rem 1.2rem 1.1rem; margin-bottom: .8rem; position: relative; }
.pp-line .pp-title { font-size: 1.2rem; font-weight: 800; } .pp-line p { margin: .25rem 0 1rem; opacity: .92; font-size: .88rem; color: #fff; }
.pp-done { position: absolute; right: 1rem; top: .9rem; background: rgba(0,0,0,.28); border-radius: 999px; padding: .12rem .7rem; font-size: .78rem; font-weight: 700; }
.pp-track { position: relative; height: 6px; border-radius: 99px; background: rgba(255,255,255,.3); margin: .6rem .4rem .3rem; }
.pp-track i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 99px; background: #fff; }
.pp-track b { position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%; transform: translate(-50%, -50%); background: rgba(255,255,255,.55); border: 2px solid rgba(255,255,255,.9); }
.pp-track b.on { background: #fff; }
.pp-task { display: flex; gap: .7rem; align-items: flex-start; padding: .3rem 0; }
.pp-tick { flex: none; width: 22px; height: 22px; border-radius: 7px; border: 2px solid var(--p-border); display: inline-grid; place-items: center; font-size: .8rem; font-weight: 800; color: #fff; margin-top: .1rem; }
.pp-tick.on { background: var(--p-ok); border-color: var(--p-ok); }
.pp-task .t { font-weight: 600; font-size: .94rem; } .pp-task .t.done { text-decoration: none; color: var(--p-muted); } .pp-task .d { font-size: .78rem; color: var(--p-muted); }
.pp-subjects { display: flex; justify-content: space-between; gap: .4rem; flex-wrap: wrap; margin: .2rem 0 .8rem; text-align: center; }
.pp-subjects .n { font-size: .68rem; font-weight: 700; letter-spacing: .08em; color: var(--p-muted); margin-top: .1rem; }
.pp-gauge { text-align: center; }
[class*="st-key-feat_"] button { justify-content: flex-start; text-align: left; border-radius: 14px; border: 0; background: transparent; font-weight: 700; padding: .35rem .2rem; box-shadow: none; }
[class*="st-key-feat_"] button:hover { color: var(--p-primary); background: var(--p-primary-soft); }
[class*="st-key-feat_"] [data-testid="stCaptionContainer"] { padding: 0 .3rem .2rem; margin-top: -.3rem; font-size: .8rem; }
.pp-qnav { display: flex; flex-wrap: wrap; gap: .35rem; margin: .4rem 0 1rem; }
.pp-qnav a { width: 32px; height: 32px; display: inline-grid; place-items: center; border-radius: 10px; border: 1px solid var(--p-border); background: var(--p-card); color: var(--p-text); text-decoration: none; font-weight: 700; font-size: .82rem; }
.pp-qnav a.on { background: var(--p-primary); color: #fff; border-color: var(--p-primary); }
.pp-qcard { display: flex; gap: .7rem; align-items: flex-start; background: var(--p-card); border: 1px solid var(--p-border); border-radius: 16px; padding: .9rem 1.1rem; margin: 1rem 0 .4rem; scroll-margin-top: 4rem; }
.pp-qnum { flex: none; min-width: 34px; height: 34px; border-radius: 11px; display: inline-grid; place-items: center; background: var(--p-primary-soft); color: var(--p-primary); font-weight: 800; }
.pp-qtext { font-size: 1.05rem; font-weight: 600; line-height: 1.45; }

/* ---------- profile button in the top bar ---------- */
.st-key-topbar_row { padding: 0 !important; margin: 0 0 1.1rem; }
.st-key-topbar_row > div { gap: 0; }
.st-key-search_panel { margin: -.5rem 0 1rem; }
.pp-sr-head { font-weight: 700; color: var(--p-muted); font-size: .8rem; letter-spacing: .04em; text-transform: uppercase; }
.pp-sr { line-height: 1.3; } .pp-sr .t { font-weight: 700; } .pp-sr .d { color: var(--p-muted); font-size: .8rem; margin-top: .1rem; }
.st-key-global_search input { border-radius: 99px; }
.pp-topbar.bare { border: 0; padding: 0; margin: 0; background: transparent; }
.st-key-topbar_row [data-testid="stHorizontalBlock"] { padding: .45rem .8rem; align-items: center; }
.st-key-profile_menu { display: flex; justify-content: flex-end; }
.st-key-profile_menu button { border-radius: 999px; font-weight: 700; padding: .25rem .9rem .25rem .5rem; max-width: 100%; }
.st-key-profile_menu button p { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* ---------- games (timed play) ---------- */
.pp-timer { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin: .2rem 0 .6rem; font-weight: 700; }
.pp-timer .big { font-size: 2rem; font-weight: 800; line-height: 1; color: var(--p-primary); font-variant-numeric: tabular-nums; } .pp-timer .big.low { color: var(--p-err); }
.pp-timer small { color: var(--p-muted); font-weight: 600; }
.pp-play .pp-qtext { font-size: 1.15rem; }
[class*="st-key-gopt_"] button { width: 100%; justify-content: flex-start; text-align: left; min-height: 2.8rem; border-radius: 14px; }
/* ---------- bars, predictor, games, leaderboard ---------- */
.pp-bar { height: 8px; border-radius: 99px; background: var(--p-primary-soft2); overflow: hidden; margin: .25rem 0 .1rem; }
.pp-bar i { display: block; height: 100%; border-radius: 99px; background: var(--p-primary); }
.pp-bar.ok i { background: var(--p-ok); } .pp-bar.warn i { background: var(--p-warn); } .pp-bar.err i { background: var(--p-err); }
.pp-barrow { margin: .45rem 0 .6rem; } .pp-barrow .top { display: flex; justify-content: space-between; align-items: baseline; gap: .6rem; font-weight: 600; font-size: .9rem; line-height: 1.3; }
.pp-barrow .top span:last-child { color: var(--p-muted); font-weight: 600; font-size: .8rem; text-align: right; } .pp-barrow small { color: var(--p-muted); font-size: .76rem; }
.pp-vs { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: .6rem; background: var(--p-primary-soft); border-radius: 14px; padding: .7rem 1rem; margin: .4rem 0 .8rem; }
.pp-vs .a small, .pp-vs .c small { display: block; color: var(--p-muted); font-size: .76rem; } .pp-vs .a b, .pp-vs .c b { font-size: 1.5rem; font-weight: 800; line-height: 1.2; }
.pp-vs .a b { color: var(--p-primary); } .pp-vs .c { text-align: right; } .pp-vs .c b { color: var(--p-ok); } .pp-vs .m { text-align: center; font-size: .78rem; font-weight: 600; color: var(--p-muted); max-width: 11rem; }
.pp-trend svg { width: 100%; height: auto; display: block; }
.pp-lb { margin: .2rem 0; } .pp-lb .r { display: grid; grid-template-columns: 2.2rem 1fr auto; align-items: center; gap: .6rem; padding: .5rem .4rem; border-bottom: 1px solid var(--p-border); font-weight: 600; font-size: .93rem; }
.pp-lb .r:last-child { border-bottom: 0; } .pp-lb .r small { display: block; color: var(--p-muted); font-weight: 400; font-size: .74rem; } .pp-lb .r .pts { font-weight: 800; color: var(--p-primary); white-space: nowrap; }
.pp-lb .r.me { background: var(--p-primary-soft); border-radius: 10px; border-bottom-color: transparent; }
.pp-lb .rk { display: inline-grid; place-items: center; width: 1.9rem; height: 1.9rem; border-radius: 50%; background: var(--p-bg); font-size: .8rem; font-weight: 800; color: var(--p-muted); }
.pp-lb .rk.m1 { background: #F5C84C; color: #5a4100; } .pp-lb .rk.m2 { background: #D4D8DE; color: #3b4048; } .pp-lb .rk.m3 { background: #E3A878; color: #54300f; }
.pp-lb .name { overflow-wrap: anywhere; line-height: 1.25; }
.pp-game b.t { font-size: 1.05rem; font-weight: 800; display: block; } .pp-game p { color: var(--p-muted); font-size: .88rem; margin: .2rem 0 .6rem; }

/* ---------- controls ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stBaseButton-secondary"] { border-radius: 12px; border: 1px solid var(--p-border); font-weight: 600; background: var(--p-card); color: var(--p-text); transition: border-color .15s, box-shadow .15s, transform .05s; }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { border-color: var(--p-primary); color: var(--p-primary); box-shadow: 0 2px 8px var(--p-primary-soft2); }
.stButton > button:active { transform: translateY(1px); }
.stButton > button:focus-visible, input:focus-visible, textarea:focus-visible { outline: 2px solid var(--p-primary); outline-offset: 2px; }
button[kind="primary"], button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButtonprimaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"] { background: var(--p-primary) !important; border-color: var(--p-primary) !important; color: #fff !important; }
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { background: var(--p-primary-dark) !important; color: #fff !important; }
button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color: #fff !important; }
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div { border-radius: 12px !important; border-color: var(--p-border) !important; background: var(--p-card) !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within { border-color: var(--p-primary) !important; box-shadow: 0 0 0 1px var(--p-primary); }
[data-testid="stFileUploaderDropzone"] { border: 2px dashed var(--p-border); border-radius: 16px; background: var(--p-card); }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--p-primary); }
div[data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid var(--p-border); flex-wrap: wrap; }
button[role="tab"] { border-radius: 10px 10px 0 0; font-weight: 600; color: var(--p-muted); }
button[role="tab"][aria-selected="true"] { color: var(--p-primary); }
div[data-baseweb="tab-highlight"] { background-color: var(--p-primary) !important; }
[data-testid="stProgress"] div[role="progressbar"] > div > div { background-color: var(--p-primary); }
[data-testid="stProgress"] div[role="progressbar"] > div { background-color: var(--p-primary-soft2); border-radius: 99px; }
[data-testid="stAlert"] { border-radius: 14px; border: 1px solid var(--p-border); }
[data-testid="stChatMessage"] { background: var(--p-card); border: 1px solid var(--p-border); border-radius: 16px; padding: .8rem 1rem; }
[data-testid="stDataFrame"] { border: 1px solid var(--p-border); border-radius: 14px; overflow: hidden; }
[data-testid="stCode"] { border-radius: 12px; }

/* answer options (every radio in the main area): selectable cards */
section.stMain [data-testid="stRadio"] [role="radiogroup"] { gap: .5rem; }
section.stMain [data-testid="stRadio"] [role="radiogroup"] > label { background: var(--p-card); border: 1px solid var(--p-border); border-radius: 14px; padding: .65rem .9rem; margin: 0; width: 100%; box-sizing: border-box; display: flex; align-items: center; gap: .6rem; transition: border-color .15s, background .15s; cursor: pointer; }
section.stMain [data-testid="stRadio"] [role="radiogroup"][aria-orientation="horizontal"] > label, section.stMain [data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(n+5)) > label { width: auto; }
section.stMain [data-testid="stRadio"] [role="radiogroup"] > label:hover { border-color: var(--p-primary); }
section.stMain [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { border-color: var(--p-primary); background: var(--p-primary-soft); }
section.stMain [data-testid="stRadio"] [role="radiogroup"] > label:has(input:focus-visible) { outline: 2px solid var(--p-primary); outline-offset: 2px; }

/* ---------- today's schedule: one list, a tab icon on every row, a Done button that turns green ---------- */
[class*="st-key-sch_ico_"] { display: flex; align-items: center; width: auto; height: auto; background: none !important; border: 0 !important; box-shadow: none !important; outline: 0 !important; color: var(--p-primary); }
[class*="st-key-sch_ico_"] *::before, [class*="st-key-sch_ico_"] *::after { content: none !important; display: none !important; }
[class*="st-key-sch_ico_"] * { border: 0 !important; text-decoration: none !important; box-shadow: none !important; background: none !important; }
[class*="st-key-sch_ico_"] p { margin: 0; line-height: 1; font-size: 1.3rem; }
.pp-sch { line-height: 1.3; } .pp-sch .t { font-weight: 700; } .pp-sch .d { color: var(--p-muted); font-size: .8rem; margin-top: .1rem; }
.pp-sch.done .t { color: var(--p-muted); text-decoration: none; }
[class*="st-key-sch_done_"] button, [class*="st-key-sch_donex_"] button { min-height: 2.1rem; padding: .15rem .9rem; font-weight: 700; border-radius: 10px; white-space: nowrap; }
[class*="st-key-sch_donex_"] button { background: var(--p-ok) !important; border-color: var(--p-ok) !important; color: #fff !important; }
[class*="st-key-sch_donex_"] button p, [class*="st-key-sch_donex_"] button [data-testid="stIconMaterial"] { color: #fff !important; }
[class*="st-key-sch_donex_"] button:hover { filter: brightness(1.08); }
.st-key-card_schedule hr { margin: .35rem 0; border-color: var(--p-border); }

/* ---------- study plan calendar ---------- */
.pp-cal { --n: 7; background: var(--p-card); border: 1px solid var(--p-border); border-radius: 18px; overflow: hidden; margin: .4rem 0 .9rem; }
.pp-cal .cal-scroll { overflow-x: auto; padding-bottom: 10px; }
.pp-cal .cal-head, .pp-cal .cal-body { min-width: calc(60px + var(--n) * 130px); }
.pp-cal .cal-head { display: grid; grid-template-columns: 60px repeat(var(--n), minmax(130px, 1fr)); border-bottom: 1px solid var(--p-border); }
.pp-cal .cal-dh { text-align: center; padding: .65rem 0; border-left: 1px solid var(--p-border); }
.pp-cal .cal-dh span { font-size: .7rem; letter-spacing: .12em; font-weight: 700; color: var(--p-muted); }
.pp-cal .cal-dh b { font-size: 1.05rem; margin-left: .35rem; padding: .1rem .45rem; border-radius: 99px; }
.pp-cal .cal-dh.today b { background: var(--p-primary); color: #fff; }
.pp-cal .cal-body { display: flex; position: relative; margin-top: 12px; }
.pp-cal .cal-hours { position: relative; width: 60px; flex: none; }
.pp-cal .cal-hr { position: absolute; right: 10px; transform: translateY(-50%); font-size: .7rem; font-weight: 600; color: var(--p-muted); }
.pp-cal .cal-grid { position: relative; flex: 1; display: grid; grid-template-columns: repeat(var(--n), minmax(130px, 1fr)); }
.pp-cal .cal-line { position: absolute; left: 0; right: 0; height: 0; border-top: 1px solid var(--p-border); }
.pp-cal .cal-col { position: relative; border-left: 1px solid var(--p-border); }
.pp-cal .cal-ev { position: absolute; left: 5px; right: 5px; box-sizing: border-box; border-radius: 10px; padding: .35rem .55rem; overflow: hidden; color: #1d2433; font-size: .72rem; line-height: 1.3; display: flex; flex-direction: column; gap: .05rem; }
.pp-cal .cal-ev b { font-size: .82rem; line-height: 1.25; padding-right: 3.4rem; }
.pp-cal .cal-ev span { font-weight: 600; opacity: .85; } .pp-cal .cal-ev small { opacity: .75; } .pp-cal .cal-ev .src { font-style: italic; }
.pp-cal .cal-ev em { position: absolute; top: .3rem; right: .4rem; font-style: normal; font-size: .62rem; font-weight: 700; background: rgba(0,0,0,.14); border-radius: 99px; padding: .08rem .45rem; }
.pp-cal .cal-ev.short { padding: .25rem .5rem; justify-content: center; } .pp-cal .cal-ev.short b { padding-right: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pp-cal .cal-ev.planned { border: 2px dashed rgba(29,36,51,.45); }
.pp-cal .k1, .cal-legend .k1 { background: #F2C94C; } .pp-cal .k2, .cal-legend .k2 { background: #6FE08A; } .pp-cal .k3, .cal-legend .k3 { background: #43D9B6; } .pp-cal .k4, .cal-legend .k4 { background: #D8B4F5; }
.pp-cal .cal-now { position: absolute; left: 0; right: 0; height: 0; border-top: 2px solid #E5383B; z-index: 2; }
.pp-cal .cal-now::before { content: ""; position: absolute; left: -5px; top: -6px; width: 9px; height: 9px; border-radius: 50%; background: #E5383B; }
.cal-legend { display: flex; flex-wrap: wrap; gap: .45rem; margin: .2rem 0 .3rem; }
.cal-legend span { font-size: .75rem; font-weight: 700; color: #1d2433; border-radius: 99px; padding: .15rem .7rem; }
.cal-legend .pl { background: transparent; color: var(--p-text); border: 2px dashed var(--p-muted); }

/* ---------- mistakes diary ---------- */
.pp-mistake { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; margin: .5rem 0 .6rem; }
.pp-mistake > div { border-radius: 12px; padding: .55rem .8rem; border: 1px solid var(--p-border); background: var(--p-card); font-weight: 600; overflow-wrap: anywhere; }
.pp-mistake small { display: block; font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; font-weight: 700; margin-bottom: .15rem; }
.pp-mistake .bad { border-color: var(--p-err); } .pp-mistake .bad small { color: var(--p-err); }
.pp-mistake .good { border-color: var(--p-ok); } .pp-mistake .good small { color: var(--p-ok); }
.st-key-diary_teaching { border-color: var(--p-primary) !important; background: var(--p-primary-soft); }
@media (max-width: 700px) { .pp-mistake { grid-template-columns: 1fr; } }

/* ---------- login ---------- */
/* The card is one container: its background is split in two halves (dark form side, burgundy brand side), so both halves always fill the full height whichever column is taller. */
.st-key-login_split { max-width: 1100px; margin: 1.2rem auto; border-radius: 28px; overflow: hidden; box-shadow: 0 24px 60px rgba(24,43,73,.28);
  background: linear-gradient(90deg, #17181C 0 50%, var(--p-primary) 50% 100%); padding: 0 !important; border: 0 !important; }
.st-key-login_split [data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: stretch; }
.st-key-login_split [data-testid="stColumn"] { padding: 0 !important; min-width: 0; }
.st-key-login_left { padding: 2.2rem 3rem 2.4rem; color: #F3F4F6; min-height: 640px; }
.st-key-login_left h1 { color: #fff; font-size: 2.1rem; font-weight: 800; margin: 2.2rem 0 .3rem; padding: 0; }
.st-key-login_left button p, .st-key-login_left button { color: inherit; } .st-key-login_left [data-testid="stForm"] button p { color: #fff !important; }
.st-key-login_left .lg-note, .st-key-login_left [data-testid="stCaptionContainer"], .st-key-login_left [data-testid="stCaptionContainer"] p { color: #A7ABB5 !important; font-size: .85rem; }
.st-key-login_left p.lg-note { margin: 0 0 1.4rem; }
.lg-brand { display: flex; align-items: center; gap: .6rem; font-weight: 800; font-size: 1.25rem; color: #fff; } .lg-brand img { height: 42px; width: auto; display: block; background: #fff; border-radius: 11px; padding: 5px 7px; box-sizing: border-box; } .lg-brand em { font-style: normal; color: #F4A3BA; }
.st-key-login_left label p, .st-key-login_left label { color: #A7ABB5 !important; font-size: .78rem; font-weight: 600; }
.st-key-login_left [data-baseweb="input"], .st-key-login_left [data-baseweb="select"] > div { background: transparent !important; border: 0 !important; border-bottom: 1px solid #50535C !important; border-radius: 0 !important; box-shadow: none !important; }
.st-key-login_left [data-baseweb="base-input"] { background: transparent !important; border: 0 !important; box-shadow: none !important; }
.st-key-login_left [data-baseweb="input"]:focus-within, .st-key-login_left [data-baseweb="select"] > div:focus-within { border-bottom-color: #F4A3BA !important; }
.st-key-login_left input, .st-key-login_left [data-baseweb="select"] div, .st-key-login_left [data-baseweb="select"] svg { color: #fff !important; -webkit-text-fill-color: #fff; }
.st-key-login_left input { padding-left: 0 !important; } .st-key-login_left input::placeholder { color: #7C808A !important; -webkit-text-fill-color: #7C808A; }
.st-key-login_left [data-testid="stForm"] { border: 0 !important; padding: 0 !important; background: transparent; }
.st-key-login_left [data-testid="stForm"] button[kind="primaryFormSubmit"], .st-key-login_left [data-testid="stForm"] button[kind="primary"], .st-key-login_left [data-testid="stBaseButton-primaryFormSubmit"] { background: var(--p-primary) !important; color: #fff !important; border: 0 !important; border-radius: 10px; min-height: 2.7rem; font-weight: 700; margin-top: .6rem; }
.st-key-login_left [data-testid="stForm"] button:hover { filter: brightness(1.15); }
[class*="st-key-login_to_"] button { background: #2B2D33 !important; border: 0 !important; border-radius: 10px; } [class*="st-key-login_to_"] button p { color: #fff !important; }
.st-key-login_to_tutor button { background: transparent !important; padding-left: 0; text-decoration: underline; } .st-key-login_to_tutor button p { color: #A7ABB5 !important; }
.st-key-login_left [data-testid="stAlert"] { border-radius: 10px; }
/* brand side */
.lg-hero { color: #fff; padding: 2.6rem 2.6rem 2rem; position: relative; overflow: hidden; min-height: 640px; box-sizing: border-box; }
.lg-hero::before { content: ""; position: absolute; width: 380px; height: 380px; border-radius: 50%; background: rgba(255,255,255,.08); right: -120px; top: -140px; }
.lg-hero::after { content: ""; position: absolute; width: 300px; height: 300px; border-radius: 45% 55% 60% 40%; background: rgba(255,255,255,.06); left: -110px; bottom: 90px; }
.lg-hero > * { position: relative; z-index: 1; }
.lg-hero .lg-mark { height: 46px; width: auto; filter: brightness(0) invert(1); display: block; margin-bottom: 1.1rem; }
.lg-hero h2 { color: #fff; margin: 0; padding: 0; font-size: 2.9rem; line-height: 1.05; letter-spacing: -.02em; display: flex; flex-direction: column; }
.lg-hero h2 b { font-weight: 800; } .lg-hero h2 span { font-weight: 300; }
.lg-hero p.lg-tag { color: #fff !important; font-weight: 700; margin: .7rem 0 .1rem; font-size: 1rem; } .lg-hero p.lg-sub { color: rgba(255,255,255,.85) !important; margin: 0; font-size: .9rem; }
.lg-hero .lg-art { width: 100%; max-width: 440px; height: auto; display: block; margin: 1.2rem auto .6rem; }
.lg-hero .lg-feats { list-style: none; margin: .4rem 0 0; padding: 0; display: grid; gap: .35rem; font-size: .85rem; } .lg-hero .lg-feats li { color: rgba(255,255,255,.92) !important; }
.lg-hero .lg-feats li::before { content: "✓"; display: inline-grid; place-items: center; width: 1.15rem; height: 1.15rem; margin-right: .5rem; border-radius: 50%; background: rgba(255,255,255,.2); font-size: .7rem; }
@media (max-width: 900px) {
  .st-key-login_split { background: #17181C; border-radius: 20px; margin: .4rem auto; }
  .st-key-login_split [data-testid="stColumn"]:last-child { display: none !important; }
  .st-key-login_split [data-testid="stColumn"]:first-child { flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important; }
  .st-key-login_left { padding: 1.4rem 1.2rem 1.8rem; min-height: 0; }
}

/* ---------- small screens ---------- */
@media (max-width: 900px) {
  .block-container { padding: .6rem .9rem 4rem; }
  .pp-greet h1 { font-size: 1.45rem; } h1 { font-size: 1.5rem; }
  .pp-topbar { padding: .5rem .7rem; } .pp-chip.hide-sm, .pp-user span:last-child small { display: none; }
  .pp-subjects { justify-content: center; gap: .8rem; }
  .pp-vs { grid-template-columns: 1fr 1fr; } .pp-vs .m { grid-column: 1 / -1; grid-row: 2; max-width: none; }
  .pp-done { position: static; display: inline-block; margin-bottom: .4rem; }
  [data-testid="stDataFrame"], [data-testid="stTable"] { overflow-x: auto; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""
