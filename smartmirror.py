#!/usr/bin/python3

from __future__ import print_function
from Tkinter import *
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from PIL import Image, ImageTk
import datetime
import json
import locale
import time
import locale
import threading
import feedparser
import traceback
import requests
import dateutil.parser

from contextlib import contextmanager

ui_locale = 'de_CH.UTF-8'
news_country = 'CH'
time_format = 12
date_format = "%b %d, %Y"
weather_api_token = '33e763a812916aecbb004eb5fd263ed2'
weather_lang = 'de'
weather_unit = 'auto'
latitude = 47.3666700
longitude = 8.5500000
xlarge_text_size = 94
large_text_size = 48
medium_text_size = 28
small_text_size = 18
LOCALE_LOCK = threading.Lock()

# These pictures are used to display the weather on the mirror
icon_lookup = {
    'clear-day': "pics/Sun.png",  # clear sky day
    'wind': "pics/Wind.png",   #wind
    'cloudy': "pics/Cloud.png",  # cloudy day
    'partly-cloudy-day': "pics/PartlySunny.png",  # partly cloudy day
    'rain': "pics/Rain.png",  # rain day
    'snow': "pics/Snow.png",  # snow day
    'snow-thin': "pics/Snow.png",  # sleet day
    'fog': "pics/Haze.png",  # fog day
    'clear-night': "pics/Moon.png",  # clear sky night
    'partly-cloudy-night': "pics/PartlyMoon.png",  # scattered clouds night
    'thunderstorm': "pics/Storm.png",  # thunderstorm
    'tornado': "pics/Tornado.png",    # tornado
    'hail': "pics/Hail.png"  # hail
}

@contextmanager
def setlocale(name): # thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


class Calendar(Frame):
    """
    This Class is used to log on to Google and get the events from Google calendar.
    """

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events'
        self.calendarLabel = Label(self, text=self.title, font=('Arial', medium_text_size), fg='white', bg='black')
        self.calendarLabel.pack(side=TOP, anchor=E)
        self.calenderEventContainer = Frame(self, bg='black')
        self.calenderEventContainer.pack(side=TOP, anchor=E)
        self.get_event()

    def get_event(self):

        # Authentication for Google Account
        save_output = list()
        SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('calendar', 'v3', http=creds.authorize(Http()))

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        # Changes time format
        for event in events:
            start = event['start'].get('dateTime')
            cut_time = start[:19]
            save_time = datetime.datetime.strptime(cut_time, '%Y-%m-%dT%H:%M:%S')  # Converts string into a date object
            new_time = datetime.datetime.strftime(save_time, '%d %b %H:%M %Y')  # Converts object into a string
            event_of_name = event['summary']
            output_event = event_of_name + ' ' + new_time
            save_output.append(output_event)

        for widget in self.calenderEventContainer.winfo_children():
            widget.destroy()

        for show_events in save_output:
            calender_event = Event(self.calenderEventContainer, event_name=show_events)
            calender_event.pack(side=TOP, anchor=E)

        self.after(60000, self.get_event)


class Event(Frame):
    """
    This Class displays the appointments on the mirror
    """

    def __init__(self, parent, event_name=None):
        Frame.__init__(self, parent, bg='black')
        self.eventName = event_name
        self.eventNameLabel = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLabel.pack(side=TOP, anchor=E)


class News(Frame):
    """
    This class gets all the news information on the main page from 20 Minutes and displays it on the mirror.
    """
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'News'
        self.newsLabel = Label(self, text=self.title, font=('Arial', medium_text_size), fg='white', bg='black')
        self.newsLabel.pack(side=TOP, anchor=W)
        self.headlinecontainer = Frame(self, bg='black')
        self.headlinecontainer.pack(side=TOP)
        self.get_headline()

    # Gets news from 20 Minuten and using the feedparser module, parses the title of the news that we need.
    def get_headline(self):
        for widget in self.headlinecontainer.winfo_children():
            widget.destroy()

        url_headline = 'https://api.20min.ch/rss/view/1'
        feed = feedparser.parse(url_headline)

        for post in feed.entries[0:5]:
            headlines = NewsHeadLines(self.headlinecontainer, post.title)
            headlines.pack(side=TOP, anchor=W)

        self.after(600000, self.get_headline)


class NewsHeadLines(Frame):
    """
    This Class is used to display a picture next to the news
    """
    def __init__(self, parent, event_name=None):
        Frame.__init__(self, parent, bg='black')

        image = Image.open('pics/rss.png')
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.picLabel = Label(self, bg='black', image=photo)
        self.picLabel.image = photo
        self.picLabel.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLabel = Label(self, text=self.eventName, font=('Arial', small_text_size), fg='white', bg='black')
        self.eventNameLabel.pack(side=LEFT, anchor=N)


class Weather(Frame):
    """
    This class gets weather data from DarkSkyNet using the REST API Interface and displays it on the mirror
    """

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.temp = ''
        self.forecast = ''
        self.location = ''
        self.now = ''
        self.icon = ''
        self.degreeFrame = Frame(self, bg='black')
        self.degreeFrame.pack(side=TOP, anchor=W)
        self.tempLabel = Label(self.degreeFrame, font=('Arial', xlarge_text_size), fg='white', bg='black')
        self.tempLabel.pack(side=LEFT, anchor=N)
        self.iconLabel = Label(self.degreeFrame, bg='black')
        self.iconLabel.pack(side=LEFT, anchor=N, padx=20)
        self.nowLabel = Label(self, font=('Arial', medium_text_size), fg='white', bg='black')
        self.nowLabel.pack(side=TOP, anchor=W)
        self.forecastLabel = Label(self, font=('Arial', small_text_size), fg="white", bg="black")
        self.forecastLabel.pack(side=TOP, anchor=W)
        self.locationLabel = Label(self, font=('Arial', small_text_size), fg="white", bg="black")
        self.locationLabel.pack(side=TOP, anchor=W)
        self.get_weatherinfo()


    # Gets weather infromation and uses the correct weather picture to display on the mirror.
    def get_weatherinfo(self):

        location_two = ''
        req_weather = 'https://api.darksky.net/forecast/%s/%s,%s?lang=%s&units=%s' % (weather_api_token, latitude,
                                                                                      longitude, weather_lang,
                                                                                      weather_unit)

        r = requests.get(req_weather)
        weather_object = json.loads(r.text)

        degree_sign = u'\N{DEGREE SIGN}'
        temp_two = "%s%s" % (str(int(weather_object['currently']['temperature'])), degree_sign)
        now_two = weather_object['currently']['summary']
        forecast_two = weather_object["hourly"]["summary"]

        icon_id = weather_object['currently']['icon']
        icon2 = None

        if icon_id in icon_lookup:
            icon2 = icon_lookup[icon_id]

        if icon2 is not None:
            if self.icon != icon2:
                self.icon = icon2
                image = Image.open(icon2)
                image = image.resize((100, 100), Image.ANTIALIAS)
                image = image.convert('RGB')
                photo = ImageTk.PhotoImage(image)

                self.iconLabel.config(image=photo)
                self.iconLabel.image = photo
        else:
            self.iconLabel.config(image='')

        if self.now != now_two:
            self.now = now_two
            self.nowLabel.config(text=now_two)
        if self.forecast != forecast_two:
            self.forecast = forecast_two
            self.forecastLabel.config(text=forecast_two)
        if self.temp != temp_two:
            self.temp = temp_two
            self.tempLabel.config(text=temp_two)
        if self.location != location_two:
            if location_two == ", ":
                self.location = "Cannot Pinpoint Location"
                self.locationLabel.config(text="Cannot Pinpoint Location")
            else:
                self.location = location_two
                self.locationLabel.config(text=location_two)

        self.after(600000, self.get_weatherinfo)


class Time(Frame):
    """
    This Class displays the local time on the mirror
    """
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        #Time Label
        self.time = ''
        self.timeLabel = Label(self, font=('Arial', large_text_size), fg='white', bg='black')
        self.timeLabel.pack(side=TOP, anchor=E)
        #Week Label
        self.day = ''
        self.dayLabel = Label(self, text=self.day, font=('Arial', small_text_size), fg='white', bg='black')
        self.dayLabel.pack(side=TOP, anchor=E)
        #Date
        self.date = ''
        self.dateLabel = Label(self, text=self.date, font=('Arial', small_text_size), fg='white', bg='black')
        self.dateLabel.pack(side=TOP, anchor=E)
        self.exec_time()

    # Gets local time from the system
    def exec_time(self):
        with setlocale(ui_locale):
            if time_format > 12:
                update_time = time.strftime('%I:%M %p')
            else:
                update_time = time.strftime('%H:%M')

            show_day = time.strftime('%A')
            show_date = time.strftime(date_format)

            if update_time != self.time:
                self.time = update_time
                self.timeLabel.config(text=update_time)
            if show_day != self.day:
                self.day = show_day
                self.dayLabel.config(text=show_day)
            if show_date != self.date:
                self.date = show_date
                self.dateLabel.config(text=show_date)
            self.timeLabel.after(200, self.exec_time)


class GUI:
    """
    This class is used to display all the information in a window and executes all the above methods to run the
    program.
    """
    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background='black')
        self.topFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.bottomFrame = Frame(self.tk, background='black')
        self.bottomFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
        self.state = False
        self.tk.bind('<Return>', self.fullscreen)
        self.tk.bind('<Escape>', self.exit_Fullscreen)
        #Time
        self.time = Time(self.topFrame)
        self.time.pack(side=RIGHT, anchor=N, padx=100, pady=60)
        #Calendar
        self.calender = Calendar(self.bottomFrame)
        self.calender.pack(side=RIGHT, anchor=S, padx=100, pady=60)
        #RSS
        self.news = News(self.bottomFrame)
        self.news.pack(side=LEFT, anchor=S, padx=100, pady=60)
        #Weather
        self.weather = Weather(self.topFrame)
        self.weather.pack(side=LEFT, anchor=N, padx=100, pady=60)

    def fullscreen(self, event=None):
        self.state = not self.state
        self.tk.attributes('-fullscreen', self.state)
        return 'break'


    def exit_Fullscreen(self, event=None):
        self.state = False
        self.tk.attributes('-fullscreen', False)
        return 'break'


def main():
    window = GUI()
    window.tk.mainloop()


if __name__ == main():
    main()