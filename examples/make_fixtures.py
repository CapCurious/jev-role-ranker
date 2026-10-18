"""Generate synthetic job postings and gold labels for jev-role-ranker.

Every label is true by construction: the template decides which sentences go into a
posting, and the labels are read back from those decisions. No model writes or checks
them. Run `python3 examples/make_fixtures.py` to rewrite examples/postings/ and
examples/gold.jsonl; the output is identical on every run (seeded).

Gold fields per posting:
  no_sponsorship  True when the posting carries a refusal-to-sponsor sentence
  seniority       early | mid | lead, from the years-of-experience sentence
  remote          remote | hybrid | onsite, from the location sentence
  fit             1 to 5, the number of profile signals present (clamped to 1..5):
                  product role, technical work, MBA welcome, early career, US location
  gold_score      0.5 * (fit-1)/4 + 0.3 * (1 - no_sponsorship) + 0.1 * seniority_w + 0.1 * remote_w
  gold_rank       1 = best; ties broken by posting id so the rank is a strict order

The weights match the shipped defaults in jev_role_ranker.py.
"""
import json
import os
import random
import sys

SEED = 20261018
N_POSTINGS = 80

WEIGHTS = {"fit": 0.5, "sponsorship": 0.3, "seniority": 0.1, "remote": 0.1}
SENIORITY_W = {"early": 1.0, "mid": 0.6, "lead": 0.2}
REMOTE_W = {"remote": 1.0, "hybrid": 0.7, "onsite": 0.4}

COMPANIES = [
    ("Northwind Robotics", "robotics"), ("Copperline Automation", "robotics"),
    ("Tessel Machines", "robotics"), ("Ironleaf Robotics", "robotics"),
    ("Vesperlight Health", "health"), ("Wrenfield Care", "health"),
    ("Pinecrest Diagnostics", "health"), ("Marlow Therapeutics", "health"),
    ("Keelhaven Freightworks", "logistics"), ("Redwood Freight", "logistics"),
    ("Stonebridge Shipping", "logistics"), ("Anchorpoint Supply", "logistics"),
    ("Quillfeather Software", "software"), ("Brightmoor Cloud", "software"),
    ("Fernhill Data", "software"), ("Orchard Analytics", "software"),
    ("Solstice Grid", "energy"), ("Cragmoor Energy", "energy"),
    ("Aspenfield Power", "energy"), ("Maplegate Markets", "retail"),
    ("Bluejay Commerce", "retail"), ("Hollowell Goods", "retail"),
    ("Larkspur Academy", "education"), ("Pennywhistle Schools", "education"),
    ("Thistledown Payments", "finance"), ("Oakhaven Lending", "finance"),
]

INTRO = {
    "robotics": [
        "{co} builds robots that move boxes, scan shelves and inspect equipment in busy facilities.",
        "{co} designs warehouse automation used by mid-sized operators across the country.",
        "At {co}, small teams ship hardware and software together on a weekly rhythm.",
    ],
    "health": [
        "{co} helps clinics schedule care, manage records and reduce paperwork for staff.",
        "{co} makes tools that connect patients with the right clinician faster.",
        "At {co}, we are a care-focused company with a growing product group.",
    ],
    "logistics": [
        "{co} moves freight for regional retailers and tracks every shipment end to end.",
        "{co} runs a network of depots and software that plans the routes between them.",
        "At {co}, thousands of deliveries a day depend on the systems this team owns.",
    ],
    "software": [
        "{co} sells workflow software to teams that outgrew their spreadsheets.",
        "{co} offers a data platform that small companies use to understand their customers.",
        "At {co}, we ship to customers every week and talk to them even more often.",
    ],
    "energy": [
        "{co} helps utilities forecast demand and balance supply from many small sources.",
        "{co} installs and monitors storage systems for commercial buildings.",
        "At {co}, the work is practical and the customers are cities, schools and factories.",
    ],
    "retail": [
        "{co} runs an online marketplace for household goods from independent makers.",
        "{co} operates stores and a web shop that share one catalog and one inventory.",
        "At {co}, a small team looks after the whole path from search to delivery.",
    ],
    "education": [
        "{co} offers tutoring and course tools to schools that want better outcomes.",
        "{co} builds learning software used in classrooms every day.",
        "At {co}, teachers are our first customers and our first critics.",
    ],
    "finance": [
        "{co} provides payments and small business lending to shops and service firms.",
        "{co} builds risk and onboarding tools for a regional lender.",
        "At {co}, careful engineering and clear communication matter more than speed.",
    ],
}

# (title, family, probability the technical sentence appears)
ROLES = [
    ("Product Manager", "product", 0.55),
    ("Technical Product Manager", "product", 0.95),
    ("Product Manager, Platform", "product", 0.85),
    ("Product Manager, Growth", "product", 0.40),
    ("Product Manager, Data", "product", 0.80),
    ("Operations Manager", "other", 0.15),
    ("Account Executive", "other", 0.05),
    ("Financial Analyst", "other", 0.20),
    ("Customer Success Manager", "other", 0.10),
    ("Field Marketing Manager", "other", 0.05),
    ("Warehouse Operations Lead", "other", 0.10),
    ("Software Engineer", "other", 0.95),
    ("Data Analyst", "other", 0.85),
]
PRODUCT_WEIGHT = 0.6

PREFIX = {
    "early": ["Associate ", "Associate ", ""],
    "mid": [""],
    "lead": ["Senior ", "Principal ", "Group ", "Senior "],
}

ROLE_LINE = [
    "We are hiring for the {title} role on a team of about twelve people.",
    "This {title} position reports to a director and works with several teams.",
    "We are looking for a {title} to join a team that is growing this year.",
]
RESP_PRODUCT = [
    "You will set the roadmap, write clear specs and decide what ships next.",
    "You will interview customers every week and turn what you hear into priorities.",
    "You will define success metrics and review them with engineering and design.",
    "You will run launches from first draft to the first month of usage data.",
    "You will weigh tradeoffs between scope, cost and timing and explain your choices.",
]
RESP_OTHER = [
    "You will own a set of recurring tasks and report on progress each month.",
    "You will work with colleagues in several departments to keep projects moving.",
    "You will prepare summaries for leadership and flag risks early.",
    "You will improve the processes your team uses and document what you change.",
    "You will manage relationships with customers and partners over the long term.",
    "You will track a handful of numbers that tell the team how the work is going.",
]
REQ = {
    "early": [
        "You have 0 to 2 years of relevant experience, and recent graduates are welcome.",
        "You have up to 2 years of experience, and we expect to teach you the rest.",
    ],
    "mid": [
        "You have 3 to 5 years of experience in a similar role.",
        "You bring 4 years of experience and have shipped work end to end.",
    ],
    "lead": [
        "You have 8 or more years of experience and have led a team before.",
        "You bring 10 years of experience and a record of mentoring others.",
    ],
}
TECH = [
    "You will work daily with engineers on APIs, data models and system tradeoffs.",
    "A technical background is expected, and you can read code or write simple queries.",
    "You are comfortable with data pipelines, dashboards and experiments.",
]
MBA = [
    "An MBA or equivalent graduate degree is welcome but not required.",
    "We hire MBA graduates for this role every year.",
    "Graduate business training is a plus.",
]
NO_SPONSOR = [
    "We are unable to sponsor work visas for this position.",
    "US citizenship is required for this role.",
    "Applicants must be authorized to work in the United States without current or future sponsorship.",
    "This position does not offer visa sponsorship of any kind.",
    "Only permanent residents and citizens may apply.",
]
SPONSOR_OK = [
    "Visa sponsorship is available for qualified candidates.",
    "We have supported work visas for new hires before and are glad to do it again.",
]
NEUTRAL = [
    "We welcome applicants from every background.",
    "Our benefits include health coverage and a learning budget.",
]
CLOSING = [
    "Send us a short note about a project you are proud of.",
    "The interview process has three short conversations.",
    "We review applications on a rolling basis.",
]

US_CITIES = ["Austin, TX", "Denver, CO", "Chicago, IL", "Seattle, WA", "Boston, MA",
             "Atlanta, GA", "San Francisco, CA", "New York, NY", "Raleigh, NC"]
NON_US_CITIES = ["Toronto, Canada", "Dublin, Ireland", "Bengaluru, India",
                 "London, United Kingdom", "Singapore, Singapore"]


def _clamp(value, low, high):
    return max(low, min(high, value))


def _pick(rng, options):
    return options[int(rng.random() * len(options)) % len(options)]


def make_posting(rng, index):
    """Return (text, labels) for one posting. Consumes rng in a fixed order."""
    company, industry = _pick(rng, COMPANIES)
    seniority = _pick(rng, ["early", "early", "mid", "mid", "mid", "lead", "lead"])
    is_product = rng.random() < PRODUCT_WEIGHT
    pool = [r for r in ROLES if (r[1] == "product") == is_product]
    base_title, family, tech_p = _pick(rng, pool)
    title = _pick(rng, PREFIX[seniority]) + base_title
    technical = rng.random() < tech_p
    mba = rng.random() < 0.45
    us = rng.random() < 0.8
    remote = _pick(rng, ["remote", "hybrid", "onsite", "hybrid", "onsite"])
    no_sponsorship = rng.random() < 0.35
    sponsor_ok = (not no_sponsorship) and rng.random() < 0.3

    if us:
        city = _pick(rng, US_CITIES)
        country = "the United States"
    else:
        city = _pick(rng, NON_US_CITIES)
        country = city.split(", ")[1]
    if remote == "remote":
        location = "Remote ({})".format("United States" if us else country)
        loc_sentence = "This is a fully remote role for candidates based in {}.".format(country)
    elif remote == "hybrid":
        location = city
        loc_sentence = "The team works from our {} office three days a week and remotely the rest.".format(
            city.split(",")[0])
    else:
        location = city
        loc_sentence = "This role is fully onsite at our {} office.".format(city.split(",")[0])

    sentences = [_pick(rng, INTRO[industry]).format(co=company),
                 _pick(rng, ROLE_LINE).format(title=title)]
    resp_pool = RESP_PRODUCT if family == "product" else RESP_OTHER
    pool_copy = list(resp_pool)
    rng.shuffle(pool_copy)
    n_resp = 2 + (1 if rng.random() < 0.5 else 0)
    sentences.extend(pool_copy[:n_resp])
    sentences.append(_pick(rng, REQ[seniority]))
    if technical:
        sentences.append(_pick(rng, TECH))
    if mba:
        sentences.append(_pick(rng, MBA))
    sentences.append(loc_sentence)
    if no_sponsorship:
        sentences.append(_pick(rng, NO_SPONSOR))
    elif sponsor_ok:
        sentences.append(_pick(rng, SPONSOR_OK))
    else:
        if rng.random() < 0.5:
            sentences.append(_pick(rng, NEUTRAL))
    closing = _pick(rng, CLOSING)
    if len(sentences) < 10:
        sentences.append(closing)
    while len(sentences) > 10:
        # drop the optional tail first, then a responsibility line (index 2 is the first one)
        sentences.pop(2)
    assert 6 <= len(sentences) <= 10, len(sentences)

    text = "Title: {}\nCompany: {}\nLocation: {}\n\n{}\n".format(
        title, company, location, " ".join(sentences))
    signals = int(family == "product") + int(technical) + int(mba) + int(seniority == "early") + int(us)
    fit = _clamp(signals, 1, 5)
    labels = {
        "id": "p{:03d}".format(index + 1),
        "title": title,
        "company": company,
        "no_sponsorship": no_sponsorship,
        "seniority": seniority,
        "remote": remote,
        "fit": fit,
        "signals": {"product": family == "product", "technical": technical, "mba": mba,
                    "early": seniority == "early", "us": us},
    }
    return text, labels


def gold_score(labels, weights=None):
    w = weights or WEIGHTS
    return (w["fit"] * (labels["fit"] - 1) / 4.0
            + w["sponsorship"] * (0.0 if labels["no_sponsorship"] else 1.0)
            + w["seniority"] * SENIORITY_W[labels["seniority"]]
            + w["remote"] * REMOTE_W[labels["remote"]])


def generate(n=N_POSTINGS, seed=SEED):
    """Return a list of (text, labels) with gold_score and gold_rank filled in."""
    rng = random.Random(seed)
    rows = [make_posting(rng, i) for i in range(n)]
    for _, labels in rows:
        labels["gold_score"] = round(gold_score(labels), 6)
    order = sorted(rows, key=lambda r: (-r[1]["gold_score"], r[1]["id"]))
    for rank, (_, labels) in enumerate(order, start=1):
        labels["gold_rank"] = rank
    return rows


def write(outdir, n=N_POSTINGS, seed=SEED):
    rows = generate(n, seed)
    pdir = os.path.join(outdir, "postings")
    os.makedirs(pdir, exist_ok=True)
    for name in os.listdir(pdir):
        if name.endswith(".txt"):
            os.remove(os.path.join(pdir, name))
    with open(os.path.join(outdir, "gold.jsonl"), "w", encoding="utf-8") as gold:
        for text, labels in rows:
            with open(os.path.join(pdir, labels["id"] + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(text)
            gold.write(json.dumps(labels, sort_keys=True) + "\n")
    return rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rows = write(here)
    spons = sum(1 for _, l in rows if l["no_sponsorship"])
    print("wrote {} postings to {} ({} no-sponsorship)".format(len(rows), here, spons))
    return 0


if __name__ == "__main__":
    sys.exit(main())
