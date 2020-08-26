# Tinycardl

**_Tinycards downloader_**

Tinycardl downloads decks, deck groups and your pinned in CSV, along with the pictures.

🚧 This is a work in progress which will never be finished, but I hope it will be useful for some of you.

### Usage

Installation:

`python3.8 -m pip install --user tinycardl`

Basic usage, downloading decks or deck groups:

`tinycardl 3AbdmJDP NZHWAf`

To download you pinned decks, you need you JWT token.
Once logged in Tinycard with your Duolingo account, look for the cookie `jwt_token` in the Development Tools of your browser (press F12).  
- For Chrome it’s under **Application > Cookies > https://tinycards.duolingo.com > jwt_token > Value**  
- For Firefox it’s under **Storage > Cookies > https://tinycards.duolingo.com > jwt_token > Value**  

`JWT_TOKEN=myVery.l0ng.t0k3n tinycardl`

