from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", "B", 20)
pdf.cell(0, 10, "ShopBot - Product Catalog", ln=True, align="C")
pdf.set_font("Arial", size=10)
pdf.cell(0, 8, "MG Road, Bhopal | Mon-Sat 9AM-6PM | Returns within 7 days", ln=True, align="C")
pdf.ln(5)

products = {
    "Smartphones": [
        ("iPhone 15", "Rs 79,999"),
        ("Samsung Galaxy S24", "Rs 74,999"),
        ("OnePlus 12", "Rs 64,999"),
        ("Redmi Note 13 Pro", "Rs 26,999"),
        ("Realme 12 Pro", "Rs 22,999"),
        ("Vivo V30", "Rs 34,999"),
        ("Oppo Reno 11", "Rs 29,999"),
        ("Google Pixel 8", "Rs 75,999"),
    ],
    "Laptops": [
        ("MacBook Air M2", "Rs 1,14,999"),
        ("Dell Inspiron 15", "Rs 55,999"),
        ("HP Pavilion 14", "Rs 49,999"),
        ("Lenovo IdeaPad Slim 5", "Rs 52,999"),
        ("Asus VivoBook 15", "Rs 47,999"),
        ("Acer Aspire 7", "Rs 58,999"),
        ("Microsoft Surface Laptop", "Rs 99,999"),
    ],
    "Audio": [
        ("Sony WH-1000XM5 Headphones", "Rs 29,999"),
        ("Apple AirPods Pro", "Rs 24,999"),
        ("Boat Airdopes 141", "Rs 1,299"),
        ("JBL Tune 770NC", "Rs 7,999"),
        ("Realme Buds Air 5", "Rs 3,499"),
        ("Bose QuietComfort 45", "Rs 31,999"),
        ("Sennheiser HD 450BT", "Rs 9,999"),
        ("Boult Audio Z40", "Rs 1,499"),
    ],
    "Smartwatches": [
        ("Apple Watch Series 9", "Rs 41,999"),
        ("Samsung Galaxy Watch 6", "Rs 27,999"),
        ("Noise ColorFit Pro 4", "Rs 3,499"),
        ("Garmin Forerunner 255", "Rs 34,999"),
        ("Boat Wave Sigma", "Rs 1,799"),
        ("Fire-Boltt Phoenix Pro", "Rs 2,499"),
        ("Amazfit GTR 4", "Rs 12,999"),
    ],
    "Cameras": [
        ("Canon EOS 1500D DSLR", "Rs 34,999"),
        ("Nikon Z30 Mirrorless", "Rs 69,999"),
        ("Sony Alpha ZV-E10", "Rs 59,999"),
        ("GoPro Hero 12", "Rs 35,999"),
        ("Fujifilm Instax Mini 12", "Rs 7,499"),
        ("DJI Osmo Pocket 3", "Rs 44,999"),
    ],
    "Accessories": [
        ("Anker 65W USB-C Charger", "Rs 2,499"),
        ("Samsung 25W Fast Charger", "Rs 1,499"),
        ("Logitech MX Master 3 Mouse", "Rs 9,999"),
        ("Keychron K2 Keyboard", "Rs 7,999"),
        ("Belkin Magsafe Charger", "Rs 4,999"),
        ("JBL Flip 6 Speaker", "Rs 9,999"),
        ("Anker PowerBank 20000mAh", "Rs 3,499"),
        ("Spigen Phone Case", "Rs 999"),
        ("Tempered Glass Pack", "Rs 299"),
        ("USB Hub 7-in-1", "Rs 1,999"),
    ],
    "TVs & Displays": [
        ("Samsung 55\" 4K Smart TV", "Rs 54,999"),
        ("LG OLED 55\" TV", "Rs 1,29,999"),
        ("Sony Bravia 43\" TV", "Rs 44,999"),
        ("Mi 40\" Full HD TV", "Rs 22,999"),
        ("Dell 27\" Monitor", "Rs 18,999"),
        ("LG 24\" IPS Monitor", "Rs 12,999"),
    ],
    "Gaming": [
        ("PlayStation 5", "Rs 54,999"),
        ("Xbox Series X", "Rs 52,999"),
        ("Nintendo Switch OLED", "Rs 34,999"),
        ("Razer DeathAdder Mouse", "Rs 4,999"),
        ("HyperX Cloud II Headset", "Rs 6,999"),
        ("Logitech G29 Steering Wheel", "Rs 19,999"),
        ("Gaming Chair DXRacer", "Rs 24,999"),
    ],
}

for category, items in products.items():
    pdf.set_font("Arial", "B", 13)
    pdf.set_fill_color(70, 130, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, f"  {category}", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=11)
    for name, price in items:
        pdf.cell(140, 8, f"  - {name}", border=0)
        pdf.cell(0, 8, price, ln=True)
    pdf.ln(3)

pdf.output("products.pdf")
print("PDF created — products.pdf!")