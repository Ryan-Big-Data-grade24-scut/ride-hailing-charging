"""Build the English defence deck.

The guide (section 7) asks for slides in English, organised around the
research logic rather than around paragraphs copied from the paper, and
recommends a nine-part structure:

    1 Title & Team          6 Baseline & Comparison
    2 Background & RQ       7 Sensitivity / Extension
    3 Optimization Problem   8 Key Insight
    4 Data & Assumptions     9 Conclusion
    5 Method / Solution

The deck follows that structure, with backup slides at the end for the
questions the guide lists. Nothing here needs Python at defence time --
the file is the deliverable.

    python tools/make_ppt.py
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
FIGS = os.path.join(ROOT, "figures")
OUT = os.path.join(ROOT, "submit", "Defense_梁睿希_202464870791.pptx")

# ---------------------------------------------------------------- palette
INK = RGBColor(0x1C, 0x23, 0x33)      # body text / headings
ACC = RGBColor(0xC2, 0x41, 0x0C)      # charging, the thing we care about
BLU = RGBColor(0x1D, 0x4E, 0xD8)      # demand
GRN = RGBColor(0x04, 0x78, 0x57)      # optimal
GRY = RGBColor(0x94, 0xA3, 0xB8)      # tariff / secondary
LGT = RGBColor(0xF1, 0xF5, 0xF9)      # panel fill
WHT = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Times New Roman"

SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------- helpers
def tb(slide, left, top, width, height, wrap=True):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    return tf


def put(tf, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT,
        italic=False, space_after=6, first=False, line=1.15, font=FONT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.line_spacing = line
    run = p.add_run()
    run.text = text
    f = run.font
    f.name, f.size, f.bold, f.italic = font, Pt(size), bold, italic
    f.color.rgb = color
    return p


def rect(slide, left, top, width, height, fill=LGT, line=None):
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh


def slide_base(title, kicker=None, number=None):
    """A content slide: a thin accent bar, the title, an optional kicker
    line that states the message of the slide, and a footer."""
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, SW, Inches(0.06), fill=ACC)
    tf = tb(s, Inches(0.62), Inches(0.30), Inches(11.6), Inches(0.62))
    put(tf, title, size=30, bold=True, first=True, space_after=0)
    if kicker:
        tf2 = tb(s, Inches(0.62), Inches(0.95), Inches(12.1), Inches(0.45))
        put(tf2, kicker, size=15, color=RGBColor(0x47, 0x55, 0x69),
            italic=True, first=True, space_after=0)
    # footer
    ft = tb(s, Inches(0.62), Inches(7.02), Inches(12.1), Inches(0.3))
    put(ft, "When Should an Electric Ride-Hailing Driver Charge?   |   "
            "Optimization Methods (084100551)", size=10, color=GRY, first=True,
        space_after=0)
    if number is not None:
        nt = tb(s, Inches(12.2), Inches(7.02), Inches(0.55), Inches(0.3))
        put(nt, str(number), size=11, color=GRY, align=PP_ALIGN.RIGHT,
            first=True, space_after=0)
    return s


def bullets(slide, items, left, top, width, height, size=18, gap=9,
            bullet_color=ACC):
    """items: list of str, or (text, level) or (text, level, colour, bold)."""
    tf = tb(slide, left, top, width, height)
    first = True
    for it in items:
        lvl, col, bold = 0, INK, False
        if isinstance(it, tuple):
            if len(it) == 2:
                text, lvl = it
            elif len(it) == 3:
                text, lvl, col = it
            else:
                text, lvl, col, bold = it
        else:
            text = it
        mark = "▪  " if lvl == 0 else "–  "
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.line_spacing = 1.18
        r = p.add_run()
        r.text = mark
        r.font.name, r.font.size, r.font.bold = FONT, Pt(size - (2 if lvl else 4)), True
        r.font.color.rgb = bullet_color if lvl == 0 else GRY
        r2 = p.add_run()
        r2.text = text
        r2.font.name, r2.font.size, r2.font.bold = FONT, Pt(size - 2 * lvl), bold
        r2.font.color.rgb = col
        if lvl:
            p.level = lvl
    return tf


def picture(slide, name, left, top, width=None, height=None):
    path = os.path.join(FIGS, name)
    kw = {}
    if width:
        kw["width"] = width
    if height:
        kw["height"] = height
    return slide.shapes.add_picture(path, left, top, **kw)


def fit_image(slide, name, left, top, max_w, max_h):
    """Place a figure scaled to fit inside (max_w, max_h), keeping its aspect.

    Returns the picture shape, so the caller can put the caption exactly
    under it instead of guessing.
    """
    from PIL import Image
    path = os.path.join(FIGS, name)
    with Image.open(path) as im:
        pw, ph = im.size
    scale = min(max_w / pw, max_h / ph)
    w, h = int(pw * scale), int(ph * scale)
    return slide.shapes.add_picture(path, left, top, width=w, height=h)


def fig_with_caption(slide, name, left, top, max_w, max_h, text,
                     cap_size=11):
    """Fit a figure into the box and hang its caption directly beneath it."""
    pic = fit_image(slide, name, left, top, max_w, max_h)
    bottom = top + pic.height + Inches(0.04)
    tf = tb(slide, left, bottom, pic.width, Inches(0.55))
    put(tf, text, size=cap_size, color=RGBColor(0x47, 0x55, 0x69),
        align=PP_ALIGN.CENTER, first=True, space_after=0, line=1.05)
    return pic


def caption(slide, text, left, top, width, size=11):
    tf = tb(slide, left, top, width, Inches(0.3))
    put(tf, text, size=size, color=RGBColor(0x47, 0x55, 0x69),
        align=PP_ALIGN.CENTER, first=True, space_after=0)


def table(slide, rows, left, top, width, height, size=13,
          head_fill=RGBColor(0xE2, 0xE8, 0xF0), col_w=None, align_first_left=True):
    """rows[0] is the header. col_w: list of relative widths."""
    nr, nc = len(rows), len(rows[0])
    shape = slide.shapes.add_table(nr, nc, left, top, width, height)
    t = shape.table
    if col_w:
        total = sum(col_w)
        for j, cwr in enumerate(col_w):
            t.columns[j].width = Emu(int(width * cwr / total))
    for i, row in enumerate(rows):
        t.rows[i].height = Emu(int(height / nr))
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = head_fill if i == 0 else WHT
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = (PP_ALIGN.LEFT if (j == 0 and align_first_left)
                           else PP_ALIGN.CENTER)
            r = p.add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = (i == 0)
            r.font.color.rgb = INK if i == 0 else RGBColor(0x33, 0x3D, 0x4C)
    return t


# ================================================================ 1. TITLE
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, Inches(0.10), fill=ACC)
tf = tb(s, Inches(1.0), Inches(1.55), Inches(11.3), Inches(1.5))
put(tf, "When Should an Electric Ride-Hailing Driver Charge?",
    size=40, bold=True, align=PP_ALIGN.CENTER, first=True, space_after=6)
put(tf, "Joint intra-day optimisation of charging time and order acceptance",
    size=20, color=RGBColor(0x47, 0x55, 0x69), align=PP_ALIGN.CENTER,
    italic=True)

rect(s, Inches(3.1), Inches(3.25), Inches(7.1), Inches(0.02), fill=GRY)

tf = tb(s, Inches(1.0), Inches(3.55), Inches(11.3), Inches(2.2))
put(tf, "Ruixi Liang (梁睿希)   ·   Student ID 202464870791",
    size=19, align=PP_ALIGN.CENTER, first=True, space_after=4)
put(tf, "Big Data Class 1   ·   School of Future Technology",
    size=15, color=RGBColor(0x47, 0x55, 0x69), align=PP_ALIGN.CENTER,
    space_after=14)
put(tf, "[Team member 2 — Name, Student ID, Major and Class]",
    size=15, color=GRY, align=PP_ALIGN.CENTER, space_after=14)
put(tf, "[Team member 3 — Name, Student ID, Major and Class]",
    size=15, color=GRY, align=PP_ALIGN.CENTER, space_after=16)
put(tf, "Course: Optimization Methods (084100551)   ·   Supervisor: Prof. Zhenhong Lin",
    size=15, color=RGBColor(0x47, 0x55, 0x69), align=PP_ALIGN.CENTER)

tf = tb(s, Inches(1.0), Inches(6.35), Inches(11.3), Inches(0.6))
put(tf, "In one sentence:  we model a single electric ride-hailing driver's "
        "charging and order decisions as a Markov decision process and show "
        "that the cheapest electricity hour is almost never the right hour "
        "to charge.",
    size=15, color=ACC, align=PP_ALIGN.CENTER, italic=True, first=True)


# ================================================== 2. BACKGROUND (problem)
s = slide_base(
    "Background: the driver is paid to drive, and billed for the plug",
    "Electric ride-hailing drivers face a time-of-use electricity tariff "
    "and an order flow that both vary over the day — but they do not vary "
    "together.", number=2)
bullets(s, [
    "A driver earns from serving orders; electricity is a pure cost with a "
    "time-of-use (TOU) tariff that is ~3.8× cheaper at night than at the "
    "16:00–19:00 super-peak.",
    "Charging takes a 15-minute slot, and the driver keeps earning while "
    "the car charges — but only if orders are still arriving.",
    ("Opportunity cost, not the tariff, decides the answer: a slot that "
     "saves $0.31/kWh but sits in a dead hour is a bad slot.", 1),
    "Naive rule (“charge in the cheapest hour”) ignores this entirely, "
    "and it is exactly what real drivers and naive dispatchers propose.",
], Inches(0.62), Inches(1.55), Inches(5.3), Inches(4.6), size=17)

fig_with_caption(s, "F1_day_in_picture.png", Inches(6.15), Inches(1.50),
                 Inches(6.6), Inches(4.55),
                 "One simulated day: demand (blue), tariff (grey), and the "
                 "MDP charging policy (orange dots) on the state-of-charge "
                 "curve.")


# ============================================ 3. RESEARCH QUESTION
s = slide_base(
    "Research question and contributions",
    "A deliberately small, sharply-posed question — a single driver, "
    "one day, one battery.", number=3)

rect(s, Inches(0.62), Inches(1.55), Inches(12.1), Inches(1.05), fill=LGT)
rect(s, Inches(0.62), Inches(1.55), Inches(0.07), Inches(1.05), fill=ACC)
tf = tb(s, Inches(0.95), Inches(1.72), Inches(11.5), Inches(0.8))
put(tf, "RQ.  When should an electric ride-hailing driver charge, and how "
        "much do we lose by charging in the cheapest hour instead of the "
        "optimal one?",
    size=20, bold=True, first=True, space_after=0)

bullets(s, [
    ("Contributions", 0, ACC, True),
    "A joint MDP of order acceptance and charging for a single driver: "
    "8,256 states, 96 slots, Poisson arrivals summed analytically.",
    "A decomposition that shows exactly why the optimal policy departs "
    "from the tariff-following rule — the opportunity cost of an idle hour.",
    "A closed-form extension to the multi-day cycle, giving the shadow "
    "price of stored energy (μ = $0.2414/kWh).",
    "Full reproducibility: public data, published seeds, and every number "
    "in the paper regenerated by one script.",
    "A boundary condition: optimisation earns 6% when the battery binds and "
    "0.4% when it does not — the hardware decides, not the algorithm.",
], Inches(0.62), Inches(2.95), Inches(12.1), Inches(3.6), size=18)


# ============================================ 4. OPTIMIZATION PROBLEM
s = slide_base(
    "The optimization problem",
    "Decision variables, one objective, three constraints — and the "
    "trade-off that makes it worth optimising.", number=4)

tf = tb(s, Inches(0.62), Inches(1.55), Inches(6.0), Inches(0.3))
put(tf, "Decision variables", size=15, bold=True, color=ACC, first=True)
bullets(s, [
    "a(t) ∈ {0, 1}: charge or not in slot t",
    "u(t) ≥ 0: number of orders accepted in slot t",
    "s(t): state of charge at the start of slot t",
    "π: the policy mapping (t, s) → (a, u)",
], Inches(0.62), Inches(1.90), Inches(6.0), Inches(1.8), size=16)

tf = tb(s, Inches(0.62), Inches(3.72), Inches(6.0), Inches(0.3))
put(tf, "Constraints", size=15, bold=True, color=ACC, first=True)
bullets(s, [
    "SOC reserve floor: s(t) ≥ 15% at all times",
    "Energy balance: s(t+1) = s(t) + η·a(t)·P·τ(s)·Δt − d(t)·u(t)",
    "Capacity and slot limits: s(t) ≤ 100%, one slot per driver",
], Inches(0.62), Inches(4.07), Inches(6.0), Inches(1.6), size=16)

rect(s, Inches(7.0), Inches(1.55), Inches(5.7), Inches(1.95), fill=LGT)
tf = tb(s, Inches(7.25), Inches(1.72), Inches(5.2), Inches(0.35))
put(tf, "Objective (max)", size=15, bold=True, color=ACC, first=True)
tf = tb(s, Inches(7.25), Inches(2.10), Inches(5.2), Inches(1.3))
put(tf, "max  E [ Σₜ ( fare(t)·u(t)  −  price(t)·P·a(t)·Δt ) ]",
    size=16, bold=True, first=True, space_after=8)
put(tf, "earnings from accepted orders, minus the electricity bill",
    size=13, color=RGBColor(0x47, 0x55, 0x69), italic=True)

rect(s, Inches(7.0), Inches(3.72), Inches(5.7), Inches(2.35), fill=WHT,
     line=ACC)
tf = tb(s, Inches(7.25), Inches(3.90), Inches(5.2), Inches(2.0))
put(tf, "The key trade-off", size=15, bold=True, color=ACC, first=True,
    space_after=8)
put(tf, "Every slot spent charging is a slot not spent earning — but the "
        "value of that slot depends on the demand profile, not on the "
        "tariff.", size=16, space_after=8)
put(tf, "Cheap electricity + no orders = a loss.  Expensive electricity + "
        "peak orders = a smaller loss.",
    size=16, bold=True, color=ACC, space_after=0)


# ============================================ 5. DATA & ASSUMPTIONS
s = slide_base(
    "Data and assumptions",
    "One public dataset for demand; the tariff and vehicle parameters are "
    "stated assumptions, not measurements — and we say so explicitly.",
    number=5)

table(s, [
    ["Parameter", "Value", "Source / note"],
    ["Order arrival rate λ(t)", "91 → 1,684 orders/h", "NYC TLC trip records, 2024-01"],
    ["Fare rate", "$53.0/h mean, $93.5/h peak", "derived from trip fare ÷ trip duration"],
    ["Battery / charger", "40 kWh, 60 kW, η = 92%", "typical BEV ride-hailing vehicle"],
    ["Reserve floor / knee", "15% SOC / 80% SOC", "CC–CV taper above the knee"],
    ["TOU tariff", "$0.11 – $0.42 / kWh", "assumption; 4 tiers, 44 valley slots"],
    ["Horizon / step", "96 slots × 15 min = 24 h", "a full operating day"],
], Inches(0.62), Inches(1.62), Inches(7.5), Inches(3.5), size=13,
    col_w=[3.0, 2.6, 3.4])

fig_with_caption(s, "F4_taper.png", Inches(8.35), Inches(1.55),
                 Inches(4.4), Inches(2.0),
                 "CC–CV taper and the resulting cost per kWh stored.")

bullets(s, [
    ("What is measured and what is assumed is the honesty line of this "
     "paper: the demand profile is measured, the tariff is an assumption, "
     "and the sensitivity analysis in Section 7 varies the assumption.", 0),
], Inches(0.62), Inches(5.40), Inches(12.1), Inches(1.0), size=17)


# ============================================ 6. METHOD
s = slide_base(
    "Method: three models, each answering one question",
    "Each step is justified by what the previous one could not resolve.",
    number=6)

rows = [
    ["Model", "Question it answers", "Why this method"],
    ["DP\nexpected value", "What is the best schedule if the future is known in advance?",
     "A lower bound and a sanity check; deterministic and easy to verify by hand"],
    ["MDP\nPoisson arrivals", "What should the driver do given only the current state?",
     "Orders arrive stochastically; the Bellman recursion sums over the Poisson arrivals in closed form"],
    ["Cyclic multi-day MDP", "What is worth carrying into tomorrow?",
     "The terminal value is the value of starting tomorrow, so it is a fixed point, solved by value iteration"],
]
table(s, rows, Inches(0.62), Inches(1.60), Inches(12.1), Inches(2.5), size=13,
      col_w=[2.2, 4.6, 5.6])

bullets(s, [
    ("Why not MILP?", 0, ACC, True),
    "A MILP is possible, but the stochastic arrival process makes the "
    "objective non-linear in the decision variables, and we would have to "
    "sample scenarios — trading a 20-minute solve for 50 approximation "
    "error.",
    "The MDP is exact and its structure is interpretable: the policy can be "
    "read off slot by slot, which is what makes the key insight visible "
    "at all.",
    ("No code on the slides: the Bellman recursion is the whole method — "
     "V(t, s) = max over actions of [ immediate reward + expected "
     "continuation ].", 1),
], Inches(0.62), Inches(4.20), Inches(12.1), Inches(2.6), size=16)


# ============================================ 7. BASELINE & COMPARISON
s = slide_base(
    "Baseline and comparison: what does optimisation buy?",
    "Eight policies, 600 simulated days (570 of them feasible), the same "
    "demand realisation for every policy.", number=7)

fig_with_caption(s, "F2_policy_comparison.png", Inches(0.62), Inches(1.55),
                 Inches(7.5), Inches(2.6),
                 "Net daily earnings and feasibility rate of the eight "
                 "policies.")

table(s, [
    ["Policy", "Net ($/day)", "Feasible"],
    ["MDP (ours)", "$946.46", "95%"],
    ["DP (capacity-aware)", "$936.08", "78%"],
    ["DP (mean demand)", "$934.15", "85%"],
    ["Charge-to-full rule", "$911.06", "82%"],
    ["Cheapest-hour rule", "$788.21", "11%"],
    ["Never charge", "$600.09", "0%"],
], Inches(8.45), Inches(1.60), Inches(4.3), Inches(3.1), size=13,
    col_w=[2.6, 1.6, 1.3])

bullets(s, [
    ("+$158.25/day (+20.1%) over the cheapest-hour rule", 0, ACC, True),
    ("+$21.47/day (+2.3%) over a perfect-forecast deterministic DP", 0,
     GRN, True),
    "Feasibility is a first-class metric: a policy that strands the driver "
    "at 0% SOC is worthless even at a high average.",
    ("Book value is not executability", 0, ACC, True),
    "The deterministic plan books $1,242.61 against the MDP's $939.55 — a "
    "$303 gap. But 95% of that gap ($303 → $14) is a Jensen artefact of "
    "truncating service at capacity, not the price of uncertainty.",
    "Even the capacity-aware plan ($953.68 book) fails on 21.7% of days, "
    "because it leaves no margin; the MDP, which plans for the realisation "
    "rather than its mean, completes 95.0%.",
], Inches(0.62), Inches(4.95), Inches(12.1), Inches(2.4), size=15, gap=6)


# ============================================ 8. SENSITIVITY / EXTENSION
s = slide_base(
    "Sensitivity and extension",
    "Does the conclusion survive when the assumptions move?", number=8)

fig_with_caption(s, "F3_sensitivity.png", Inches(0.62), Inches(1.50),
                 Inches(8.0), Inches(4.30),
                 "Gain of the optimal policy over the tariff-following rule, "
                 "10 one-factor sweeps.")

bullets(s, [
    ("10 sweeps: TOU spread, battery size, consumption, charger power, "
     "peak utilisation, fare level, start-of-day SOC, charging efficiency, "
     "reserve floor, billing mode", 0),
    "The gain is positive everywhere and grows as the energy budget "
    "tightens — optimisation matters more when energy is scarcer.",
    ("Ablations A1–A7 isolate every mechanism", 0, ACC, True),
    "Removing the opportunity-cost term from the reward is the only "
    "ablation that changes the policy qualitatively — and it turns the MDP "
    "back into the cheapest-hour rule.",
    ("Multi-day cycle", 0, ACC, True),
    "Cyclic MDP: μ = $0.2414/kWh shadow price, optimal start-of-day SOC "
    "36.8%, steady-state charging at 04:45 and 12:00.",
    ("Excursion model (next slide)", 0, ACC, True),
    "Charging as drive + queue + charge + return: the gain over the best "
    "rule rises from 2.3% to 6.0%.",
], Inches(8.75), Inches(1.50), Inches(4.0), Inches(5.45), size=13, gap=5)



# ============================================ 9. EXCURSION EXTENSION
s = slide_base(
    "Extension: charging is an excursion, and the queue is not free",
    "The real cost of charging is the trip — drive to the station, wait, "
    "plug in, drive back.", number=9)

fig_with_caption(s, "F5_queue_cost.png", Inches(0.62), Inches(1.50),
                 Inches(7.9), Inches(4.30),
                 "Net earnings against the peak queue length, for the 40 kWh "
                 "car (left), the 57.6 kWh car (centre), and the mechanism — "
                 "slots spent off the road (right).")

bullets(s, [
    ("Charging = drive + queue + charge + return", 0, ACC, True),
    "The state space does not grow: the queue is exogenous, so it needs "
    "no state of its own (still 8,256 states).",
    "The opportunity cost is no longer a term in the objective — it "
    "emerges: no fare can be collected while the driver is away.",
    ("What the queue costs", 0, ACC, True),
    "40 kWh car: a 2-hour queue costs $24–$79/day and drops feasibility "
    "from 87.6% to 61.9%.",
    "57.6 kWh car: the same queue costs $0–$0.58 under a demand-matched "
    "queue and $18 under a uniform one — a bigger pack lets the driver "
    "leave early and dodge it.",
    ("Larger than the whole optimisation gain", 0, ACC, True),
    "Optimisation is worth $21.47/day in the simple model; the queue is "
    "worth up to $79.",
    ("And when is optimisation worth it at all?", 0, ACC, True),
    "Only when the battery binds: if usable energy is below 1.1x the day's "
    "need, the gain is under 1%; above it, 6%.",
], Inches(8.75), Inches(1.45), Inches(4.05), Inches(5.3), size=12, gap=4)


# ============================================ 10. KEY INSIGHT
s = slide_base(
    "Key insight: the cheapest hour is the wrong hour",
    "This is the one figure we would keep if we could only keep one.",
    number=10)

rect(s, Inches(0.62), Inches(1.60), Inches(12.1), Inches(1.35), fill=LGT)
rect(s, Inches(0.62), Inches(1.60), Inches(0.07), Inches(1.35), fill=ACC)
tf = tb(s, Inches(0.95), Inches(1.78), Inches(11.5), Inches(1.1))
put(tf, "The tariff spread is $0.31/kWh, but the demand spread over the "
        "same 24 hours is 18.5×. Opportunity cost dominates, so the "
        "optimal policy buys cheap energy in slots where it is cheap — "
        "and charges where the demand gap is small.",
    size=19, first=True, space_after=0)

bullets(s, [
    ("Measured on the optimal policy:", 0, ACC, True),
    "74.4% of feasible days contain at least one off-valley charge; "
    "25.6% are valley-only.",
    "100% of days charge in the deep night (00:00–05:00).",
    "Modal slot: 04:45 (87.2% of days); then 20:30 (9.5%), 12:30 (9.0%).",
    ("Why 20:30 and 12:30 appear:", 0, ACC, True),
    "They are shoulder-tier (2× cheaper than peak) AND still inside the "
    "demand shoulder — the only slots that satisfy both conditions.",
    ("The general lesson:", 0, ACC, True),
    "Price a time slot by its opportunity cost, not by its sticker price.",
], Inches(0.62), Inches(3.02), Inches(6.9), Inches(3.7), size=14, gap=7)

fig_with_caption(s, "F1_day_in_picture.png", Inches(7.85), Inches(3.05),
                 Inches(4.85), Inches(3.15),
                 "The optimal day: charge at the shoulder boundary, not at "
                 "the tariff minimum.")


# ============================================ 10. CONCLUSION
s = slide_base(
    "Conclusion",
    "Direct answer to the research question, with the conditions attached.",
    number=11)

bullets(s, [
    ("Finding 1.", 0, ACC, True),
    "Charging at the tariff minimum is the worst reasonable rule: "
    "$788.21/day and 11% feasibility, against $946.46/day and 95% for the "
    "optimal policy.",
    ("Finding 2.", 0, ACC, True),
    "The optimal policy is strongly valley-anchored (74.4% of days charge "
    "off-valley) but not valley-exclusive: 25.6% stay entirely in the valley.",
    ("Finding 3.", 0, ACC, True),
    "The decision is driven by demand availability, not by price: 18.5× "
    "demand spread vs a 3.8× tariff spread, so the opportunity cost of an "
    "idle slot sets the optimum.",
    ("Finding 4.", 0, ACC, True),
    "Across a multi-day cycle, stored energy is worth μ = $0.2414/kWh and "
    "the optimal start-of-day SOC is 36.8%.",
    ("Finding 5 (corrected).", 0, ACC, True),
    "Book value is not executability: the $303 gap between a deterministic "
    "plan's book value and the MDP's is 95% a Jensen artefact of capacity "
    "truncation, not the price of uncertainty.",
    ("Finding 6.", 0, ACC, True),
    "Charging is a trip, not a slot. With the queue in the model the gain "
    "over the best rule rises from 2.3% to 6.0%, and a 2-hour queue is "
    "worth $24–$79/day — more than the whole optimisation gain.",
    ("Finding 7.", 0, ACC, True),
    "Optimising is worth it only when the battery binds: the gain is under "
    "1% while usable energy is below 1.1x the day's consumption, and 6% "
    "above it. The hardware decides, not the algorithm.",
], Inches(0.62), Inches(1.42), Inches(12.1), Inches(4.5), size=12, gap=2)

rect(s, Inches(0.62), Inches(5.95), Inches(12.1), Inches(0.95), fill=LGT)
tf = tb(s, Inches(0.90), Inches(6.07), Inches(11.6), Inches(0.8))
put(tf, "Limitations and next steps", size=13, bold=True, color=ACC,
    first=True, space_after=3)
put(tf, "Single driver (the fleet-scale version needs a different "
        "treatment); the tariff is an assumption, not a measured price; the "
        "charger queue is exogenous, so a driver's own decision cannot "
        "lengthen the queue he faces. Next: an endogenous queue, a finer "
        "charging sub-grid, and multi-agent congestion.",
    size=13, color=RGBColor(0x33, 0x3D, 0x4C))


# ============================================ 11. BACKUP
s = slide_base(
    "Backup: verification and reproducibility",
    "Because every number in the paper is regenerated by one script.",
    number=12)

table(s, [
    ["Check", "Result"],
    ["Planner vs simulator consistency", "2.25 standard errors (consistent rule); 2.31 SE (legacy rule)"],
    ["Bellman residual (cyclic MDP)", "9.29 × 10⁻¹⁰ after 34 sweeps"],
    ["Bellman residual (excursion MDP)", "7.01 × 10⁻¹⁰ after 36 sweeps"],
    ["Formula validation", "143 LaTeX formulas checked with KaTeX, 0 failures"],
    ["Paper equations in Word", "114 native OMML equation objects, 0 pasted images"],
    ["Data", "2,803,713 cleaned trips; 2,739,936 in-profile over 30 full days"],
    ["Reproduction", "code/ + data/ + published seeds; one command regenerates all figures and tables"],
], Inches(0.62), Inches(1.60), Inches(12.1), Inches(3.4), size=14,
    col_w=[4.0, 8.1])

bullets(s, [
    ("AI use statement (also in the paper):", 0, ACC, True),
    "Generative AI was used for literature understanding, model discussion, "
    "code debugging and English-language editing. All results, equations "
    "and code logic were verified by the team; the authors take full "
    "responsibility for the submitted content.",
], Inches(0.62), Inches(5.25), Inches(12.1), Inches(1.4), size=16)


s = slide_base(
    "Backup: expected questions",
    "The guide lists eight questions we should be ready for; three of them "
    "have non-trivial answers.", number=13)

table(s, [
    ["Question", "Short answer"],
    ["Why is this an optimization problem?",
     "Two coupled decisions (when to charge, which orders to take) compete for the same scarce resource: the driver's time and battery."],
    ["Why is this constraint necessary?",
     "Without the 15% reserve floor the DP would plan runs that strand the driver at 0% SOC; we proved the constraint is non-redundant and measured the resulting infeasibility."],
    ["Why this method?",
     "The arrivals are stochastic and the state is (time, SOC) — exactly the structure of an MDP with a closed-form Poisson expectation."],
    ["Why does the optimal solution have this shape?",
     "Because the value of a slot is the demand it forgoes; when demand is flat, the tariff decides, and when demand is steep, the tariff cannot outvote it."],
    ["What if a key parameter changes?",
     "10 sensitivity sweeps: the gain over the tariff-following rule stays positive and grows as the energy budget tightens — under 1% while the battery does not bind, 6% once it does."],
    ["What if the charger is busy?",
     "We model the queue as exogenous and sweep four shapes × five levels: a 2-hour queue costs $24–$79/day on the 40 kWh car and about $0 on the 57.6 kWh car, which can simply leave early. An endogenous queue — drivers competing for the same charger — is the next step."],
    ["Would the conclusion hold under different assumptions?",
     "Yes for the tariff shape and fare level (re-calibrated VOT still gives 16 of 96 slots below $15.20/h) — but a flat tariff would collapse the problem to a pure energy-balance question."],
], Inches(0.62), Inches(1.60), Inches(12.1), Inches(4.9), size=12,
    col_w=[3.4, 8.7])


# ---------------------------------------------------------------- save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs.save(OUT)
print("wrote", OUT, "-", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
