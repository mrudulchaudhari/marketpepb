from flask import Flask, render_template
from core import get_report_message
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    report = get_report_message()
    return render_template('index.html', report=report)


if __name__ == '__main__':
    app.run(debug=True)
