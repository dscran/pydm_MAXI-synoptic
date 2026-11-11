import os

# The tests never show a window, also when the desktop session sets a platform such as xcb.
# Qt reads this when the application is created, which happens after this file is imported.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
