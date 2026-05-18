SERVICE_CATEGORIES = [
    {
        "title": "染髮服務",
        "services": [
            {
                "name": "日本資生堂染髮",
                "description": "適合想改變髮色、提升整體造型，並重視染後質感的顧客。",
                "keywords": ["資生堂染髮", "染髮", "髮色", "顏色", "造型", "質感"],
            },
            {
                "name": "日本哥德式染髮",
                "description": "適合想染髮，同時在意染後髮質與修護感的顧客。",
                "keywords": ["哥德式染髮", "染後", "染髮修護", "染後髮質"],
            },
        ],
    },
    {
        "title": "護髮服務",
        "services": [
            {
                "name": "哥德式護髮",
                "description": "適合染燙後受損、乾燥或髮尾毛裂，需要深層修護的顧客。",
                "keywords": ["哥德式護髮", "受損", "修護", "深層", "染燙", "髮尾毛裂"],
            },
            {
                "name": "資生堂護髮",
                "description": "適合想提升柔順度、光澤與髮絲觸感的顧客。",
                "keywords": ["資生堂護髮", "柔順", "光澤", "毛躁", "觸感"],
            },
        ],
    },
]

SERVICE_HINTS = {
    service["name"]: {
        "reason": service["description"],
        "keywords": service["keywords"],
    }
    for category in SERVICE_CATEGORIES
    for service in category["services"]
}

SERVICE_OPTIONS = {
    service_name: details["reason"]
    for service_name, details in SERVICE_HINTS.items()
}
