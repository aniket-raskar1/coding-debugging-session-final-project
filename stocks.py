from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# ===== Email Config =====
SENDER_EMAIL = "fakeloginpage13@gmail.com"
SENDER_PASSWORD = "facd uucd rqsd wtjy"  # Gmail App Password

CSV_FILE = "user_data.csv"

# ===== Email Function =====
def send_email(url, price, receiver_email):
    subject = "Amazon Price Alert!"
    body = f"Price dropped to ₹{price}!\nCheck the product here: {url}"

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

# ===== Scraper =====
def get_product_details(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")

    title = soup.find(id="productTitle")
    title_text = title.get_text(strip=True) if title else "N/A"

    price = None
    if soup.select_one("span.a-price-whole"):
        whole = soup.select_one("span.a-price-whole").get_text(strip=True)
        fraction = soup.select_one("span.a-price-fraction")
        price = whole + (fraction.get_text(strip=True) if fraction else "")

    img = soup.select_one("#imgTagWrapperId img")
    img_url = img["src"] if img else ""

    return {"title": title_text, "price": price, "image": img_url, "url": url}

# ===== Save User Data =====
def save_user_data(url, threshold, email):
    new_data = pd.DataFrame([[url, threshold, email]], columns=["URL", "Threshold", "Email"])
    if os.path.exists(CSV_FILE):
        new_data.to_csv(CSV_FILE, mode="a", header=False, index=False)
    else:
        new_data.to_csv(CSV_FILE, index=False)

# ===== Scheduler Task =====
def scheduled_task():
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE)
    for _, row in df.iterrows():
        url, threshold, email = row["URL"], int(row["Threshold"]), row["Email"]
        product = get_product_details(url)
        if product["price"]:
            cleaned_price = int(product["price"].replace(",", "").strip())
            if cleaned_price <= threshold:
                send_email(url, cleaned_price, email)

# Start background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, "interval", hours=24)  # checks daily
scheduler.start()

# ===== Routes =====
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/track", methods=["POST"])
def track():
    url = request.form["url"]
    threshold = int(request.form["threshold"])
    email = request.form["email"]

    save_user_data(url, threshold, email)
    product = get_product_details(url)

    # Send email immediately if price <= threshold
    if product["price"]:
        cleaned_price = int(product["price"].replace(",", "").strip())
        if cleaned_price <= threshold:
            send_email(url, cleaned_price, email)

    return render_template("index.html", product=product)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)  # use_reloader=False prevents signal errors
