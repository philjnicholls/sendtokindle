# Send To Kindle
Sends an email to your kindle email address which contains a webpage for easy reading.

Very much a WIP and part of #100daysofcode

## Config
Rename .sendtokindle.rc.example to .sendtokindle.rc and fill in your details.

## Testing
    curl -d "token=<user api token>" -d "url=https://realpython.com/python-testing/" http://localhost:5000
    
    curl -d "token=<user api token>" -d "url=https://www.ladybirdeducation.co.uk/the-importance-of-fairy-tales-in-the-efl-classroom/" http://localhost:5000

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
    
 ### systemd
    vim /lib/systemd/system/sendtokindle-queue.service
 
    [Unit]
    Description=Sendtokindle rq worker
    After=network.target
    
    [Service]
    User=someuser
    WorkingDirectory=/path/to/app
    ExecStart=/path/to/venv/bin/python worker.py
    Restart=always
    
    [Install]
    WantedBy=multi-user.target