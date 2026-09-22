import os
import random
from dotenv import load_dotenv
from google import genai

load_dotenv()

# 16 Diverse Extempore & Speech Practice Categories with Offline Backup Topics
CATEGORIES = {
    "Technology & Artificial Intelligence": [
        "The Ethical Implications of Autonomous AI Agents",
        "Brain-Computer Interfaces: Evolution or Danger?",
        "Quantum Computing and the Death of Traditional Encryption",
        "Deepfakes, Misinformation, and the Erosion of Digital Trust",
        "Will Artificial General Intelligence Replace Human Creativity?",
    ],
    "Space & Cosmology": [
        "The Fermi Paradox: Where Are All the Aliens?",
        "The Overview Effect and How Spaceflight Alters Consciousness",
        "Terraforming Mars: Humanity's Greatest Frontier or Folly?",
        "Kessler Syndrome: The Danger of Space Debris",
        "The Dark Flow and Unexplained Cosmic Structures",
    ],
    "History & Historical Mysteries": [
        "The Dancing Plague of 1518: Collective Hysteria in History",
        "The Mystery of the Antikythera Mechanism",
        "The Year Without a Summer (1816) and Its Global Aftermath",
        "Ghost Ships and the Unsolved 'Mary Celeste' Mystery",
        "The Voynich Manuscript: Code, Language, or Hoax?",
    ],
    "Philosophy & Ethics": [
        "The Ship of Theseus: Personal Identity Through Constant Change",
        "The Ethics of Gene Editing and Designer Babies",
        "Determinism vs. Free Will in the Age of Neuroscience",
        "Is Utilitarianism Still Practical in the Modern World?",
        "The Hedonic Treadmill and the Pursuit of Genuine Happiness",
    ],
    "Psychology & Human Behavior": [
        "The Tetris Effect: How Repetition Rewires the Brain",
        "Decision Fatigue and How Micro-Choices Drain Mental Energy",
        "The Bystander Effect and Social Responsibility in Crises",
        "Imposter Syndrome in High Achievers",
        "The Psychology of Nostalgia and Why the Past Feels Comforting",
    ],
    "Environment & Climate Sustainability": [
        "Solar Radiation Management: Geoengineering Climate Solutions",
        "The Ocean Plastic Crisis and Bioplastic Alternatives",
        "Nuclear Energy: Necessary Bridge or Outdated Hazard?",
        "Rewilding Ecosystems to Restore Biodiversity",
        "Circular Economy: Transitioning Away from Disposable Culture",
    ],
    "Business, Startups & Economics": [
        "The Gig Economy: Flexibility vs. Worker Exploitation",
        "Why 90% of Startups Fail: Lessons from Market Mismatches",
        "The Fall of Monopolies in the Digital Era",
        "Central Bank Digital Currencies (CBDCs) and Financial Privacy",
        "The Psychology of Pricing and Consumer Irrationality",
    ],
    "Art, Architecture & Culture": [
        "Brutalist Architecture: Heroic Monumentalism or Ugly Concrete?",
        "AI Generated Art: Is Authenticity Dead?",
        "How Minimalist Design Influences Human Wellbeing",
        "Cultural Preservation in an Ultra-Globalized World",
        "Street Art: Vandalism or Legitimate Public Expression?",
    ],
    "Society & Modern Media": [
        "The Illusion of Hyper-Connectivity in the Social Media Age",
        "Doomscrolling and Attention Span Fragmentation",
        "Echo Chambers and the Polarization of Public Discourse",
        "Cancel Culture: Accountability vs. Mob Mentality",
        "The Rise of Solitary Lifestyles in Megacities",
    ],
    "Education & Future of Work": [
        "Are Traditional 4-Year College Degrees Becoming Obsolete?",
        "The 4-Day Work Week: Productivity Boost or Corporate Fantasy?",
        "Gamification of Learning: Revolutionizing Classrooms",
        "Remote Work vs. Office Collaboration: The Permanent Shift",
        "Soft Skills vs. Technical Skills in an Automated Future",
    ],
    "Health, Neuroscience & Longevity": [
        "The Science and Ethics of Radical Life Extension",
        "Circadian Rhythms and the Modern Epidemic of Sleep Deprivation",
        "The Gut-Brain Axis: How Microbiome Governs Mental Health",
        "Neuroplasticity: Can the Adult Brain Truly Reinvent Itself?",
        "Ultra-Processed Foods and the Metabolic Crisis",
    ],
    "Literature, Cinema & Storytelling": [
        "Why Dystopian Fiction Resonates Across Generations",
        "The Hero's Journey: Why Monomyth Still Rules Hollywood",
        "The Decline of Traditional Print Books in the Screen Age",
        "Anti-Heroes in Modern Media: Why We Love Flawed Protagonists",
        "The Art of the Open Ending in Cinema and Literature",
    ],
    "Sports, Adventure & Human Endurance": [
        "The Psychology of Solo Extreme Mountaineering",
        "The Ethics of Performance Enhancements and Biohacking in Sports",
        "Esports as Olympic Contenders: Redefining Athlete",
        "The Ultramarathon Mindset: Pushing Past the Breaking Point",
        "Risk vs. Reward in Extreme Action Sports",
    ],
    "Geopolitics & Global Affairs": [
        "The Race for Rare Earth Minerals and Clean Tech Dominance",
        "The Future of the United Nations in a Multipolar World",
        "Cyber Warfare as the Primary Domain of Modern Conflict",
        "Global Demographic Collapse: Shrinking Populations",
        "Water Scarcity as the Next Catalyst for International Conflict",
    ],
    "Scientific Wonders & Quantum Concepts": [
        "Quantum Entanglement and Einstein's 'Spooky Action at a Distance'",
        "CRISPR and the Dawn of Programmable Biology",
        "Dark Matter and Dark Energy: The 95% of the Universe We Can't See",
        "Superconductivity at Room Temperature: The Holy Grail of Physics",
        "The Great Emu War and Ecological Unintended Consequences",
    ],
    "Deep Dilemmas & Thought Experiments": [
        "The Experience Machine: Would You Choose Simulated Perfection?",
        "The Trolley Problem in Programming Self-Driving Cars",
        "The Veil of Ignorance: Designing a Truly Fair Society",
        "The Boltzmann Brain Paradox in Infinite Space",
        "The Chinese Room Argument: Can Machines Ever Truly Understand?",
    ],
}

FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def get_all_categories() -> list[str]:
    """Return a list of all available topic categories."""
    return list(CATEGORIES.keys())


def _generate_topic_with_gemini(category: str) -> str:
    """Generate a fresh, thought-provoking extempore topic using Gemini AI."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured in .env")

    client = genai.Client(api_key=api_key)

    prompt = (
        f"You are a speech contest topic generator. Generate ONE engaging, "
        f"thought-provoking extempore/impromptu speech topic for the category: "
        f"'{category}'.\n"
        f"Rules:\n"
        f"1. Return ONLY the single topic title/phrase (under 12 words).\n"
        f"2. Do NOT add quotation marks, bullet points, numbering, or intro text.\n"
        f"3. Make it interesting and suitable for a 1-minute speech."
    )

    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            chat = client.chats.create(model=model_name)
            res = chat.send_message(prompt)
            if res and res.text:
                topic = res.text.strip().strip('"').strip("'").strip()
                lines = [ln.strip() for ln in topic.splitlines() if ln.strip()]
                if lines:
                    topic = lines[0].lstrip("-*#0123456789. ")
                topic = topic.replace("**", "").replace("*", "").strip()
                if topic:
                    return topic
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Could not generate topic from Gemini.")


def get_random_topic(category: str | None = None) -> tuple[str, str]:
    """Get a random speech topic from a specified or randomly selected category.

    Uses Gemini AI API to generate a fresh topic. If offline or if the API
    fails, automatically falls back to a curated offline topic bank.

    Args:
        category: Optional category name from get_all_categories().
                  If None, a random category is chosen.

    Returns:
        tuple of (category_name, topic_name)
    """
    if not category or category not in CATEGORIES:
        category = random.choice(list(CATEGORIES.keys()))

    # Attempt online generation via Gemini
    try:
        topic = _generate_topic_with_gemini(category)
        return category, topic
    except Exception as e:
        print(f"  [Note] Using offline topic bank ({type(e).__name__})")
        backup_topics = CATEGORIES.get(category, [])
        if backup_topics:
            topic = random.choice(backup_topics)
        else:
            topic = "The Impact of Modern Innovation on Society"
        return category, topic


if __name__ == "__main__":
    print("=== Testing SpeakWise Topic Generator ===")
    print(f"Total Available Categories: {len(CATEGORIES)}\n")

    for i in range(3):
        cat, top = get_random_topic()
        print(f"[{i+1}] Category: {cat}")
        print(f"    Topic:    {top}\n")