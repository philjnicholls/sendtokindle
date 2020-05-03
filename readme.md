# Send To Kindle
Sends an email to your kindle email address which contains a webpage for easy reading.

Very much a WIP and part of #100daysofcode

## Config
Rename .sendtokindle.rc.example to .sendtokindle.rc and fill in your details.

## Testing
    curl -d "url=https://realpython.com/python-testing/" http://localhost:5000
    
    curl -d "url=https://www.ladybirdeducation.co.uk/the-importance-of-fairy-tales-in-the-efl-classroom/" http://localhost:5000

## Webserver Config
### Apache Example
    WSGIScriptAlias /sendtokindle /some/path/to/sendtokindle/app.wsgi process-group=sendtokindle
    WSGIDaemonProcess sendtokindle python-home=/some/path/to/sendtokindle/venv python-path=/some/path/to/sendtokindle
    WSGIProcessGroup sendtokindle
    <Directory /some/path/to/sendtokindle>
            <Files app.wsgi>
                    Require all granted
            </Files>
    </Directory>
    
## Bookmarklet
    javascript:const Http = new XMLHttpRequest();Http.open("POST", "https://sendtokindle.philjnicholls.com/", true); Http.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");Http.send("url=" + window.location);