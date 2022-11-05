import os

from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from cs50 import SQL

from helpers import login_required, nosession, officeronly, specsdict

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_COOKIE_NAME"] = "SESSION"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# For image uploads https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/
UPLOAD_FOLDER = "static/prodimgs"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    # Source of code used https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///blazepc.db")


# Store -------------------------------------------------------------------

@app.route("/")
def items():
    return render_template("items.html")

@app.route("/search", methods=["GET"])
def search():
    if request.args.get("q"):
        items = db.execute("SELECT * FROM items WHERE name LIKE ?", "%" + request.args.get("q") + "%")
    else:
        items = items = db.execute("SELECT * FROM items")

    return render_template("search.html", items=items)

@app.route("/item", methods=["GET", "POST"])
def item():
    if request.args.get("id") and request.args.get("id").isdigit():
        item = db.execute("SELECT * FROM items WHERE id = ?", request.args.get("id"))

        if not item:
            return redirect("/")

        item = item[0]

        specs = specsdict(item["specs"])

        return render_template("item.html", item=item, specs=specs)
    else:
        return redirect("/")


# https://cs50.harvard.edu/x/2022/notes/9/#store-shows The source of the code for the cart
@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():

    # Ensure cart exists
    if "cart" not in session:
        session["cart"] = []

    # POST
    if request.method == "POST":
        id = request.form.get("id")
        if id:
            session["cart"].append(id)
        return redirect("/cart")

    # GET
    items = db.execute("SELECT * FROM items WHERE id IN (?)", session["cart"])
    totalprice = 0
    if not items:
        items = None
    else:
        uniques = set(session["cart"])
        for id in uniques:
            session[str(id)] = session["cart"].count(str(id))
            price = db.execute("SELECT price FROM items WHERE id = (?)", id)
            price = price[0]["price"]
            totalprice += session[str(id)] * price

    return render_template("cart.html", items=items, totalprice=totalprice)

@app.route("/cart/quantity", methods=["POST"])
@login_required
def cartquantity():
    if request.method =="POST":
        if not request.form.get("itemid") or not request.form.get("itemid").isdigit():
            return redirect("/cart")
        elif not request.form.get("button"):
            return redirect("/cart")

        id = request.form.get("itemid")
        button = request.form.get("button")

        if button == "+":
            session["cart"].append(id)
            return redirect("/cart")
        elif button == "-":
            session["cart"].remove(id)
            return redirect("/cart")
        else:
            return redirect("/cart")
    else:
        return redirect("/cart")


# End Store ---------------------------------------------------------------



# Accounts ----------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
@nosession
def register():
    if request.method == "POST":
        # Check input
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return redirect("register?error=Invalid Inputs")

        # Check for username in db
        name = request.form.get("username")
        users = db.execute("SELECT * FROM USERS WHERE username LIKE ?", name)

        # Check if in use, if not, check for passwords match
        if len(users) > 0:
            return redirect("register?error=Username already in use")
        elif request.form.get("password") != request.form.get("confirmation"):
            return redirect("register?error=Passwords didn't match")

        # Generate an hash from the password
        password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # Add user and hash to db
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", name, password)

        # Select the newly created user
        user = db.execute("SELECT * FROM users WHERE username = ?", name)

        # Remember which user has logged in, and his username
        session["user_id"] = user[0]["id"]
        session["username"] = user[0]["username"]

        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
@nosession
def login():
    if request.method == "POST":
        # Check input
        if not request.form.get("username") or not request.form.get("password"):
            return redirect("login?error=Invalid Inputs")

        # Save input for ease of use
        name = request.form.get("username")
        password = request.form.get("password")

        # Retrieve user
        user = db.execute("SELECT * FROM users WHERE username = ?", name)

        # Check for user
        if len(user) == 1:
            # Check password
            if check_password_hash(user[0]["hash"], password):
                # Session start
                session["user_id"] = user[0]["id"]
                session["username"] = user[0]["username"]
                return redirect("/")
            else:
                return redirect("login?error=Wrong password")
        else:
            return redirect("login?error=Account doesn't exist")
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():

    # Forget session
    session.clear()

    return redirect("/")

@app.route("/account")
@login_required
def account():
    return render_template("account.html")

# End Accounts ------------------------------------------------------------



# Office ------------------------------------------------------------------

@app.route("/backoffice", methods=["GET","POST"])
@officeronly
def backoffice():
    # This decides with what category we're working with, for adding an item or adding a spec
    catspecs = []
    if request.args.get("itemcat") and request.args.get("itemcat").isdigit():
        catspecs = db.execute("SELECT * FROM specs WHERE category_id = ?", request.args.get("itemcat"))
        if not catspecs:
            return redirect("/backoffice")

    # This is used to display current tables entries
    brands = db.execute("SELECT * FROM brands")
    categories = db.execute("SELECT * FROM categories")
    specs = db.execute("SELECT * FROM specs")

    return render_template("backoffice.html", brands=brands, categories=categories, specs=specs, catspecs=catspecs)



@app.route("/backoffice/brands", methods=["GET", "POST"])
@officeronly
def officebrands():
    if request.method == "POST":
        # Check for input
        if  not request.form.get("newbrand"):
            return redirect("/backoffice?error=No Brand")

        # Add Value
        db.execute("INSERT INTO brands (name) VALUES (?)", request.form.get("newbrand"))
    else:
        # Used to Delete Values
        if not request.args.get("id") or not request.args.get("id").isdigit():
            return redirect("/backoffice?error=No brand selected")
        db.execute("DELETE FROM brands WHERE id = ?", request.args.get("id"))

    return redirect("/backoffice")


@app.route("/backoffice/categories", methods=["GET", "POST"])
@officeronly
def officecategories():
    if request.method == "POST":
        # Check for input
        if  not request.form.get("newcategory"):
            return redirect("/backoffice?error=No Category")

        # Add Value
        db.execute("INSERT INTO categories (name) VALUES (?)", request.form.get("newcategory"))
    else:
        # Used to Delete Values
        if not request.args.get("id") or not request.args.get("id").isdigit():
            return redirect("/backoffice?error=No category selected")
        db.execute("DELETE FROM categories WHERE id = ?", request.args.get("id"))

    return redirect("/backoffice")


@app.route("/backoffice/specs", methods=["GET", "POST"])
@officeronly
def officespecs():
    if request.method == "POST":
        # Check for input
        if  not request.form.get("newspec") or not request.form.get("catid") or not request.form.get("catid").isdigit():
            return redirect("/backoffice?error=No Spec")

        # Add Value
        db.execute("INSERT INTO specs (name,category_id) VALUES (?,?)", request.form.get("newspec"), request.form.get("catid"))
        # This url_for makes it so I keep editing the same category of specs
        return redirect(url_for("backoffice", itemcat=request.form.get("catid")))
    else:
        # Used to Delete Values
        if not request.args.get("id") or not request.args.get("id").isdigit():
            return redirect("/backoffice?error=No spec selected")
        db.execute("DELETE FROM specs WHERE id = ?", request.args.get("id"))
        # This url_for makes it so I keep editing the same category of specs
        return redirect(url_for("backoffice", itemcat=request.args.get("catid")))



@app.route("/backoffice/items", methods=["GET", "POST"])
@officeronly
def officeitems():
    if request.method == "POST":
        # Checking for inputs
        if not request.form.get("name") or not request.form.get("description"):
            return redirect("/backoffice?error=Empty Inputs")

        # For easier check, store most of the fields in this array
        formnums = [ "price", "stock", "brand", "category"]

        for num in formnums:
            if not request.form.get(num) or not request.form.get(num).isdigit():
                return redirect("/backoffice?error=Empty Inputs/Invalid " + num)

        # Read the specs available to the current category
        specs = db.execute("SELECT * FROM specs WHERE category_id = ?", request.form.get("category"))

        # This will be the info I save into the db
        allspecs = ""

        for spec in specs:
            if not request.form.get("spec"+str(spec["id"])):  # Check for the specs available on the form
                return redirect("/backoffice?error=Wrong Specs")
            else:
                allspecs = allspecs + request.form.get("spec"+str(spec["id"])) + ", "
                # If everything goes right, I'll write the specs values into the allspecs variable, separating each value with a comma


        # If all inputs are within parameters, add an item to db

        db.execute("""
        INSERT INTO
        items(name,price,stock,description,specs,category_id,brands_id)
        VALUES (?,?,?,?,?,?,?)""",
        request.form.get("name"),
        request.form.get("price"),
        request.form.get("stock"),
        request.form.get("description"),
        allspecs,
        request.form.get("category"),
        request.form.get("brand")
        )


    return redirect("/backoffice")

@app.route("/backoffice/images", methods=["GET", "POST"])
@officeronly
def officeimages():
    # Source of code used https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/

    if request.method == "POST":
        if not request.form.get("itemid") or not request.form.get("itemid").isdigit():
            return redirect("/backoffice/images?error=invalid inputs")

        # Iterate through the possible image files and if they exist save them to the server's filesystem
        images = {'file1','file2','file3'}
        for image in images:
            if image in request.files:
                file = request.files[image]
                if allowed_file(file.filename):
                    filename = secure_filename(str(request.form.get("itemid")) + "-img" + image.rsplit('e')[1] + ".png")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if request.form.get("itemid") and request.form.get("itemname"):
            return redirect(url_for("officeimages", itemid=request.form.get("itemid"), itemname=request.form.get("itemname")))
        else:
            return redirect("/backoffice/images")

    else:
        items = db.execute("SELECT * FROM items")

        if request.args.get("itemid") and request.args.get("itemname"):
             return render_template("officeimages.html", items=items, itemid=request.args.get("itemid"), itemname=request.args.get("itemname"))

        return render_template("officeimages.html", items=items)

@app.route("/backoffice/images/delete", methods=["POST"])
@officeronly
def officeimagesdelete():
    if request.method == "POST":
        if not request.form.get("itemid") or not request.form.get("itemid").isdigit():
            return redirect("/backoffice/images?error=invalid inputs")
        elif not request.form.get("imagenum") or not request.form.get("imagenum").isdigit():
            return redirect("/backoffice/images?error=invalid inputs")


        item = request.form.get("itemid")
        image = request.form.get("imagenum")


        if int(image) > 0 and int(image) < 4:
            filename = secure_filename(str(item) + "-img" + str(image) + ".png")
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], filename)): # https://stackoverflow.com/questions/82831/how-do-i-check-whether-a-file-exists-without-exceptions
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename)) # https://stackoverflow.com/questions/6996603/how-do-i-delete-a-file-or-folder-in-python


        if request.form.get("itemid") and request.form.get("itemname"):
            return redirect(url_for("officeimages", itemid=request.form.get("itemid"), itemname=request.form.get("itemname")))
        else:
            return redirect("/backoffice/images")
    else:
        return redirect("/backoffice/images")

@app.route("/backoffice/deleteitems", methods=["GET","POST"])
@officeronly
def officeitemsdelete():
    if request.method == "POST":
        if not request.form.get("itemid") or not request.form.get("itemid").isdigit():
            return redirect("/backoffice/images?error=invalid inputs")

        item = request.form.get("itemid")

        db.execute("DELETE FROM items WHERE id = ?", item)

        for i in range(1,4,1):
            filename = secure_filename(str(item) + "-img" + str(i) + ".png")
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))


        return redirect(url_for("officeitemsdelete", error="item deleted"))
    else:
        items = db.execute("SELECT * FROM items")

        return render_template("officeitemdelete.html", items=items)


@app.route("/backoffice/pricestock", methods=["GET","POST"])
@officeronly
def officepricestock():
    if request.method == "POST":
        if not request.form.get("itemid") or not request.form.get("itemid").isdigit():
            return redirect("/backoffice/pricestock?error=wrong itemid")
        elif not request.form.get("stock") or not request.form.get("stock").isdigit():
            return redirect("/backoffice/pricestock?error=invalid stock number")
        elif not request.form.get("price") or not request.form.get("price").isdigit():
            return redirect("/backoffice/pricestock?error=invalid price number")
        elif int(request.form.get("price")) < 0 or int(request.form.get("stock")) < 0:
            return redirect("/backoffice/pricestock?error=invalid numbers")

        id = request.form.get("itemid")
        price = request.form.get("price")
        stock = request.form.get("stock")

        db.execute("""
        UPDATE items
        SET price = ?, stock = ?
        WHERE id = ?""",
        price,
        stock,
        id)

        return redirect(url_for("officepricestock",itemid=id))
    else:
        current = None
        if request.args.get("itemid") and request.args.get("itemid").isdigit():
            current = db.execute("SELECT * FROM items WHERE id = ?", request.args.get("itemid"))
            if not current:
                return redirect("/backoffice/pricestock")
            current = current[0]

        items = db.execute("SELECT * FROM items")

        return render_template("officepricestock.html", items=items, current=current)





# End Office --------------------------------------------------------------


