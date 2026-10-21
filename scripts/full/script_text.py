"""The narration of the full video, as data: chapters -> paragraphs -> sentences.

Every sentence gets an id (S001...) that the shot list, the voice timings and the animation
settings all refer to. Run this file to write public/full/script.json.
"""
import json, re
from pathlib import Path

CHAPTERS = [
    ("intro", "Opening", [
        "The goal of ten thousand steps a day did not come from a lab. "
        "It came from a step counter sold in Japan in 1965. "
        "Its name meant ten thousand steps meter. "
        "Nobody had tested the number. "
        "It was simply easy to remember.",

        "So here's what we'll find out. "
        "What actually happens inside your body when you walk? "
        "And how many steps does the science say you really need? "
        "By the end, we'll come back to that little step counter, and see how close it came.",
    ]),
    ("ch1", "Where did ten thousand come from?", [
        "Let's start with that step counter. "
        "In the 1960s, Japan was excited about fitness. "
        "Tokyo had just hosted the Olympic Games. "
        "A company called Yamasa sold a small step counter you clipped to your belt. "
        "Inside, a little weight swung with each step and moved the count up by one. "
        "They called it manpo-kei. "
        "Man means ten thousand. "
        "Po means step. "
        "Kei means meter. "
        "Put together, a ten thousand steps meter.",

        "It was a good name. "
        "But it was not a finding. "
        "Years later, a Harvard researcher named I-Min Lee went looking for the science behind the number. "
        "She found it had started as a brand name. "
        "So researchers began to test it properly, with real people wearing step counters. "
        "We'll get to what they found. "
        "But first, a simpler question. "
        "What does one step actually do?",
    ]),
    ("ch2", "What happens in your legs?", [
        "Take one step and look at your legs. "
        "Walking uses some of the biggest muscles in your body. "
        "The big muscles at the front of your thigh tighten to keep your knee steady. "
        "The muscles at the back of your hip and thigh push your body forward. "
        "And down in your calf, a muscle squeezes every time you push off the ground.",

        "That squeeze does a second job. "
        "Your leg veins have tiny one-way valves, like little doors. "
        "When your calf muscle tightens, it presses on the veins and pushes blood up towards your heart. "
        "The valves close behind it, so the blood can't slide back down. "
        "Doctors call this the calf muscle pump. "
        "It's one reason your ankles can swell when you sit still on a long flight.",

        "So every step moves blood. "
        "But those working muscles need fuel to keep going. "
        "Where do they get it?",
    ]),
    ("ch3", "Where does the sugar go?", [
        "After you eat, sugar from your food moves into your blood. "
        "Your body needs to clear it out and store it somewhere. "
        "And the biggest place it goes is your muscles. "
        "When researchers measured this, about eighty percent of the sugar cleared from the blood went into muscle.",

        "Normally, muscles need a hormone called insulin to let sugar in. "
        "Insulin works like a key. "
        "But a working muscle has its own way in. "
        "When it contracts, it moves little sugar doors to its surface and pulls sugar in by itself. "
        "So when your legs are moving, they soak up sugar from your blood.",

        "This is why the timing of a walk can matter. "
        "In a study from New Zealand, people with type 2 diabetes tried two plans. "
        "First, one thirty-minute walk a day, whenever they liked. "
        "Then, a ten-minute walk after each meal. "
        "Same total time. "
        "But walking after meals lowered their blood sugar after eating by about twelve percent. "
        "After dinner, the drop was bigger, about twenty-two percent.",

        "So a walk works on your blood sugar right away. "
        "But all that blood, full of fuel, needs something to push it around. "
        "That's the job of the heart. "
        "What does walking do to it?",
    ]),
    ("ch4", "What does walking do to your heart?", [
        "At rest, an adult heart usually beats between sixty and one hundred times a minute. "
        "When you start walking, it beats faster. "
        "It sends more blood to the muscles that are working. "
        "The blood vessels in those muscles widen to let it through. "
        "Like any muscle, your heart adapts to the work you give it.",

        "Something else happens after the walk ends. "
        "Your blood pressure can stay lower than it was before, for hours. "
        "Scientists call this post-exercise hypotension. "
        "One walk gives you a small dip. "
        "Walking most days keeps giving it to you.",

        "So how much is enough? "
        "The World Health Organization says adults should get at least 150 minutes of moderate activity a week. "
        "That's about twenty minutes a day. "
        "A brisk walk counts. "
        "And it doesn't have to happen all at once. "
        "Short walks add up too. "
        "But your heart isn't the only organ that changes. "
        "What about the one doing the thinking?",
    ]),
    ("ch5", "What does walking do to your brain?", [
        "Deep inside your brain there's a curled-up structure called the hippocampus. "
        "Its name means seahorse, because of its shape. "
        "It helps you form new memories. "
        "And as we get older, it slowly shrinks.",

        "In one study, older adults walked for forty minutes, three days a week, for a year. "
        "Another group only did stretching. "
        "Then the researchers scanned their brains. "
        "In the walkers, the hippocampus grew by about two percent. "
        "In the stretching group, it kept shrinking. "
        "That's like turning back one to two years of age-related loss.",

        "A much larger study in the UK followed about seventy-eight thousand adults wearing step counters. "
        "People who took about nine thousand eight hundred steps a day had about half the risk of dementia. "
        "Even three thousand eight hundred steps a day was linked to about a quarter lower risk.",

        "Walking even changes how you think in the moment. "
        "In a Stanford study, eighty-one percent of people came up with more creative ideas while walking than while sitting. "
        "Even on a treadmill, facing a blank wall. "
        "So if walking can change the brain, can it change how we feel?",
    ]),
    ("ch6", "Can a walk change your mood?", [
        "Depression is common. "
        "The World Health Organization calls it a leading cause of disability around the world. "
        "In 2022, scientists combined fifteen studies with nearly two hundred thousand people. "
        "They looked at who later developed depression.",

        "People who got the activity doctors recommend, about two and a half hours of brisk walking a week, had a twenty-five percent lower risk of depression. "
        "People who did half that still had about an eighteen percent lower risk. "
        "The biggest jump came from going from nothing to something.",

        "That's good news if you're starting from zero. "
        "You don't need a lot to get much of the benefit. "
        "A short walk around the block is a fine place to begin. "
        "But it raises a practical question. "
        "When you do walk, does it matter how fast?",
    ]),
    ("ch7", "Does speed matter?", [
        "Researchers in Britain looked at more than fifty thousand walkers. "
        "They simply asked people how fast they usually walked. "
        "Slow, average, or brisk. "
        "Then they followed them for years.",

        "Compared with slow walkers, people who said they walked at an average pace had about a twenty percent lower risk of dying during the study. "
        "Brisk walkers had about a twenty-four percent lower risk.",

        "So what counts as brisk? "
        "A simple guide is about one hundred steps a minute. "
        "That's roughly where walking becomes moderate exercise. "
        "You can check it yourself. "
        "Count your steps for fifteen seconds, then multiply by four. "
        "If you get about twenty-five, you're right around one hundred steps a minute.",

        "Pace helps. "
        "But two large step studies found something interesting. "
        "Once they counted everyone's total steps, how fast they walked made little extra difference. "
        "The count mattered most. "
        "Which brings us back to the big question. "
        "How many steps do you actually need?",
    ]),
    ("ch8", "How many steps do you really need?", [
        "Remember I-Min Lee, the researcher who traced the number back to that step counter? "
        "In 2019, her team studied about sixteen thousand women, with an average age of seventy-two. "
        "Each wore a step counter for a week, and the team followed them for over four years.",

        "The least active women took about two thousand seven hundred steps a day. "
        "Women who took about four thousand four hundred had a forty-one percent lower risk of dying during the study. "
        "The benefit kept growing with more steps, then leveled off at around seven thousand five hundred.",

        "A US study of nearly five thousand adults found something similar. "
        "Eight thousand steps a day, compared with four thousand, was linked to about half the risk of dying during the study.",

        "Then, in 2022, researchers pooled fifteen studies from around the world, almost forty-eight thousand people. "
        "For people over sixty, the benefit leveled off at about six to eight thousand steps. "
        "For younger adults, it leveled off at about eight to ten thousand. "
        "In other words, there comes a point where more steps add less.",
    ]),
    ("ending", "Back to the step counter", [
        "So let's go back to that little step counter from 1965. "
        "Its number wasn't based on science. "
        "It was a name that sounded good. "
        "But it turned out to be a fair guess. "
        "For younger adults, the benefit really does run up toward ten thousand.",

        "And the most important part was never the exact number. "
        "You don't need a special number to begin. "
        "The first few thousand steps make the biggest difference, especially if you're starting from very few. "
        "Every walk moves your blood, feeds your muscles, steadies your blood sugar, and is good for your brain. "
        "So the best number of steps to start with is a few more than yesterday.",
    ]),
]


def split_sentences(par):
    return [s for s in re.split(r"(?<=[.?!])\s+", par.strip()) if s]


def build():
    out, sid, pid = [], 0, 0
    for cid, title, pars in CHAPTERS:
        ch = {"id": cid, "title": title, "paragraphs": []}
        for par in pars:
            pid += 1
            sents = []
            for s in split_sentences(par):
                sid += 1
                sents.append({"id": f"S{sid:03d}", "text": s})
            ch["paragraphs"].append({"id": f"P{pid:02d}", "text": par, "sentences": sents})
        out.append(ch)
    return out


if __name__ == "__main__":
    data = build()
    Path("public/full").mkdir(parents=True, exist_ok=True)
    Path("public/full/script.json").write_text(json.dumps(data, indent=1))
    words = sum(len(p["text"].split()) for c in data for p in c["paragraphs"])
    sents = sum(len(p["sentences"]) for c in data for p in c["paragraphs"])
    pars = sum(len(c["paragraphs"]) for c in data)
    print(f"{words} words, {sents} sentences, {pars} paragraphs, {len(data)} chapters")
    for c in data:
        print(f"  {c['id']:7s} {sum(len(p['text'].split()) for p in c['paragraphs']):4d} words  {c['title']}")
