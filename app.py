
from ast import pattern
import email
import os
from flask import jsonify
from pydoc import text
from flask import Flask, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_bcrypt import Bcrypt
from wtforms import StringField, TextAreaField, IntegerField, SubmitField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length, ValidationError
from werkzeug.utils import secure_filename
import re
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



app = Flask(__name__)

app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test.db')

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"check_same_thread": False}
}

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# SESSION MANAGEMENT

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# DATABASE MODELS

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    stream = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(200), default="default.png")


class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    description = db.Column(db.Text)
    time = db.Column(db.String(50))
    date = db.Column(db.String(50))
    seats = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='created_slots')
    is_active = db.Column(db.Boolean, default=True)

class Booking(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'))
    slot = db.relationship('Slot')
    user = db.relationship('User')
    attended = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer)   # 1–5
    review = db.Column(db.Text)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # receiver (creator)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_read = db.Column(db.Boolean, default=False)

class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    subject = db.Column(db.String(50))

class PostReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'))
    reaction = db.Column(db.String(10))  # "agree" / "disagree"

class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

# FORMS

class RegisterForm(FlaskForm):

    username = StringField(validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)])
    email = StringField(validators=[InputRequired(), Length(max=100)])

    # STREAMS
    stream = SelectField(
        "Stream",
        choices=[
            ("SBL", "SBL"),
            ("SLSE", "SLSE"),
            ("SOS", "SOS"),
            ("SET", "SET"),
            ("SEDA", "SEDA")
        ],
        validators=[InputRequired()]
    )

    # SEMESTER 
    semester = SelectField(
        "Semester",
        choices=[(str(i), f"Semester {i}") for i in range(1, 11)],
        validators=[InputRequired()]
    )

    submit = SubmitField("Register")

    def validate_email(self, email):

        pattern = r'^[a-z]+\.[a-z]+\.[a-z]+@nuv\.ac\.in$'

        if not re.match(pattern, email.data):
            raise ValidationError("Use format: abc.def.ghi@nuv.ac.in")

        existing_user = User.query.filter_by(email=email.data).first()
        if existing_user:
            raise ValidationError("Email already registered")

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)])
    submit = SubmitField("Login")


class SlotForm(FlaskForm):
    name = StringField(validators=[InputRequired()])
    subject = StringField(validators=[InputRequired()])
    topic = StringField(validators=[InputRequired()])
    date = StringField(validators=[InputRequired()])   
    time = StringField(validators=[InputRequired()])
    description = StringField(validators=[InputRequired()])
    duration = IntegerField(validators=[InputRequired()])
    seats = IntegerField(validators=[InputRequired()])

    submit = SubmitField("Publish Slot")

class ContactForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=2, max=100)])
    email = StringField(validators=[InputRequired(), Length(max=100)])
    message = TextAreaField(validators=[InputRequired()])
    submit = SubmitField("Send Message")

class EditProfileForm(FlaskForm):
    bio = TextAreaField(validators=[Length(max=500)])
    profile_pic = FileField(validators=[FileAllowed(['jpg', 'png', 'gif'], 'Images only!')])
    submit = SubmitField("Update Profile")

# ROUTES

from sqlalchemy import or_

@app.route("/", methods=["GET"])
def home():

    subject = request.args.get("subject")
    name = request.args.get("name")
    date = request.args.get("date")
    time = request.args.get("time")

    filters = []

    if subject:
        filters.append(Slot.subject.ilike(f"%{subject}%"))
    if name:
        filters.append(Slot.name.ilike(f"%{name}%"))
    if date:
        filters.append(Slot.date == date)
    if time:
        filters.append(Slot.time == time)

    if filters:
        slots = Slot.query.filter(*filters, Slot.is_active == True).all()
    else:
        slots = Slot.query.filter_by(is_active=True).all()

    return render_template("home.html", slots=slots)
# REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():

        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode("utf-8")

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            stream=form.stream.data,
            semester=int(form.semester.data)
)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)

            return redirect(url_for("dashboard"))

        else:
            flash("Invalid username or password")

    return render_template("login.html", form=form)


# LOGOUT

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


# CREATE SLOT

@app.route("/list_slot", methods=["GET", "POST"])
@login_required
def list_slot():

    form = SlotForm()

    if form.validate_on_submit():

        slot = Slot(
            name=form.name.data,
            subject=form.subject.data,
            description=form.description.data,
            time=form.time.data,
            date=form.date.data,
            seats=form.seats.data,

            # SAVE CREATOR
            user_id=current_user.id
        )

        db.session.add(slot)
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("list_slot.html", form=form)


@app.route("/delete_slot/<int:slot_id>", methods=["POST"])
@login_required
def delete_slot(slot_id):

    slot = Slot.query.get_or_404(slot_id)

    # SECURITY
    if slot.user_id != current_user.id:
        flash("Unauthorized action!")
        return redirect(url_for("home"))

    db.session.delete(slot)
    db.session.commit()

    flash("Slot deleted successfully")

    return redirect(url_for("home"))

# JOIN SLOT

@app.route("/join_slot/<int:slot_id>")
@login_required
def join_slot(slot_id):

    slot = Slot.query.get_or_404(slot_id)
    # BLOCK CREATOR FROM JOINING THEIR OWN SLOTS
    if slot.user_id == current_user.id:
        flash("You cannot join your own slot!")
        return redirect(url_for("home"))

    return render_template("confirm_slot.html", slot=slot)


# CONFIRM BOOKING

@app.route("/confirm_booking/<int:slot_id>")
@login_required
def confirm_booking(slot_id):

    slot = Slot.query.get_or_404(slot_id)

    if slot.user_id == current_user.id:
        flash("You cannot book your own slot!")
        return redirect(url_for("home"))

    existing_booking = Booking.query.filter_by(
        user_id=current_user.id,
        slot_id=slot.id
    ).first()

    if existing_booking:
        flash("Already joined!")
        return redirect(url_for("dashboard"))

    if slot.seats > 0:

        booking = Booking(user_id=current_user.id, slot_id=slot.id)
        slot.seats -= 1

        # ✅ CREATE NOTIFICATION FOR CREATOR
        notif = Notification(
            user_id=slot.user_id,
            message=f"{current_user.username} joined your slot '{slot.name}'"
        )

        db.session.add(booking)
        db.session.add(notif)
        db.session.commit()

        flash("Slot booked successfully!")

    return redirect(url_for("dashboard"))

# Slot detail with attendees list (only for creator)

@app.route("/slot/<int:slot_id>")
@login_required
def slot_detail(slot_id):
    slot = Slot.query.get_or_404(slot_id)

    if slot.user_id != current_user.id:
        flash("Unauthorized!")
        return redirect(url_for("home"))

    bookings = Booking.query.filter_by(slot_id=slot.id).all()

    total = len(bookings)
    present = sum(1 for b in bookings if b.attended)

    attendance_percentage = 0
    if total > 0:
        attendance_percentage = (present / total) * 100

    return render_template(
        "slot_detail.html",
        slot=slot,
        bookings=bookings,
        total=total,
        present=present,
        attendance_percentage=attendance_percentage
    )

# about page
@app.route("/about")
def about():
    return render_template("about.html")

# Attendance marking (only for creator)

@app.route("/mark_attendance/<int:booking_id>", methods=["POST"])
@login_required
def mark_attendance(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = booking.slot

    # Only creator can mark attendance
    if slot.user_id != current_user.id:
        flash("Unauthorized!")
        return redirect(url_for("home"))

    booking.attended = True
    db.session.commit()

    flash("Attendance marked!")
    return redirect(url_for("slot_detail", slot_id=slot.id))

# End Session
@app.route("/end_session/<int:slot_id>", methods=["POST"])
@login_required
def end_session(slot_id):
    slot = Slot.query.get_or_404(slot_id)

    if slot.user_id != current_user.id:
        flash("Unauthorized!")
        return redirect(url_for("home"))

    slot.is_active = False
    db.session.commit()

    flash("Session ended successfully!")
    return redirect(url_for("home"))

# Review and Rating
@app.route("/submit_review/<int:booking_id>", methods=["POST"])
@login_required
def submit_review(booking_id):

    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        flash("Unauthorized!")
        return redirect(url_for("dashboard"))

    booking.rating = int(request.form.get("rating"))
    booking.review = request.form.get("review")

    # ✅ NOTIFY CREATOR
    notif = Notification(
        user_id=booking.slot.user_id,
        message=f"{current_user.username} rated {booking.rating}/5 and said: '{booking.review}'"
    )

    db.session.add(notif)
    db.session.commit()

    flash("Review submitted!")
    return redirect(url_for("dashboard"))

# CONTACT
@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data
        )
        db.session.add(msg)
        db.session.commit()
        flash("Message sent successfully!")
        return redirect(url_for("contact"))
    return render_template("contact.html", form=form)

# DASHBOARD

@app.route("/dashboard")
@login_required
def dashboard():

    bookings = Booking.query.filter_by(user_id=current_user.id).all()

    return render_template("dashboard.html", bookings=bookings)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


# EDIT PROFILE
@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        current_user.bio = form.bio.data

        # Handle file upload
        if form.profile_pic.data:
            file = form.profile_pic.data

            # secure filename
            filename = secure_filename(f"{current_user.id}_{file.filename}")

            # correct absolute path
            upload_path = os.path.join(app.root_path, 'static/images')

            # create folder if not exists
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)

            # full file path
            file_path = os.path.join(upload_path, filename)

            # save file
            file.save(file_path)

            print("Saved at:", file_path)  # debug

            # save filename in DB
            current_user.profile_pic = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    elif request.method == "GET":
        form.bio.data = current_user.bio

    return render_template("edit_profile.html", form=form)

# messages
@app.route("/messages")
@login_required
def messages():
    return render_template("messages.html")


# notifications
@app.route("/notifications")
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()

    return render_template("notifications.html", notifs=notifs)


# my slots page
@app.route("/my_slots")
@login_required
def my_slots():
    slots = Slot.query.filter_by(user_id=current_user.id).all()
    return render_template("my_slots.html", slots=slots)

# Community page
from collections import defaultdict

@app.route("/community", methods=["GET", "POST"])
@login_required
def community():

    # 👉 CREATE POST
    if request.method == "POST":

        file = request.files.get("image")
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            upload_folder = os.path.join(app.root_path, 'static', 'uploads')

            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file.save(os.path.join(upload_folder, filename))

        new_post = CommunityPost(
            title=request.form.get("title"),
            description=request.form.get("description"),
            subject=request.form.get("subject"),
            image=filename,
            user_id=current_user.id
        )

        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("community"))

    # 👉 FETCH POSTS
    posts = CommunityPost.query.order_by(
        CommunityPost.timestamp.desc()
    ).all()

    # 👉 FETCH COMMENTS
    from collections import defaultdict
    comments_map = defaultdict(list)

    all_comments = PostComment.query.order_by(PostComment.timestamp.asc()).all()

    for c in all_comments:
        comments_map[c.post_id].append(c)

    # 👉 TRENDING
    topic_scores = defaultdict(int)

    for post in posts:
        agree_count = PostReaction.query.filter_by(
            post_id=post.id,
            reaction="agree"
        ).count()

        if post.subject:
            topic_scores[post.subject] += agree_count

    trending_topics = sorted(
        topic_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return render_template(
        "community.html",
        posts=posts,
        comments_map=comments_map,
        trending_topics=trending_topics
    )
    


# Comments

@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def comment(post_id):

    comment = PostComment(
        post_id=post_id,
        user_id=current_user.id,
        comment=request.form.get("comment")
    )

    db.session.add(comment)
    db.session.commit()

    return redirect(url_for("community"))

# Reactiions
@app.route("/agree/<int:post_id>")
@login_required
def agree(post_id):

    existing = PostReaction.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if existing:
        existing.reaction = "agree"
    else:
        db.session.add(PostReaction(
            user_id=current_user.id,
            post_id=post_id,
            reaction="agree"
        ))

    db.session.commit()
    return redirect(url_for("community"))

@app.route("/disagree/<int:post_id>")
@login_required
def disagree(post_id):

    existing = PostReaction.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if existing:
        if existing.reaction == "disagree":
            return redirect(url_for("community"))  # already disliked
        else:
            existing.reaction = "disagree"
    else:
        db.session.add(PostReaction(
            user_id=current_user.id,
            post_id=post_id,
            reaction="disagree"
        ))

    db.session.commit()
    return redirect(url_for("community"))

# API
@app.route("/api/react", methods=["POST"])
@login_required
def api_react():

    data = request.get_json()
    post_id = data.get("post_id")
    reaction_type = data.get("reaction")

    existing = PostReaction.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if existing:
        if existing.reaction == reaction_type:
            pass  # do nothing
        else:
            existing.reaction = reaction_type
    else:
        db.session.add(PostReaction(
            user_id=current_user.id,
            post_id=post_id,
            reaction=reaction_type
        ))

    db.session.commit()

    # return updated counts
    agree = PostReaction.query.filter_by(post_id=post_id, reaction="agree").count()
    disagree = PostReaction.query.filter_by(post_id=post_id, reaction="disagree").count()

    return jsonify({
        "agree": agree,
        "disagree": disagree
    })


@app.route("/api/analytics")
def analytics():

    from collections import defaultdict

    scores = defaultdict(int)

    posts = CommunityPost.query.all()

    for post in posts:

        agree = PostReaction.query.filter_by(
            post_id=post.id,
            reaction="agree"
        ).count()

        disagree = PostReaction.query.filter_by(
            post_id=post.id,
            reaction="disagree"
        ).count()

        # 🔥 weighted score (important upgrade)
        score = (agree * 2) - (disagree * 1)

        if post.subject:
            scores[post.subject] += score

    data = []

    for subject, score in scores.items():
        data.append({
            "subject": subject,
            "score": score
        })

    return jsonify(data)


# Analytics page

@app.route("/analytics")
@login_required
def analytics_page():
    return render_template("analytics.html")

# Delete Post
@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):

    post = CommunityPost.query.get_or_404(post_id)

    # 🔐 ONLY CREATOR CAN DELETE
    if post.user_id != current_user.id:
        flash("You are not authorized to delete this post!")
        return redirect(url_for("community"))

    # delete image file (optional but good)
    if post.image:
        image_path = os.path.join(app.root_path, "static", "uploads", post.image)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(post)
    db.session.commit()

    flash("Post deleted successfully!")
    return redirect(url_for("community"))

# Profile
@app.route("/user/<int:user_id>")
@login_required
def user_profile(user_id):

    user = User.query.get_or_404(user_id)

    # fetch user's posts (optional social feel)
    posts = CommunityPost.query.filter_by(user_id=user.id).all()

    return render_template("user_profile.html", user=user, posts=posts)

@app.route("/users")
@login_required
def users():

    all_users = User.query.all()

    return render_template("users.html", users=all_users)

# Messages
@app.route("/send_message/<int:receiver_id>", methods=["POST"])
@login_required
def send_message(receiver_id):

    msg = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message=request.form.get("message")
    )

    db.session.add(msg)
    db.session.commit()

    return redirect(url_for("chat", user_id=receiver_id))

#Chat 
@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):

    other_user = User.query.get_or_404(user_id)

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template("chat.html", other_user=other_user, messages=messages)

@app.before_request
def init_db():
    db.create_all()

@app.errorhandler(500)
def error(e):
    return f"ERROR: {str(e)}", 500
    
if __name__ == "__main__":
    app.run(debug=True)
