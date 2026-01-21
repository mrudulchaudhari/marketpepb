from flask import Flask, render_template
from core import get_report_message
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    report = get_report_message()
    now = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")
    return render_template('index.html', report=report, now=now)



if __name__ == '__main__':
    app.run(debug=True)
