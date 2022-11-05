from flask import redirect, session
from functools import wraps


from cs50 import SQL


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///blazepc.db")

def login_required(f):
    # From the CS50's Problem set 9 https://cs50.harvard.edu/x/2022/psets/9/finance/
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def nosession(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id"):
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def officeronly(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id"):
            officers = db.execute("SELECT * FROM officers WHERE user_id = ?", session.get("user_id"))
            if len(officers) != 1:
                return redirect("/")
        else:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def specsdict(specsdb):
     # I need to process the data I inserted into the specs value
    specs = {}
    for spec in specsdb.rsplit(","):
        # Reused the code from the source code of fileuploads from flask
        if spec != " ": # For trowing off the last empty space
            specs[spec.rsplit("=")[0].strip()] = spec.rsplit("=")[1].strip()
    return specs