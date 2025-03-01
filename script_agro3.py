import os
import time
import requests
import threading
from datetime import datetime  # Добавляем для работы со временем
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Телеграм токен и список чат IDs из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = os.getenv("CHAT_IDS", "")
if CHAT_IDS:
    CHAT_IDS = CHAT_IDS.split(",")
else:
    CHAT_IDS = []

# Данные для трёх аккаунтов из переменных окружения
ACCOUNTS = [
    {"email": os.getenv("ACCOUNT1_EMAIL"), "password": os.getenv("ACCOUNT1_PASSWORD"), "clicked": False},
    {"email": os.getenv("ACCOUNT2_EMAIL"), "password": os.getenv("ACCOUNT2_PASSWORD"), "clicked": False},
    {"email": os.getenv("ACCOUNT3_EMAIL"), "password": os.getenv("ACCOUNT3_PASSWORD"), "clicked": False}
]

# Настройки браузера
options = Options()
options.add_argument("--headless")  # Убрать комментарий для фонового режима
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

found_button = False  # Флаг для завершения проверки после нахождения кнопки
vacancy_links = []  # Глобальный список вакансий

def send_telegram_message(message):
    print("📩 Отправка сообщения в Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in CHAT_IDS:  # Отправляем сообщение каждому ID в списке
        data = {"chat_id": chat_id, "text": message}
        requests.post(url, data=data)
    print("✅ Сообщение отправлено всем получателям!")

def update_vacancy_links():
    global vacancy_links
    while not all(account["clicked"] for account in ACCOUNTS):
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print("🔹 Обновляю список вакансий...")
        driver.get("https://agropraktika.eu/vacancies")
        time.sleep(1)
        
        vacancies = driver.find_elements(By.CLASS_NAME, "vacancy-item")
        new_links = [vacancy.find_element(By.TAG_NAME, "a").get_attribute("href") for vacancy in vacancies]
        
        if new_links != vacancy_links:
            vacancy_links = new_links
            print("🔹 Обновленный список вакансий:")
            for link in vacancy_links:
                print(link)
        
        driver.quit()
        time.sleep(0.5)  # Минимальная задержка перед обновлением списка

def login_and_check_vacancies(account):
    email = account["email"]
    password = account["password"]
    
    while not account["clicked"]:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print(f"🔹 Вхожу в аккаунт: {email}")
        driver.get("https://agropraktika.eu/login")
        time.sleep(2)
        
        try:
            email_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")
            email_input.send_keys(email)
            password_input.send_keys(password)
            password_input.submit()
            time.sleep(3)
        except Exception as e:
            print(f"❌ Ошибка входа в аккаунт {email}: {e}")
            driver.quit()
            return
        
        while not account["clicked"]:
            if not vacancy_links:
                time.sleep(0.1)
                continue
            
            for link in vacancy_links:
                if account["clicked"]:
                    break
                
                print(f"🔹 [{email}] Открываю вакансию: {link}")
                driver.get(link)
                time.sleep(1)
                
                try:
                    print(f"🔹 [{email}] Проверяю наличие кнопки 'Подать заявку'...")
                    button_block = driver.find_element(By.XPATH, "/html/body/main/div/div/div[3]/div[2]")
                    buttons = button_block.find_elements(By.TAG_NAME, "button") + button_block.find_elements(By.TAG_NAME, "a")
                    
                    for button in buttons:
                        if "подать заявку" in button.text.lower():
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Текущее время
                            print(f"✅ [{email}] Кнопка найдена на {link}! Нажимаю...")
                            button.click()
                            # Формируем понятное уведомление
                            message = (
                                f"Заявка подана!\n"
                                f"Время: {current_time}\n"
                                f"Аккаунт: {email}\n"
                                f"Вакансия: {link}"
                            )
                            send_telegram_message(message)
                            account["clicked"] = True
                            break
                except:
                    print(f"❌ [{email}] Кнопка НЕ найдена на {link}, проверяю снова...")
        
        driver.quit()
        time.sleep(0.1)  # Минимальная задержка перед повторной проверкой

def start_checking():
    threading.Thread(target=update_vacancy_links, daemon=True).start()  # Фоновый процесс обновления списка вакансий
    threads = []
    
    for account in ACCOUNTS:
        thread = threading.Thread(target=login_and_check_vacancies, args=(account,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print("✅ Проверка завершена!")

if __name__ == "__main__":
    start_checking()
