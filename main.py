from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from form import LoginForm, Register, CommentForm
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

app = Flask(__name__)

app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

Bootstrap(app)
ckeditor = CKEditor(app)

# db connect
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///cafe.db"
db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    all_cafes = relationship("Cafe", back_populates="provider")
    all_ratings = relationship("Rating", back_populates="rating_author")
    all_comments = relationship("Comment", back_populates="comment_author")


class Cafe(db.Model):
    __tablename__ = "cafes"
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    provider = relationship("User", back_populates="all_cafes")
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    address = db.Column(db.String(250), nullable=False)
    wifi = db.Column(db.String, nullable=False)
    dessert = db.Column(db.String, nullable=False)
    meal = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    power = db.Column(db.String, nullable=False)
    official_website = db.Column(db.String(250), nullable=False)
    google_map = db.Column(db.String(250), nullable=True)
    review = db.Column(db.Boolean, default=False, nullable=False)
    business_hours = relationship("BusinessHours", back_populates="parent_cafe")
    cafe_rating = relationship("Rating", back_populates="parent_cafe")
    avg_rating = db.Column(db.String, default="None", nullable=False)
    comments = relationship("Comment", back_populates="comment_cafe")


class BusinessHours(db.Model):
    __tablename__ = "business_hours"
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafes.id"))
    parent_cafe = relationship("Cafe", back_populates="business_hours")
    mon = db.Column(db.String, nullable=False)
    tue = db.Column(db.String, nullable=False)
    wed = db.Column(db.String, nullable=False)
    thu = db.Column(db.String, nullable=False)
    fri = db.Column(db.String, nullable=False)
    sat = db.Column(db.String, nullable=False)
    sun = db.Column(db.String, nullable=False)


class Rating(db.Model):
    __tablename__ = "rating"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    rating_author = relationship("User", back_populates="all_ratings")
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafes.id"))
    parent_cafe = relationship("Cafe", back_populates="cafe_rating")
    rating = db.Column(db.Integer, default=0, nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    comment_author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="all_comments")
    comment_cafe_id = db.Column(db.Integer, db.ForeignKey("cafes.id"))
    comment_cafe = relationship("Cafe", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()


def rating_avg(cafe):
    all_rating = [r.rating for r in cafe.cafe_rating if r.rating != 0]
    avg_rating = 0
    star = ""
    if len(all_rating) != 0:
        for r in all_rating:
            avg_rating += r
        avg_rating = round(avg_rating / len(all_rating), 1)
        for n in range(int(avg_rating)):
            star += "⭐"
    return str(avg_rating) + star


def admin_required(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            abort(401)

    return wrap


@app.route("/")
def home():
    delete_hours = db.session.query(BusinessHours).filter_by(cafe_id=None)
    for h in delete_hours:
        db.session.delete(h)
        db.session.commit()

    new_6_cafe = db.session.query(Cafe).filter_by(review=True).all()[::-1]
    if len(new_6_cafe) >= 6:
        new_6_cafe = new_6_cafe[:6]

    return render_template("index.html", cafes=new_6_cafe)


@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = Register()
    if register_form.validate_on_submit():
        user_name = register_form.name.data.title()
        email = register_form.email.data
        password = register_form.password.data
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            new_user = User()
            new_user.username = user_name
            new_user.email = email
            new_user.password = password

            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for("login"))

        flash("帳號已註冊")

    return render_template("register.html", form=register_form)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        user = db.session.query(User).filter_by(email=email).first()
        if user:
            if user.password == password:
                login_user(user)

                return redirect(url_for("home"))

            flash("密碼錯誤")
        else:
            flash("帳號不存在")

    return render_template("login.html", form=login_form)


@app.route("/logout")
@login_required
def logout():
    logout_user()

    return redirect(url_for("home"))


@app.route("/new-cafe", methods=["GET", "POST"])
@login_required
def add_new_cafe():
    if request.method == "POST":
        city = request.form["city"]
        name = request.form["name"]
        address = request.form["address"]

        cafes = db.session.query(Cafe).all()
        for cafe in cafes:
            if name in cafe.name and city == cafe.city:
                flash("此咖啡廳已加入清單")

                return redirect(url_for("add_new_cafe"))

        input_list = {"wifi": "", "dessert": "", "meal": "", "time": "", "power": "", "website": ""}
        for item in input_list.keys():
            try:
                if request.form[item] == "":
                    raise KeyError
                else:
                    input_list[item] = request.form[item]
            except KeyError:
                input_list[item] = "未提供"

        new_cafe = Cafe(
            provider=current_user,
            name=name,
            city=city,
            address=address,
            wifi=input_list["wifi"],
            dessert=input_list["dessert"],
            meal=input_list["meal"],
            time=input_list["time"],
            power=input_list["power"],
            official_website=input_list["website"]
        )

        if current_user.id == 1:
            new_cafe.review = True

        new_business_hours = BusinessHours(
            parent_cafe=new_cafe,
            mon=request.form["mon-open"] + " - " + request.form["mon-close"],
            tue=request.form["tue-open"] + " - " + request.form["tue-close"],
            wed=request.form["wed-open"] + " - " + request.form["wed-close"],
            thu=request.form["thu-open"] + " - " + request.form["thu-close"],
            fri=request.form["fri-open"] + " - " + request.form["fri-close"],
            sat=request.form["sat-open"] + " - " + request.form["sat-close"],
            sun=request.form["sun-open"] + " - " + request.form["sun-close"]
            )

        rating = Rating(
            rating_author=current_user,
            parent_cafe=new_cafe
        )

        if request.form["rating"] != "":
            rating.rating = int(request.form["rating"])

        db.session.add(new_cafe)
        db.session.add(new_business_hours)
        db.session.add(rating)
        db.session.commit()

        new_cafe.avg_rating = rating_avg(new_cafe)

        db.session.commit()

        if current_user.id == 1:
            return redirect(url_for("home"))
        else:
            return redirect(url_for("upload"))

    return render_template("add_cafe.html")


@app.route("/review-list")
@login_required
@admin_required
def review_list():
    review_cafe = [c for c in db.session.query(Cafe).filter_by(review=False)]

    return render_template("review_list.html", cafe=review_cafe)


@app.route("/result_page/<key_word>", methods=['GET', 'POST'])
def result_page(key_word):
    if request.method == "POST":
        all_cafe = []
        is_search = True

        if request.form["search"] == "":
            return render_template("result_page.html", cafes=all_cafe, is_search=is_search)

        key_word = [w for w in request.form["search"].split(" ") if w != " "]
        cafes = [c for c in db.session.query(Cafe).filter(Cafe.review).all()]
        for cafe in cafes:
            for key in key_word:
                if key in cafe.address or key in cafe.name:
                    all_cafe.append(cafe)
                    break

        return render_template("result_page.html", cafes=all_cafe, is_search=is_search)

    all_cafe = [c for c in db.session.query(Cafe).filter(Cafe.city == key_word).all() if c.review]
    is_search = False

    return render_template("result_page.html", cafes=all_cafe, is_search=is_search, key_word=key_word)


@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
def cafe_page(cafe_id):
    cafe = db.session.query(Cafe).get(cafe_id)
    hour = cafe.business_hours[0]
    comments_form = CommentForm()

    if comments_form.validate_on_submit() and current_user.is_authenticated:
        new_comment = Comment(
            comment_author=current_user,
            comment_cafe=cafe,
            text=comments_form.body.data
        )

        db.session.add(new_comment)
        db.session.commit()

        return redirect(url_for("cafe_page", cafe_id=cafe.id))

    if request.method == "POST":
        cafe = db.session.query(Cafe).get(cafe_id)

        edit_rating = db.session.query(Rating).filter_by(author_id=current_user.id, cafe_id=cafe.id).first()
        if edit_rating:
            edit_rating.rating = request.form["rating"]
        else:
            rating = Rating(
                rating_author=current_user,
                parent_cafe=cafe,
                rating=int(request.form["rating"])
            )

            db.session.add(rating)

        db.session.commit()

        cafe.avg_rating = rating_avg(cafe)

        db.session.commit()

        return redirect(url_for("cafe_page", cafe_id=cafe.id))

    return render_template("cafe_page.html", cafe=cafe, hour=hour, form=comments_form)


@app.route("/edit/<int:cafe_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit(cafe_id):
    cafe = db.session.query(Cafe).get(cafe_id)
    hour = db.session.query(BusinessHours).get(cafe_id)

    if request.method == "POST":
        cafe_review = cafe.review

        cafe.name = request.form["name"]
        cafe.city = request.form["city"]
        cafe.address = request.form["address"]
        cafe.wifi = request.form["wifi"]
        cafe.dessert = request.form["dessert"]
        cafe.meal = request.form["meal"]
        cafe.time = request.form["time"]
        cafe.power = request.form["power"]
        cafe.official_website = request.form["website"]
        cafe.google_map = request.form["map"]
        cafe.review = True

        hour.mon = request.form["mon-open"] + " - " + request.form["mon-close"]
        hour.tue = request.form["tue-open"] + " - " + request.form["tue-close"]
        hour.wed = request.form["wed-open"] + " - " + request.form["wed-close"]
        hour.thu = request.form["thu-open"] + " - " + request.form["thu-close"]
        hour.fri = request.form["fri-open"] + " - " + request.form["fri-close"]
        hour.sat = request.form["sat-open"] + " - " + request.form["sat-close"]
        hour.sun = request.form["sun-open"] + " - " + request.form["sun-close"]

        db.session.commit()

        if cafe_review:
            return redirect(url_for("home"))
        else:
            return redirect(url_for("review_list"))

    return render_template("edit.html", cafe=cafe, hour=hour)


@app.route("/delete_cafe/<int:cafe_id>")
@login_required
@admin_required
def delete_cafe(cafe_id):
    cafe = db.session.query(Cafe).get(cafe_id)
    cafe_review = cafe.review

    db.session.delete(cafe)
    db.session.commit()

    for r in db.session.query(Rating).filter_by(cafe_id=None).all():
        db.session.delete(r)
        db.session.commit()

    if cafe_review:
        return redirect(url_for("home"))
    else:
        return redirect(url_for("review_list"))


@app.route("/delete_user/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    user = db.session.query(User).get(user_id)

    if user.id != 1:
        db.session.delete(user)
        db.session.commit()

        return redirect(url_for("home"))
    else:
        return f"<h1>This is admin account<h/1>"


@app.route("/upload")
@login_required
def upload():
    return render_template("upload.html")


@app.route("/insert-map/<int:cafe_id>")
@login_required
@admin_required
def insert_map(cafe_id):
    cafe = db.session.query(Cafe).get(cafe_id)
    name = cafe.name
    address = cafe.address

    driver = webdriver.Chrome("chromedriver.exe")
    driver.get("https://www.google.com/maps")

    search_box = driver.find_element(By.ID, "searchboxinput")
    search_box.click()

    search_box.send_keys(name + " " + address)

    search_button = driver.find_element(By.ID, "searchbox-searchbutton")
    search_button.click()

    time.sleep(3)

    button_share = driver.find_element(By.XPATH, "/html/body/div[3]/div[8]/div[9]/div/div/div[1]/div[2]/div/div[1]"
                                                 "/div/div/div[4]/div[5]/button")
    button_share.click()
    time.sleep(1)
    button_map = driver.find_element(By.XPATH, "/html/body/div[3]/div[1]/div/div[2]/div/div[3]/div/div/div[1]/div"
                                               "[2]/button[2]")
    button_map.click()

    element_address = driver.find_element(By.CLASS_NAME, "yA7sBe").get_attribute("value").split('"')[1]

    driver.close()

    cafe.google_map = element_address
    db.session.commit()

    return redirect(url_for("edit", cafe_id=cafe.id))


if __name__ == "__main__":
    app.run(debug=True)
