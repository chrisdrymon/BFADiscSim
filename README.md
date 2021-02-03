# BFADiscSim
Code that simulates World of Warcraft combat as performed by a Disc Priest in the Battle for Azeroth Expansion. It could assist a player in optimizing stats and gear choices.
# Web App
discsim.py is stand-alone code while dashversion.py is fully ready to be integrated into a Flask web app following the application factory format which allows for easy scalability. Dash is the visualization framework that the web app utilizes.
View the web app in action at https://chrisdrymon.com/wowsim.
# Under the Hood
The app requires merging multiple overlapping timelines of events, finding the next event, creating new events at appropriate time stops, determining which events required further assessment, calculating the magnitude of spell hits, simulating randomness, and determining the next attack to be carried out based on those timelines.
