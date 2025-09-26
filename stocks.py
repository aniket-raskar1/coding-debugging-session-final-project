import requests
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler

# ========== Email Config ==========
SENDER_EMAIL = "fakeloginpage13@gmail.com"
SENDER_PASSWORD = "facd uucd rqsd wtjy"   # use Gmail App Password, not your real password
RECEIVER_EMAIL = "fakeloginpage13@gmail.com"

def send_email(url, price):
    subject = "Amazon Price Alert!"
    body = f"Price dropped to ₹{price}!\nCheck the product here: {url}"

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    st.success("📧 Email sent!")

def get_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36",
    }
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")

    title = soup.find(id="productTitle")
    title_text = title.get_text(strip=True) if title else "N/A"

    price = None
    if soup.find(id="priceblock_ourprice"):
        price = soup.find(id="priceblock_ourprice").get_text(strip=True)
    elif soup.find(id="priceblock_dealprice"):
        price = soup.find(id="priceblock_dealprice").get_text(strip=True)
    elif soup.find(id="priceblock_saleprice"):
        price = soup.find(id="priceblock_saleprice").get_text(strip=True)
    elif soup.select_one("span.a-price-whole"):
        whole = soup.select_one("span.a-price-whole").get_text(strip=True)
        fraction = soup.select_one("span.a-price-fraction")
        price = whole + (fraction.get_text(strip=True) if fraction else "")

    if not price:
        return title_text, None

    digits = re.sub(r"\D", "", price)
    converted_price = int(digits) if digits else None
    return title_text, converted_price


# ========== Streamlit UI ==========
st.title("🛒 Amazon Price Tracker")
st.write("Enter an Amazon product link and get notified via email when the price drops below your threshold!")

url = st.text_input("Enter Amazon Product URL")
threshold = st.number_input("Enter threshold price (₹)", min_value=1, step=100)

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None

def scheduled_task():
    if not url.strip():
        return
    title, current_price = get_price(url)
    if current_price and current_price <= threshold:
        send_email(url, current_price)

if st.button("Start Tracking"):
    if not url.strip():
        st.error("Please enter a valid Amazon URL.")
    else:
        title, current_price = get_price(url)
        if current_price:
            st.write(f"**Product:** {title}")
            st.write(f"**Current Price:** ₹{current_price}")

            # Case 1: price already low enough → send immediately
            if current_price <= threshold:
                send_email(url, current_price)
            else:
                # Case 2: schedule daily check
                st.warning(f"❌ Current price ₹{current_price} > threshold ₹{threshold}. Scheduling daily check...")
                scheduler = BackgroundScheduler()
                scheduler.add_job(scheduled_task, "interval", days=1)
                scheduler.start()
                st.session_state.scheduler = scheduler
        else:
            st.error("❌ Could not fetch price. Amazon may be blocking the request.")
