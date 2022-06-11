import os

import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")




@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    totals=[]  #current stock price X number of shares owned
    companies = []  #array of dictionaries which containes name, price and symbol information of the stock
    prices = []  #containes the usd version of the prices
    sum=0  #the total value of the current value of owned stocks and cash
    cash = db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
    portfolio = db.execute("SELECT * FROM stocks WHERE id=?",user_id)
    index = range(len(portfolio))  #to be able to use a for loop in the index.html
    for i in range(len(portfolio)):
        companies.append(lookup(portfolio[i]["symbol"]))
        totals.append((companies[i]["price"])*int(portfolio[i]["shares"]))
        sum+=totals[i]
        prices.append(usd(companies[i]["price"]))
    sum+=cash
    sum = usd(sum)
    cash=usd(cash)
    for i in range(len(totals)):
        totals[i]=usd(totals[i])
    return render_template("index.html",portfolio=portfolio, companies=companies, prices=prices,index=index,cash=cash,totals=totals,sum=sum)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user_id = session["user_id"]
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol=request.form.get("symbol")
        if not request.form.get("shares"):
            return apology("invalid shares",403)
        if not lookup(symbol):
            return apology("invalid symbol", 403)
        stock_info = lookup(symbol)
        symbol = stock_info["symbol"]
        portfolio = (db.execute("SELECT symbol FROM stocks WHERE id=?",user_id))
        portfolio_list = []
        for i in portfolio:
            portfolio_list.append(i["symbol"])
        balance = db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
        shares=int(request.form.get("shares"))
        print("love pussies")
        if stock_info["symbol"] not in portfolio_list:
            if (stock_info["price"]*shares)<balance:
                dt=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db.execute("INSERT INTO stocks (id,symbol,shares) VALUES(?,?,?)",user_id,symbol,str(shares))
                balance = balance - (stock_info["price"])*shares
                db.execute("UPDATE users SET cash=? WHERE id=?",balance,session["user_id"])
                db.execute("INSERT INTO history (id,symbol,shares,price,time) VALUES(?,?,?,?,?)",user_id,symbol,str(shares),stock_info["price"],dt)
                return redirect("/")
            return apology("can't afford", 403)
        else:
            share = shares
            shares += db.execute("SELECT shares FROM stocks WHERE id=?",user_id)[0]["shares"]
            if (stock_info["price"]*share)<balance:
                dt=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db.execute("UPDATE stocks SET shares=? WHERE symbol=? AND id=?",str(shares),stock_info["symbol"],session["user_id"])
                balance = balance - (stock_info["price"])* share
                db.execute("UPDATE users SET cash=? WHERE id=?",balance,session["user_id"])
                db.execute("INSERT INTO history (id,symbol,shares,price,time) VALUES(?,?,?,?,?)",user_id,symbol,str(share),stock_info["price"],dt)
                return redirect("/")
            return apology("can't afford", 403)




@app.route("/history")
@login_required
def history():
    history=db.execute("SELECT * FROM history WHERE id=? ORDER BY time DESC",session["user_id"])
    return render_template("history.html",history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method=="GET":
        return render_template("quote.html")
    else:
        stock = request.form.get("quote")
        stock_info = lookup(stock)
        if stock_info:
            return render_template("quoted.html",stock=stock_info)
        return apology("invalid symbol", 403)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method=="GET":
        return render_template("register.html")
    else:
        username_list = []
        usernames = db.execute("SELECT username FROM users")
        for i in usernames:
            username_list.append(i["username"])
        if request.form.get("username") in username_list:
            return apology("username exists",403)
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("most provide password", 403)
        elif not request.form.get("password_again"):
            return apology("most provide your password again", 403)
        elif request.form.get("password")!= request.form.get("password_again"):
            return apology("passwords don't match", 403)

        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))
        cash = 10000


        db.execute("INSERT INTO users (username, hash, cash) VALUES(?,?,?)",username,hash,cash)

        rows = db.execute("SELECT * FROM users WHERE username = ?",username)


        session["user_id"] = rows[0]["id"]

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    portfolio = (db.execute("SELECT symbol FROM stocks WHERE id=?",user_id))
    portfolio_list = []
    for i in range(len(portfolio)):
        portfolio_list.append(portfolio[i]["symbol"])
    if request.method=="GET":
        return render_template("sell.html",portfolio_list=portfolio_list)
    else:
        if request.form.get("symbol") not in portfolio_list:
            return apology("symbol not owned", 403)
        else:
            shares = (db.execute("SELECT shares FROM stocks WHERE symbol=? AND id=?",request.form.get("symbol"),user_id ))[0]["shares"]
            if int(request.form.get("shares"))>shares:
                return apology("too many shares",403)
            elif int(request.form.get("shares"))==shares:
                dt=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db.execute("DELETE FROM stocks WHERE symbol=? AND id=?",request.form.get("symbol"),user_id)
                price=lookup(request.form.get("symbol"))["price"]
                cash=db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
                db.execute("UPDATE users SET cash=? WHERE id=?",(cash+(price*shares)),user_id)
                db.execute("INSERT INTO history (id,symbol,shares,price,time) VALUES(?,?,?,?,?)",user_id,request.form.get("symbol"),(-1*int(request.form.get("shares"))),price,dt)
                return redirect("/")
            else:
                dt=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sell_shares = int(request.form.get("shares"))
                shares-=sell_shares
                db.execute("UPDATE stocks SET shares=? WHERE symbol=? AND id=?",shares,request.form.get("symbol"),user_id)
                price=lookup(request.form.get("symbol"))["price"]
                cash=db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
                db.execute("UPDATE users SET cash=? WHERE id=?",(cash+(price*sell_shares)),user_id)
                db.execute("INSERT INTO history (id,symbol,shares,price,time) VALUES(?,?,?,?,?)",user_id,request.form.get("symbol"),(-1*int(request.form.get("shares"))),price,dt)

                return redirect("/")


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method=="GET":
        return render_template("deposit.html")
    else:
        user_id = session["user_id"]
        amount = request.form.get("amount")
        balance = db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
        if int(amount) > 0:
            db.execute("UPDATE users SET cash=? WHERE id=?",str(int(amount)+balance),user_id)
            return redirect("/")
        return apology("invalid amount", 403)

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method=="GET":
        return render_template("withdraw.html")
    else:
        user_id = session["user_id"]
        amount = request.form.get("amount")
        balance = db.execute("SELECT cash FROM users WHERE id=?",user_id)[0]["cash"]
        if int(amount) < balance:
            db.execute("UPDATE users SET cash=? WHERE id=?",str(balance-int(amount)),user_id)
            return redirect("/")
        return apology("invalid amount", 403)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method=="GET":
        return render_template("account.html")
    else:
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if not request.form.get("password"):
            return apology("must enter current password", 403)
        elif not request.form.get("new_password"):
            return apology("most provide new password", 403)
        elif not request.form.get("new_password_again"):
            return apology("must provide new password again", 403)
        elif request.form.get("new_password")!= request.form.get("new_password_again"):
            return apology("passwords don't match", 403)
        elif not  check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("wrong password", 403)

        hash = generate_password_hash(request.form.get("new_password"))


        db.execute("UPDATE users SET hash=? WHERE id=?",hash,session["user_id"])

        return redirect("/")


