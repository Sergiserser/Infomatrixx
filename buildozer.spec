[app]

title = StepPrep
package.name = stepprep
package.domain = org.osana

source.dir = .
source.include_exts = py,json,kv,png,jpg,jpeg,ttf
source.exclude_patterns = emergency_evidence/*,google_user_profile.json,__pycache__/*,.git/*,rescue app.py,Exsample.py

version = 0.1.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,plyer,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,RECORD_AUDIO,VIBRATE
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = False

[buildozer]

log_level = 2
warn_on_root = 1
