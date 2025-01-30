from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from . import db_requests
from .logger_singleton import LoggerSingleton
import os

app = Flask(__name__)
app.secret_key = 'db40b07f5d0de1fedbffa26e6a610f26ec328a8e8c6f857faea5f84a1b79c838'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db_worker = db_requests.DbWork()
logger = LoggerSingleton().get_logger()


@app.route('/')
def home():
    return redirect('/auth', 301)


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_id = db_worker.check_password(username, password)
        logger.debug(f"us_id = {user_id}")
        if user_id == -1:
            error = "Password or username is incorrect"
        elif user_id == -5:
            error = "Server error"
        else:
            session['user_id'] = user_id
            return redirect('/main_page', 301)
    return render_template("auth.html", error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        contact = request.form.get('contact')
        confirm_password = request.form['confirm_password']

        if not contact:
            contact = "No contact information"

        if password != confirm_password:
            error = "Passwords don't match"
        else:
            user_id = db_worker.register_user(username, password, contact)
            if user_id == -1:
                error = "Username is already registered"
            elif user_id == -5:
                error = "Server error"
            else:
                session['user_id'] = user_id
                return redirect('/main_page', 301)
    return render_template("registration.html", error=error)


@app.route("/main_page", methods=['GET', 'POST'])
def main_page():
    category = request.form.get('sort-category')
    weight = request.form.get('sort-weight')
    logger.debug(f"category = {category}, weight = {weight}")
    res = db_worker.get_lots()
    logger.debug(f"orders: {res}")
    orders = []
    for lot_id in res:
        to_add = {}
        if category != "all" and category != None:
            if category != res[lot_id]['category']:
                continue
        if weight != "all" and weight != None:
            logger.error(f"weight = {weight}, lot = {res[lot_id]['weight']}")
            if weight == 1 and float(res[lot_id]['weight']) > 1:
                continue
            elif weight == 2 and not (1 < float(res[lot_id]['weight']) < 5):
                continue
            elif weight == 3 and  float(res[lot_id]['weight']) < 5:
                continue
        '''
        <option value="1">Light(&lt; 1 kg)</option>
        <option value="2">Middle (1–5 kg)</option>
        <option value="3">Hard (&gt; 5 kg)</option>
        '''
        to_add["id"] = lot_id
        to_add["description"] = res[lot_id]["description"]
        to_add["category"] = res[lot_id]["category"]
        to_add["weight"] = res[lot_id]["weight"]
        to_add["images"] = []
        for image_id in res[lot_id]["images"]:
            to_add["images"].append(res[lot_id]["images"][image_id])
        author_info = db_worker.get_user(res[lot_id]["author_id"])
        to_add["name"] = author_info["name"]
        to_add["contact"] = author_info["contact"]
        orders.append(to_add)
    logger.debug(f"OTHERSERWASRSERD: {orders}")
    user = db_worker.get_user(session['user_id'])
    tp = render_template("main_page.html", user=user, orders=orders)
    return tp


@app.route("/profile")
def profile():
    res = db_worker.get_lots(session['user_id'])
    logger.debug(f"orders: {res}")
    orders = []
    for lot_id in res:
        to_add = {}
        to_add["id"] = res[lot_id]["id"]
        to_add["description"] = res[lot_id]["description"]
        to_add["category"] = res[lot_id]["category"]
        to_add["weight"] = res[lot_id]["weight"]
        to_add["images"] = []
        to_add["owner"] = 1
        for image_id in res[lot_id]["images"]:
            to_add["images"].append(res[lot_id]["images"][image_id])
        author_info = db_worker.get_user(res[lot_id]["author_id"])
        to_add["name"] = author_info["name"]
        to_add["contact"] = author_info["contact"]
        orders.append(to_add)

    user = db_worker.get_user(session['user_id'])
    user["owner"] = 1
    return render_template("profile.html", orders=orders, user=user)


@app.route("/upload_avatar", methods=['GET', 'POST'])
def upload_avatar():
    logger.debug(f"imgfile = {request.files}")
    if 'avatar' not in request.files:
        return redirect(request.url)
    file = request.files['avatar']
    if file:
        res = db_worker.give_img_last_id()
        new_name = str(res + 1) + "." + file.filename.split(".")[-1]
        with open(os.path.join("app", app.config['UPLOAD_FOLDER'], new_name), "wb") as fh:
            file.save(os.path.join("app", app.config['UPLOAD_FOLDER'], new_name))
        logger.debug(f"new_name = {new_name}")
        db_worker.add_avatar(session["user_id"], new_name)
        return redirect('/profile')
    return 500


@app.route("/new_order", methods=['GET', 'POST'])
def new_order():
    if request.method == 'POST':
        description = request.form['description']
        category = int(request.form['category'])  # 1-package or 2-envelope
        weight = float(request.form['weight'])
        logger.debug(f"description = {description}, category = {category}, weight = {weight}")
        lot_id = db_worker.add_lot_by_user(session['user_id'], description, category, weight)
        files = request.files.getlist("photos[]")
        logger.debug(f"files = {files}")
        for file in files:
            res = db_worker.give_img_last_id()
            logger.info(f"res = {res}")
            new_name = str(res + 1) + "." + file.filename.split(".")[-1]
            with open(os.path.join("app", app.config['UPLOAD_FOLDER'], new_name), "wb") as fh:
                file.save(os.path.join("app", app.config['UPLOAD_FOLDER'], new_name))
            logger.debug(f"new_name = {new_name}")
            db_worker.add_img_to_lot(lot_id, new_name)
        logger.debug("redirect to main page")
    return render_template("new_order.html")


@app.route("/delete_lot/<lot_id>")
def delete_lot(lot_id):
    db_worker.disable_lot(lot_id)
    return redirect("/profile", 301)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
