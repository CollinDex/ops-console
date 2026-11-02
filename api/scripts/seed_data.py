"""Plain name lists for the seed. Fictional data; no Faker (it has no Nigerian locale)."""

from app.models.enums import CheckType, Sector

FIRST_NAMES = [
    # Yoruba
    "Adebayo", "Folake", "Tunde", "Yemi", "Funmilayo", "Segun", "Bukola", "Kunle",
    "Damilola", "Temitope", "Olumide", "Abiola",
    # Igbo
    "Chinedu", "Ngozi", "Emeka", "Chioma", "Obinna", "Ifeoma", "Nnamdi", "Adaeze",
    "Uchenna", "Amaka", "Ikenna", "Chiamaka",
    # Hausa
    "Musa", "Aisha", "Ibrahim", "Fatima", "Sani", "Zainab", "Abdullahi", "Hauwa",
    "Yusuf", "Maryam", "Bello", "Halima",
    # Edo
    "Osagie", "Eghosa", "Iyobosa", "Osaze", "Ehi", "Nosa", "Efe", "Idemudia",
    # Ijaw
    "Preye", "Ebiere", "Tamuno", "Ebi", "Ogbonna", "Timi", "Seiyefa", "Ebikibina",
]  # fmt: skip

SURNAMES = [
    # Yoruba
    "Adeyemi", "Ogunleye", "Balogun", "Olawale", "Adewale", "Akinola", "Fashola", "Ojo",
    "Bakare", "Ayodele", "Oyelaran", "Alabi",
    # Igbo
    "Okonkwo", "Nwosu", "Eze", "Okafor", "Chukwu", "Nnadi", "Obi", "Onyeama",
    "Ugwu", "Anyanwu", "Okeke", "Madu",
    # Hausa
    "Danjuma", "Abubakar", "Garba", "Lawal", "Yakubu", "Suleiman", "Umar", "Mohammed",
    "Aliyu", "Hassan", "Idris", "Shehu",
    # Edo
    "Igbinedion", "Osaretin", "Ehigiator", "Aigbokhan", "Omoregie", "Uwaifo", "Oviasu",
    "Ogbemudia",
    # Ijaw
    "Ebiowei", "Ekpo", "Tonye", "Dikio", "Ogoriba", "Kuromiema", "Alagoa", "Opuowei",
]  # fmt: skip

# 12 extra staff (the three demo logins are defined in seed.py): (first, last, role).
EXTRA_STAFF = [
    ("Chidi", "Eze", "ops_admin"),
    ("Funke", "Adeyemi", "ops_admin"),
    ("Ibrahim", "Garba", "ops_admin"),
    ("Ngozi", "Nwosu", "ops_admin"),
    ("Bola", "Ogunleye", "analyst"),
    ("Emeka", "Okafor", "analyst"),
    ("Zainab", "Lawal", "analyst"),
    ("Osagie", "Omoregie", "analyst"),
    ("Preye", "Ekpo", "analyst"),
    ("Kunle", "Balogun", "analyst"),
    ("Amaka", "Obi", "viewer"),
    ("Sani", "Danjuma", "viewer"),
]  # fmt: skip

NAME_PREFIXES = [
    "Adebayo", "Chukwu", "Danjuma", "Okonkwo", "Eko", "Arewa", "Naija", "Zuma",
    "Lagos", "Niger", "Delta", "Ibadan", "Kano", "Abuja", "Sapele", "Ogun",
    "Afolabi", "Okoro", "Balogun", "Umar", "Eze", "Bello", "Obi", "Nwachukwu",
    "Ayo", "Chioma", "Tunde", "Kemi", "Sunrise", "Golden", "Royal", "Heritage",
    "Pinnacle", "Alpha", "Unity", "Crown", "Bright", "Prime", "Evergreen", "Zenith",
]  # fmt: skip

SECTOR_WORDS: dict[Sector, list[str]] = {
    Sector.agriculture: ["Agro", "Farms", "Foods"],
    Sector.retail: ["Stores", "Mart", "Trading"],
    Sector.manufacturing: ["Industries", "Plastics", "Packaging"],
    Sector.logistics: ["Logistics", "Haulage", "Freight"],
    Sector.technology: ["Tech", "Digital", "Systems"],
    Sector.healthcare: ["Pharma", "Clinics", "Medicals"],
    Sector.hospitality: ["Hotels", "Suites", "Catering"],
    Sector.construction: ["Builders", "Construction", "Estates"],
    Sector.fashion: ["Fabrics", "Couture", "Styles"],
    Sector.education: ["Academy", "Schools", "Learning"],
}

NAME_SUFFIXES = ["Ltd", "Nigeria Ltd", "Enterprises", "Ventures", "Global Services Ltd"]

BANKS = [
    "Access Bank", "GTBank", "Zenith Bank", "First Bank", "UBA", "Moniepoint",
    "Kuda", "Wema Bank", "Fidelity Bank", "Stanbic IBTC", "Sterling Bank", "Providus Bank",
]  # fmt: skip

# 36 states + FCT.
HEAVY_STATES = {
    "Lagos": 30, "FCT": 12, "Rivers": 4, "Oyo": 4, "Kano": 4, "Kaduna": 4,
    "Anambra": 4, "Enugu": 4, "Ogun": 4, "Delta": 4,
}  # fmt: skip
OTHER_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Ebonyi", "Edo", "Ekiti", "Gombe", "Imo", "Jigawa", "Katsina",
    "Kebbi", "Kogi", "Kwara", "Nasarawa", "Niger", "Ondo", "Osun", "Plateau",
    "Sokoto", "Taraba", "Yobe", "Zamfara",
]  # fmt: skip
ALL_STATES = [*HEAVY_STATES, *OTHER_STATES]

FAILURE_REASONS: dict[CheckType, list[str]] = {
    CheckType.cac: [
        "CAC number not found in registry",
        "Company name does not match CAC record",
        "Company status is inactive",
    ],
    CheckType.tin: [
        "TIN not registered with FIRS",
        "TIN does not match company name",
    ],
    CheckType.bvn: [
        "BVN name does not match director",
        "BVN date of birth mismatch",
        "BVN record not found",
    ],
    CheckType.bank_link: [
        "Account name does not match company name",
        "Bank consent expired",
        "Statement fetch timed out",
    ],
}

# Failure weights: bvn > bank_link > cac > tin.
FAILURE_WEIGHTS: dict[CheckType, int] = {
    CheckType.bvn: 4,
    CheckType.bank_link: 3,
    CheckType.cac: 2,
    CheckType.tin: 1,
}
