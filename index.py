import pprint, smtplib, time 

pp = pprint.PrettyPrinter(indent=4)

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from seleniumrequests import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from selenium.webdriver.support import expected_conditions as EC

import yaml

with open("vondelbot.yaml", "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

class VondelGym:

    def __init__(self, user):
        self.name = user['name']
        self.email = user['email']
        self.username = user['username']
        self.password = user['password']
        self.appointments = user['appointments']

        for appointment in self.appointments: 
            appointment['day'] = appointment['day'].lower()
            appointment['training'] = appointment['training'].lower()
            appointment['time'] = appointment['time'].lower()

        self.bookings = []

        self.driver = webdriver.Firefox()
        self.driver.get("http://www.vondelgym.nl")
        assert "Vondelgym" in self.driver.title

        return None 

    def login(self):
        driver = self.driver

        login_button = driver.find_element_by_class_name('login_button')
        login_button.click()

        username = driver.find_element_by_id("f_email_")
        username.clear()
        username.send_keys(self.username)

        password = driver.find_element_by_id("f_password_")
        password.clear()
        password.send_keys(self.password)

        submit_button = driver.find_element_by_class_name('submit_buttons')
        submit_button.click()
        return

    def logout(self):
        driver = self.driver
        logout_button = driver.find_element_by_class_name('log_out')
        logout_button.click()
        return 

    def get_schedule(self):
        driver = self.driver 

        driver.get("https://vondelgym.nl/lesrooster-vondelgym-west")
        days = driver.find_elements_by_class_name("res_days")

        schedule = {}

        for idx, day in enumerate(days):
            day.click()
            activities = day.find_elements_by_class_name("res_activities")

            date_day = day.find_element_by_class_name("date_day").text.lower()
            date_dd = day.find_element_by_class_name("date_dd").text.lower()

            this_day = []

            for idx, activity in enumerate(activities):
                this_activity = {}

                reserve = activity.find_element_by_class_name("res_reserve")

                this_activity['name'] = activity.find_element_by_class_name("res_name").text.lower()
                this_activity['time'] = activity.find_element_by_class_name("res_time").text.lower()
                this_activity['status'] = reserve.find_element_by_class_name("available").text.lower()

                try:
                    this_activity['id_selector'] = reserve.find_element_by_link_text('Inschrijven').get_attribute("id")
                except:
                    this_activity['id_selector'] = None

                this_day.append(this_activity)
            
            schedule[date_day] = this_day

        self.schedule = schedule
        return 

    def book_appointments(self):
        driver = self.driver 
        schedule = self.schedule
        bookings = self.bookings

        for appointment in self.appointments:
            driver.find_element_by_partial_link_text(appointment['day'].upper()).click()
            schedule_for_day = schedule[appointment['day']]
            filtered_trainings = list(filter(lambda x: (appointment['training'] in x['name']), schedule_for_day))
            selected_training = next(training for training in filtered_trainings if appointment['time'] in training['time'])
            button = driver.find_element_by_id(selected_training['id_selector'])
            button.click()
            time.sleep(2)
            alert = Alert(driver)
            bookings.append(alert.text)
            alert.accept()

        return 

    def email_bookings(self):

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Here to serve you master'
        msg['From'] = 'Vondelbot <vondelbot@mjrc.nl>'
        msg['To'] = self.email

        html_bookings = "".join(["<ul>" + booking + "</ul>" for booking in self.bookings])
        text_bookings = "".join(["- " + booking + "\n" for booking in self.bookings])


        html = f"""
            <html>
                <head></head>
                <body>
                    <p>Hello {self.name},<br><br>
                        Here is the list of new VondelGym bookings:<br>
                        {html_bookings}
                        <br><br>
                        Always at your service,<br>
                        Vondelbot
                    </p>
                </body>
            </html>
        """

        text = f"""Hey {self.name},\n\nHere is the list of new VondelGym bookings: \n\n{text_bookings}\n\nAlways at your service,\nVondelbot"""

        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP('mail.mjrc.nl', 587) as server:
            server.starttls()
            server.login(config['smtp']['username'], config['smtp']['password'])
            server.send_message(msg)
            return

    def close(self): 
        driver = self.driver
        driver.close()
        return 


for user in config['users']:
    session = VondelGym(user)
    session.login()
    session.get_schedule()
    session.book_appointments()
    session.email_bookings()
    session.logout()
    session.close()

exit()
