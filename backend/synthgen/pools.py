"""Curated, fully synthetic data pools for the generator.

All names are common, generic Indian given-names / surnames with their Devanagari
spellings and a few realistic romanization variants. Nothing here refers to any
real individual — it exists only to reproduce the *shape* of real-world noise
(transliteration, honorifics, spelling drift) described in the proposal.
"""
from __future__ import annotations

from collections import namedtuple

# canonical  = the "true" romanized form we cluster back to
# devanagari = Devanagari spelling (may be "" if we don't ship one)
# variants   = alternative romanizations seen in the wild
NameEntry = namedtuple("NameEntry", ["canonical", "devanagari", "variants"])

MALE_FIRST_NAMES = [
    NameEntry("Mohammad", "मोहम्मद", ["Mohd", "Md", "Mohamad", "Muhammad", "Mohammed"]),
    NameEntry("Arif", "आरिफ", ["Aarif", "Arief"]),
    NameEntry("Imran", "इमरान", ["Emran", "Imraan"]),
    NameEntry("Salman", "सलमान", ["Salmaan"]),
    NameEntry("Abdul", "अब्दुल", ["Abdool"]),
    NameEntry("Rahim", "रहीम", ["Raheem", "Raheem"]),
    NameEntry("Ram", "राम", ["Raam"]),
    NameEntry("Prasad", "प्रसाद", ["Prashad"]),
    NameEntry("Suresh", "सुरेश", ["Sureshh"]),
    NameEntry("Ramesh", "रमेश", ["Rameshh"]),
    NameEntry("Rajesh", "राजेश", ["Rajeshh"]),
    NameEntry("Vijay", "विजय", ["Bijay", "Vijai"]),
    NameEntry("Anil", "अनिल", ["Aneel"]),
    NameEntry("Sunil", "सुनील", ["Suneel"]),
    NameEntry("Amit", "अमित", ["Ameet"]),
    NameEntry("Rakesh", "राकेश", ["Rakeshh"]),
    NameEntry("Deepak", "दीपक", ["Dipak"]),
    NameEntry("Manoj", "मनोज", ["Manooj"]),
    NameEntry("Sanjay", "संजय", ["Sanjai"]),
    NameEntry("Ravi", "रवि", ["Ravee"]),
]

FEMALE_FIRST_NAMES = [
    NameEntry("Priya", "प्रिया", ["Priyaa"]),
    NameEntry("Sunita", "सुनीता", ["Suneeta"]),
    NameEntry("Anjali", "अंजली", ["Anjalee"]),
    NameEntry("Pooja", "पूजा", ["Puja"]),
    NameEntry("Neha", "नेहा", ["Nehaa"]),
    NameEntry("Kavita", "कविता", ["Kavita", "Kabita"]),
    NameEntry("Fatima", "फ़ातिमा", ["Fatema", "Fatmah"]),
    NameEntry("Ayesha", "आयशा", ["Aisha", "Ayisha"]),
    NameEntry("Sana", "सना", ["Sanaa"]),
    NameEntry("Meena", "मीना", ["Mina"]),
]

SURNAMES = [
    NameEntry("Kumar", "कुमार", ["Kumaar"]),
    NameEntry("Sharma", "शर्मा", ["Sharmaa", "Sarma"]),
    NameEntry("Verma", "वर्मा", ["Varma"]),
    NameEntry("Yadav", "यादव", ["Yaadav"]),
    NameEntry("Singh", "सिंह", ["Singhh"]),
    NameEntry("Gupta", "गुप्ता", ["Guptaa"]),
    NameEntry("Khan", "ख़ान", ["Khaan", "Xan"]),
    NameEntry("Sheikh", "शेख़", ["Shaikh", "Shaik", "Sheik"]),
    NameEntry("Ansari", "अंसारी", ["Ansaari"]),
    NameEntry("Mishra", "मिश्रा", ["Misra", "Mishraa"]),
    NameEntry("Pandey", "पांडे", ["Pande", "Pandy"]),
    NameEntry("Reddy", "रेड्डी", ["Reddi"]),
    NameEntry("Das", "दास", ["Daas"]),
]

# (locality, district, state)
PLACES = [
    ("Hazratganj", "Lucknow", "Uttar Pradesh"),
    ("Aminabad", "Lucknow", "Uttar Pradesh"),
    ("Gomti Nagar", "Lucknow", "Uttar Pradesh"),
    ("Sadar Bazar", "Kanpur", "Uttar Pradesh"),
    ("Civil Lines", "Kanpur", "Uttar Pradesh"),
    ("Malviya Nagar", "Jaipur", "Rajasthan"),
    ("Vaishali Nagar", "Jaipur", "Rajasthan"),
    ("Andheri", "Mumbai", "Maharashtra"),
    ("Dadar", "Mumbai", "Maharashtra"),
    ("Salt Lake", "Kolkata", "West Bengal"),
    ("Connaught Place", "New Delhi", "Delhi"),
    ("Karol Bagh", "New Delhi", "Delhi"),
]

BANKS = ["SBI", "HDFC", "ICICI", "Axis", "PNB", "Bank of Baroda", "Kotak", "Canara"]

# (section, short description)
IPC_SECTIONS = [
    ("302", "Murder"),
    ("379", "Theft"),
    ("420", "Cheating"),
    ("406", "Criminal breach of trust"),
    ("120B", "Criminal conspiracy"),
    ("326", "Grievous hurt"),
    ("392", "Robbery"),
    ("467", "Forgery"),
    ("66C IT Act", "Identity theft"),
    ("66D IT Act", "Cheating by personation"),
]

# state RTO code prefixes for vehicle plates, keyed by state
RTO_SERIES = {
    "Uttar Pradesh": ["UP15", "UP32", "UP78"],
    "Rajasthan": ["RJ14", "RJ45"],
    "Maharashtra": ["MH01", "MH02", "MH12"],
    "West Bengal": ["WB02", "WB06"],
    "Delhi": ["DL3C", "DL8C"],
}

HONORIFICS = ["Sh.", "Shri", "Mr.", "Md.", "Smt.", "Ms."]

# address abbreviations for noisy address rendering
ADDR_ABBR = {
    "Road": ["Rd", "Rd.", "road"],
    "Street": ["St", "St.", "gali"],
    "House No": ["H.No", "HNo", "h.no", "makan no"],
    "Near": ["nr", "nr.", "paas"],
}
