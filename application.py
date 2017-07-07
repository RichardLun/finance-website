import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)


# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    money = 0
    stock = db.execute("SELECT shares, ticker FROM purchases WHERE user_id = :id", id=session["user_id"])
    for singlestock in stock:
        ticker = singlestock["ticker"]
        shares = singlestock["shares"]
        stock = lookup(ticker)
        total = shares * stock["price"]
        name = stock["symbol"]
        money = money + total
        db.execute("UPDATE purchases SET price=:price, total=:total WHERE user_id=:id AND ticker=:symbol", price=usd(stock["price"]), total=usd(total), id=session["user_id"], symbol=ticker)
    
    newmoney = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    money = money + newmoney[0]["cash"]
    newstock = db.execute("SELECT * from purchases WHERE user_id=:id", id=session["user_id"])
    return render_template("index.html", stocks=newstock, cash=usd(newmoney[0]["cash"]), total= usd(money) )

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        tick = request.form.get("ticker")
        quote = lookup(tick)
        if not quote:
            return apology("Ticker does not exist")
        shares = int(request.form.get("shares"))
        if shares <= 0:
            return apology("Please input a valid number of shares")
        money = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        if float(money[0]["cash"]) < quote["price"] * shares:
            return apology("Not enough money")
        db.execute("UPDATE users SET cash = cash - :purchase WHERE id = :id", id=session["user_id"], purchase=(quote["price"] * float(shares)))
        findshares = db.execute("SELECT shares FROM purchases WHERE user_id = :id AND ticker=:ticker", id=session["user_id"], ticker=quote["symbol"])

        if not findshares:
            db.execute("INSERT INTO purchases (username, shares, price, total, ticker, user_id) VALUES(:username, :shares, :price, :total, :ticker, :id)", username=quote["name"], shares=shares, price=usd(quote["price"]), total=usd(shares * quote["price"]), ticker=quote["symbol"], id=session["user_id"])
        else:
            db.execute("UPDATE purchases SET shares=:number, total=:total WHERE user_id=:id AND ticker=:ticker", id=session["user_id"], ticker=quote["symbol"], total=(float(quote["price"])*float(shares)), number=int(findshares[0]['shares']) + int(shares))
        return redirect(url_for("index"))

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    histories = db.execute("SELECT * from purchases WHERE user_id=:id", id=session["user_id"])
    
    return render_template("history.html", histories=histories)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        ticker = request.form.get("ticker")
        current = lookup(str(ticker))
        if current == None:
            return apology("That stock doesn't exist :(")
        return render_template("quoted.html", quote = current)

@app.route("/register", methods=["GET", "POST"])
def register():
    user = request.form.get("username")
    password = request.form.get("password") 
    confirm = request.form.get("confirm_password")
    if request.method == "POST":
        if not user:
            return apology("Please provide a username :(")
        elif not password:
            return apology("Please provide a password :(")
        elif not confirm:
            return apology("Please confirm your password :(")
        
        if password == confirm:
            hash = pwd_context.encrypt(password)
        else:
            return apology("Password and confirmation must match")
        
        insert = db.execute("INSERT INTO 'users' ('username','hash') VALUES (:username,:password)", username=user, password=hash)
        if insert == None:
            return apology("Sorry that username has already been taken")
        return render_template("index.html")
        
    else:       
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        tick = request.form.get("ticker")
        quote = lookup(tick)
        if not quote:
            return apology("Ticker does not exist")
        shares = int(request.form.get("shares"))
        if shares <= 0:
            return apology("Please input a valid number of shares")
        money = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        #if shares < int(money[0]["shares"]):
        #    return apology("You don't have those shares >:(")
        db.execute("UPDATE users SET cash = cash + :purchase WHERE id = :id", id=session["user_id"], purchase=(quote["price"] * float(shares)))
        findshares = db.execute("SELECT shares FROM purchases WHERE user_id = :id AND ticker=:ticker", id=session["user_id"], ticker=quote["symbol"])
        
        
        if not findshares:
            return apology("You don't have those shares >:(")
        else:
            if int(findshares[0]['shares']) < int(shares):
                return apology("You don't have those shares >:(")
            db.execute("UPDATE purchases SET shares=:number, total=:total WHERE user_id=:id AND ticker=:ticker", id=session["user_id"], ticker=quote["symbol"], total=(float(quote["price"])*float(shares)), number=int(findshares[0]['shares']) - int(shares))
        return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)