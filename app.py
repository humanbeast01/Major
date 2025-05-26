import streamlit as st
import mysql.connector
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import os
import time

# --- SPLASH IMAGE ---
st.image("image.jpeg", use_column_width=True)
time.sleep(1)
st.empty()

# --- MYSQL CONNECTION ---
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="Mukul",
        password="Mukul@1234",  
        database="car_rental"
    )

# --- DISTANCE & MAP URL FUNCTIONS ---
def calculate_distance(start, end):
    geolocator = Nominatim(user_agent="car_rental_app")
    loc1 = geolocator.geocode(start)
    loc2 = geolocator.geocode(end)
    if loc1 and loc2:
        return geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
    return None

def generate_maps_link(start, end):
    return f"https://www.google.com/maps/dir/{start.replace(' ', '+')}/{end.replace(' ', '+')}"

# --- PDF GENERATION FUNCTION ---
def generate_invoice_pdf(car, customer_name, phone, address, start_location, destination, rent_date, return_date, rental_id, total_days, charges, distance_km, maps_url):
    file_name = f"Invoice_{rental_id}.pdf"
    c = canvas.Canvas(file_name)
    c.setFont("Helvetica", 14)
    c.drawString(100, 800, "Car Rental Invoice")
    c.line(100, 790, 400, 790)

    c.drawString(100, 760, f"Invoice ID: {rental_id}")
    c.drawString(100, 740, f"Customer: {customer_name}")
    c.drawString(100, 720, f"Phone: {phone}")
    c.drawString(100, 700, f"Address: {address}")
    c.drawString(100, 680, f"Start Location: {start_location}")
    c.drawString(100, 660, f"Destination: {destination}")
    c.drawString(100, 640, f"Car: {car}")
    c.drawString(100, 620, f"Rent Date: {rent_date}")
    c.drawString(100, 600, f"Return Date: {return_date}")
    c.drawString(100, 580, f"Total Days: {total_days}")
    c.drawString(100, 560, f"Charges: ₹{charges:.2f}")
    if distance_km:
        c.drawString(100, 540, f"Estimated Distance: {distance_km:.2f} km")
    c.drawString(100, 500, "Thank you for using our service!")
    c.save()
    return file_name

# --- MAIN APP ---
st.title("🚗 Car Rental System")
menu = st.sidebar.selectbox("Menu", ["Add Car", "View Available Cars", "Rent a Car", "View Rentals"])

# Add Car
if menu == "Add Car":
    st.header("➕ Add New Car")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT brand, model FROM cars")
    existing_cars = cursor.fetchall()
    existing_car_models = [f"{b} {m}" for b, m in existing_cars]
    car_model_option = st.selectbox("Choose Existing or Enter New Car Model", existing_car_models + ["Other"])
    if car_model_option == "Other":
        brand = st.text_input("Enter New Brand")
        model = st.text_input("Enter New Model")
    else:
        brand, model = car_model_option.split(' ', 1)


    if st.button("Add Car"):
        if not brand.strip() or not model.strip():
            st.error("Brand and model cannot be empty.")
        else:
            cursor.execute("INSERT INTO cars (brand, model) VALUES (%s, %s)", (brand.strip(), model.strip()))
            conn.commit()
            conn.close()
            st.success("✅ Car added successfully!")


# View Available Cars
elif menu == "View Available Cars":
    st.header("🚘 Available Cars")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, brand, model FROM cars WHERE available = TRUE")
    cars = cursor.fetchall()
    conn.close()

    if cars:
        for car in cars:
            st.write(f"ID: {car[0]}, Brand: {car[1]}, Model: {car[2]}")
    else:
        st.warning("No available cars.")

# Rent a Car
elif menu == "Rent a Car":
    st.header("📄 Rent a Car")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, brand, model FROM cars WHERE available = TRUE")
    cars = cursor.fetchall()

    if not cars:
        st.warning("No cars available for rent.")
        st.stop()

    car_dict = {f"{c[1]} {c[2]} (ID: {c[0]})": c for c in cars}
    selected_car = st.selectbox("Choose a Car", list(car_dict.keys()))
    customer_name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    address = st.text_area("Address")
    start_location = st.text_input("Starting Location")
    destination = st.text_input("Destination")
    return_date = st.date_input("Return Date")
    rate_per_day = st.number_input("Rate Per Day (₹)", min_value=500.0, value=500.0)

    if st.button("Confirm Rent"):
        car = car_dict[selected_car]
        car_id = car[0]
        brand_model = f"{car[1]} {car[2]}"
        rent_date = date.today()
        total_days = (return_date - rent_date).days
        if total_days < 0:
            st.error("Return date cannot be before rent date.")
            st.stop()
        elif total_days == 0:
            total_days = 1  # Treat same-day rental as 1-day rent

        charges = total_days * rate_per_day

        distance_km = calculate_distance(start_location, destination)
        maps_url = generate_maps_link(start_location, destination)

        cursor.execute("""
            INSERT INTO rentals (car_id, customer_name, phone, address, start_location, destination, rent_date, return_date, total_days, charges)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (car_id, customer_name, phone, address, start_location, destination, rent_date, return_date, total_days, charges))
        rental_id = cursor.lastrowid

        cursor.execute("UPDATE cars SET available = FALSE WHERE id = %s", (car_id,))
        conn.commit()
        conn.close()

        st.markdown(f"**Estimated Distance:** {distance_km:.2f} km" if distance_km else "Distance not found")
        st.markdown(f"[📍 View Route on Google Maps]({maps_url})")

        pdf_file = generate_invoice_pdf(brand_model, customer_name, phone, address, start_location, destination, rent_date, return_date, rental_id, total_days, charges, distance_km, maps_url)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Download Invoice", f, file_name=pdf_file)

        st.success(f"✅ Car rented to {customer_name} for ₹{charges:.2f}!")

        payment_link = f"https://www.instamojo.com/@yourshop/rental_payment_{rental_id}"
        st.markdown(f"[💳 Pay Now]({payment_link})", unsafe_allow_html=True)

# View Rentals
elif menu == "View Rentals":
    st.header("📚 Rental Records")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, c.brand, c.model, r.customer_name, r.phone, r.address, r.start_location, r.destination, r.rent_date, r.return_date, r.total_days, r.charges
        FROM rentals r 
        JOIN cars c ON r.car_id = c.id
    """)
    records = cursor.fetchall()
    conn.close()

    for record in records:
        st.write(f"🧾 ID: {record[0]}, Car: {record[1]} {record[2]}, Customer: {record[3]}, Phone: {record[4]}, Address: {record[5]}, Start: {record[6]}, Destination: {record[7]}, Rent Date: {record[8]}, Return Date: {record[9]}, Days: {record[10]}, Charges: ₹{record[11]}")
