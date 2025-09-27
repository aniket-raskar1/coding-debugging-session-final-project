
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import os

# ========== Email Config ==========
SENDER_EMAIL = "fakeloginpage13@gmail.com"
SENDER_PASSWORD = "facd uucd rqsd wtjy"   # use Gmail App Password


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

    st.success(f"📧 Email sent to {receiver_email}!")


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
    
    cleaned_price = price.replace(",", "").replace("₹", "").strip()

    try:
        converted_price = int(float(cleaned_price))
    except ValueError:
        converted_price = None
    return title_text, converted_price


# ========== CSV Helper ==========
CSV_FILE = "user_data.csv"

def save_user_data(url, threshold, email):
    new_data = pd.DataFrame([[url, threshold, email]],
                            columns=["URL", "Threshold", "Email"])
    if os.path.exists(CSV_FILE):
        new_data.to_csv(CSV_FILE, mode="a", header=False, index=False)
    else:
        new_data.to_csv(CSV_FILE, index=False)


def scheduled_task():
    if not os.path.exists(CSV_FILE):
        return
    
    df = pd.read_csv(CSV_FILE)
    for _, row in df.iterrows():
        url, threshold, email = row["URL"], row["Threshold"], row["Email"]
        title, current_price = get_price(url)
        if current_price and current_price <= int(threshold):
            send_email(url, current_price, email)


# ========== Streamlit UI ==========
st.title("🛒 Amazon Price Tracker")
st.write("Enter an Amazon product link and get notified via email when the price drops below your threshold!")

url = st.text_input("Enter Amazon Product URL")
threshold = st.number_input("Enter threshold price (₹)", min_value=1, step=100)
user_email = st.text_input("Enter your email for notification")

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None

if st.button("Start Tracking"):
    if not url.strip() or not user_email.strip():
        st.error("Please enter a valid Amazon URL and your email.")
    else:
        title, current_price = get_price(url)
        if current_price:
            st.write(f"**Product:** {title}")
            st.write(f"**Current Price:** ₹{current_price}")

            # Save user details to CSV
            save_user_data(url, threshold, user_email)

            if current_price <= threshold:
                send_email(url, current_price, user_email)
            else:
                st.warning(f"❌ Current price ₹{current_price} > threshold ₹{threshold}. Scheduling daily check...")
                scheduler = BackgroundScheduler()
                scheduler.add_job(scheduled_task, "interval", days=1)
                scheduler.start()
                st.session_state.scheduler = scheduler
        else:
            st.error("❌ Could not fetch price. Amazon may be blocking the request.")

