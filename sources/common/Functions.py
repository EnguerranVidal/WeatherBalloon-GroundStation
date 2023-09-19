######################## IMPORTS ########################
import json
import os
import folium
import geocoder
import requests
import pandas as pd

# ------------------- PyQt Modules -------------------- #
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# --------------------- Sources ----------------------- #
from sources.common.FileHandling import loadSettings, saveSettings, nameGiving
from sources.common.Widgets import FlatButton, SearchBar


######################## CLASSES ########################

def getTextHeight(fontSize):
    font = QFont()
    font.setPointSize(fontSize)
    fontMetrics = QFontMetrics(font)
    textHeight = fontMetrics.height()
    return textHeight


def isInternetAvailable(url="http://www.google.com", timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        pass
    return False
