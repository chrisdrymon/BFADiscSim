# BFADiscSim
Code that simulates World of Warcraft combat as performed by a Disc Priest in the Battle for Azeroth Expansion. It could assist a player in optimizing stats and gear choices.
# Web App
The code was integrated in to a Flask web app following the application factory format which allow for easy scalability. They were visualized with Dash.
View the web app at https://chrisdrymon.com/wowsim.
# Under the Hood
The app requires merging multiple overlapping timelines of events, finding the next event, creating new events at appropriate time stops, determining which events required further assessment, calculating the magnitude of spell hits, simulating randomness, and determining the next attack to be carried out based on those timelines.
